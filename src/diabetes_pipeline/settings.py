"""Configuration loading and project path resolution."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_CONFIG = PROJECT_ROOT / "config" / "datasets.yaml"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "publication_pipeline"


class ConfigurationError(ValueError):
    """Raised when a pipeline configuration is invalid."""


def configuration_sha256(config: dict[str, Any]) -> str:
    def normalize(value: Any) -> Any:
        if isinstance(value, Path):
            try:
                return str(value.relative_to(PROJECT_ROOT))
            except ValueError:
                return str(value)
        if isinstance(value, dict):
            return {str(key): normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        return value

    payload = json.dumps(normalize(config), sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def source_tree_sha256() -> str:
    digest = hashlib.sha256()
    source_root = PROJECT_ROOT / "src" / "diabetes_pipeline"
    for path in sorted(source_root.rglob("*.py")):
        digest.update(str(path.relative_to(PROJECT_ROOT)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file does not exist: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ConfigurationError(f"Configuration must be a mapping: {path}")
    return payload


def load_dataset_registry(path: Path | str = DEFAULT_DATASET_CONFIG) -> dict[str, dict[str, Any]]:
    path = Path(path)
    payload = _read_yaml(path)
    datasets = payload.get("datasets")
    if not isinstance(datasets, dict) or not datasets:
        raise ConfigurationError("Dataset configuration must contain a non-empty 'datasets' mapping")

    required = {
        "display_name",
        "task",
        "endpoint",
        "raw_path",
        "loader",
        "target_name",
        "evaluation_strategy",
        "numeric_features",
        "categorical_features",
    }
    registry: dict[str, dict[str, Any]] = {}
    for name, raw_cfg in datasets.items():
        if not isinstance(raw_cfg, dict):
            raise ConfigurationError(f"Dataset '{name}' configuration must be a mapping")
        missing = sorted(required - set(raw_cfg))
        if missing:
            raise ConfigurationError(f"Dataset '{name}' is missing required keys: {missing}")
        cfg = deepcopy(raw_cfg)
        cfg["name"] = name
        raw_path = Path(cfg["raw_path"])
        cfg["raw_path"] = raw_path if raw_path.is_absolute() else PROJECT_ROOT / raw_path
        registry[name] = cfg
    return registry


def get_dataset_config(name: str, path: Path | str = DEFAULT_DATASET_CONFIG) -> dict[str, Any]:
    registry = load_dataset_registry(path)
    try:
        return registry[name]
    except KeyError as exc:
        raise ConfigurationError(
            f"Unknown dataset '{name}'. Available datasets: {sorted(registry)}"
        ) from exc


def load_experiment_profile(name: str) -> dict[str, Any]:
    path = PROJECT_ROOT / "config" / "experiments" / f"{name}.yaml"
    profile = _read_yaml(path)
    required = {"name", "seed", "optimization_metric", "n_trials", "n_bootstrap"}
    missing = sorted(required - set(profile))
    if missing:
        raise ConfigurationError(f"Experiment profile '{name}' is missing keys: {missing}")
    if profile["name"] != name:
        raise ConfigurationError("Experiment filename and profile name disagree")
    if profile["optimization_metric"] != "average_precision":
        raise ConfigurationError("The implemented tuning objective is average_precision")
    if name == "final":
        validate_final_profile(profile)
    elif name == "final_internal_validation":
        from diabetes_pipeline.publication.governance import (
            validate_final_internal_profile,
        )

        validate_final_internal_profile(profile)
    return profile


def validate_final_profile(profile: dict[str, Any]) -> None:
    """Reject reduced budgets even when an operator marks a profile as locked."""
    failures = []
    for field, expected in (("name", "final"), ("n_trials", 75), ("n_bootstrap", 2000),
                            ("optimization_metric", "average_precision")):
        if profile.get(field) != expected:
            failures.append(f"{field} must equal {expected}")
    for field in ("max_repeats", "max_outer_folds", "inner_folds_override"):
        if profile.get(field) is not None:
            failures.append(f"{field} cannot reduce final evaluation")
    limits = profile.get("sample_limits", {})
    if not isinstance(limits, dict) or any(value is not None for value in limits.values()):
        failures.append("final sample limits must all be null")
    if failures:
        raise ConfigurationError("Invalid final profile: " + "; ".join(failures))
