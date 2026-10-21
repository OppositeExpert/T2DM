"""Fail-closed controls for finalized, transparently internal validation."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

import yaml

from diabetes_pipeline.settings import PROJECT_ROOT, ConfigurationError


DEFAULT_FINAL_PUBLICATION_PROTOCOL = (
    PROJECT_ROOT / "config" / "final_publication_protocol.yaml"
)
FINAL_INTERNAL_PROFILE_NAME = "final_internal_validation"
FINAL_MODELS = (
    "logistic_regression",
    "random_forest",
    "xgboost",
    "lightgbm",
    "catboost",
)


def final_protocol_sha256(protocol: dict[str, Any]) -> str:
    """Hash a protocol while excluding only its self-referential hash field."""

    normalized = deepcopy(protocol)
    normalized["protocol_sha256"] = None
    return hashlib.sha256(
        json.dumps(normalized, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def validate_final_internal_profile(profile: dict[str, Any]) -> None:
    """Reject any reduced or unlocked publication-internal profile."""

    failures: list[str] = []
    required = {
        "name": FINAL_INTERNAL_PROFILE_NAME,
        "seed": 42,
        "optimization_metric": "average_precision",
        "n_trials": 75,
        "n_bootstrap": 2000,
        "locked": True,
        "evidence_scope": "final_prespecified_internal_validation",
        "independent_holdout_claim_allowed": False,
    }
    for field, expected in required.items():
        if profile.get(field) != expected:
            failures.append(f"{field} must equal {expected!r}")
    for field in ("max_repeats", "max_outer_folds", "inner_folds_override"):
        if profile.get(field) is not None:
            failures.append(f"{field} cannot reduce finalized internal validation")
    limits = profile.get("sample_limits")
    expected_datasets = {"pidd", "sylhet", "brfss", "hospital130"}
    if (
        not isinstance(limits, dict)
        or set(limits) != expected_datasets
        or any(value is not None for value in limits.values())
    ):
        failures.append("all final internal-validation sample limits must be null")
    if failures:
        raise ConfigurationError(
            "Invalid final internal-validation profile: " + "; ".join(failures)
        )


def _load_protocol(path: Path | str) -> dict[str, Any]:
    path = Path(path).resolve()
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ConfigurationError("Final publication protocol must be a mapping")
    return payload


def assert_final_internal_validation_authorized(
    *,
    dataset_name: str,
    profile: dict[str, Any],
    models: Sequence[str],
    raw_data_sha256: str,
    split_manifest_sha256: str,
    dataset_configuration_sha256: str,
    analysis_configuration_sha256: str,
    source_tree_sha256: str,
    requirements_lock_sha256: str,
    protocol_path: Path | str = DEFAULT_FINAL_PUBLICATION_PROTOCOL,
) -> str:
    """Verify the frozen bindings before any finalized result is produced."""

    validate_final_internal_profile(profile)
    protocol = _load_protocol(protocol_path)
    failures: list[str] = []
    if protocol.get("status") != "frozen":
        failures.append("protocol status is not frozen")
    recorded_protocol_sha = protocol.get("protocol_sha256")
    observed_protocol_sha = final_protocol_sha256(protocol)
    if not recorded_protocol_sha or recorded_protocol_sha != observed_protocol_sha:
        failures.append("protocol SHA-256 is absent or invalid")
    if not bool(protocol.get("execution", {}).get("authorized", False)):
        failures.append("final internal-validation execution is not authorized")
    if protocol.get("profile", {}).get("name") != FINAL_INTERNAL_PROFILE_NAME:
        failures.append("protocol profile does not name final_internal_validation")
    if tuple(models) != FINAL_MODELS:
        failures.append("the complete frozen five-model registry is required")
    strategy = protocol.get("evaluation_strategies", {}).get(dataset_name)
    if not strategy or "internal_validation" not in str(strategy):
        failures.append(f"{dataset_name} is not registered as internal validation")
    if dataset_name in {"brfss", "hospital130"}:
        dataset_protocol = protocol.get("datasets", {}).get(dataset_name, {})
        if dataset_protocol.get("independent_holdout") is not False:
            failures.append(
                f"{dataset_name} must explicitly prohibit an independent-holdout claim"
            )

    bindings = protocol.get("frozen_bindings", {})
    expected = {
        "raw_data_sha256": raw_data_sha256,
        "split_manifest_sha256": split_manifest_sha256,
        "dataset_configuration_sha256": dataset_configuration_sha256,
        "analysis_configuration_sha256": analysis_configuration_sha256,
    }
    for family, observed in expected.items():
        recorded = bindings.get(family, {}).get(dataset_name)
        if recorded != observed:
            failures.append(f"{family}.{dataset_name} does not match")
    for field, observed in (
        ("source_tree_sha256", source_tree_sha256),
        ("requirements_lock_sha256", requirements_lock_sha256),
    ):
        if bindings.get(field) != observed:
            failures.append(f"{field} does not match")
    if failures:
        raise RuntimeError(
            "Final internal-validation execution denied: " + "; ".join(failures)
        )
    return str(protocol["protocol_id"])
