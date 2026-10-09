"""Outcome-blind persisted holdout manifests and final-execution safeguards."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
import yaml

from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.settings import (
    DEFAULT_OUTPUT_ROOT,
    PROJECT_ROOT,
    configuration_sha256,
    get_dataset_config,
    source_tree_sha256,
    validate_final_profile,
)
from diabetes_pipeline.splitting.registry import validate_split_manifest
from diabetes_pipeline.splitting.strategies import build_split_manifest


DEFAULT_PROTOCOL_PATH = PROJECT_ROOT / "config" / "publication_protocol.yaml"
FORBIDDEN_OUTCOME_KEYS = {
    "target",
    "label",
    "outcome",
    "event",
    "events",
    "positive",
    "positives",
    "prevalence",
    "target_counts",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _contains_outcome_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key).strip().lower()
            if normalized in FORBIDDEN_OUTCOME_KEYS or _contains_outcome_key(item):
                return True
    elif isinstance(value, list):
        return any(_contains_outcome_key(item) for item in value)
    return False


def sanitize_holdout_manifest(manifest: pd.DataFrame) -> pd.DataFrame:
    """Remove all persisted outcome information from a holdout manifest."""

    required = {
        "dataset",
        "strategy",
        "row_position",
        "row_id",
        "group_id",
        "role",
        "repeat",
        "outer_fold",
        "inner_seed",
        "seed",
    }
    missing = sorted(required - set(manifest.columns))
    if missing:
        raise ValueError(f"Holdout manifest is missing required fields: {missing}")
    if set(manifest["role"]) != {"development", "test"}:
        raise ValueError("Concealed manifest requires development and test roles")
    safe = manifest[[column for column in manifest.columns if column != "target"]].copy()
    if any(str(column).strip().lower() in FORBIDDEN_OUTCOME_KEYS for column in safe):
        raise RuntimeError("Outcome field survived holdout-manifest sanitization")
    return safe.sort_values("row_position").reset_index(drop=True)


def _concealed_metadata(
    manifest: pd.DataFrame,
    *,
    manifest_sha256: str,
    purpose: str,
) -> dict[str, Any]:
    role_rows = {
        str(role): int(count)
        for role, count in manifest["role"].value_counts().sort_index().items()
    }
    group_counts: dict[str, int | None] = {}
    for role, frame in manifest.groupby("role"):
        nonempty = frame["group_id"].astype(str).str.len().gt(0)
        group_counts[str(role)] = (
            int(frame.loc[nonempty, "group_id"].nunique())
            if nonempty.any()
            else None
        )
    metadata = {
        "schema_version": "1.0",
        "dataset": str(manifest["dataset"].iloc[0]),
        "strategy": str(manifest["strategy"].iloc[0]),
        "seed": int(manifest["seed"].iloc[0]),
        "purpose": str(purpose),
        "outcome_blind": True,
        "rows": int(len(manifest)),
        "role_rows": role_rows,
        "role_groups": group_counts,
        "manifest_sha256": manifest_sha256,
    }
    if _contains_outcome_key(metadata):
        raise RuntimeError("Concealed metadata contains an outcome-derived key")
    return metadata


def validate_concealed_manifest_files(
    manifest_path: Path | str,
    *,
    expected_sha256: str | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    manifest_path = Path(manifest_path).resolve()
    metadata_path = manifest_path.with_suffix(".json")
    if not manifest_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            f"Concealed manifest or metadata is missing: {manifest_path}, {metadata_path}"
        )
    columns = pd.read_csv(manifest_path, nrows=0).columns
    if any(str(column).strip().lower() in FORBIDDEN_OUTCOME_KEYS for column in columns):
        raise RuntimeError("Persisted concealed manifest exposes an outcome field")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if _contains_outcome_key(metadata) or not bool(metadata.get("outcome_blind")):
        raise RuntimeError("Persisted concealed metadata is not outcome-blind")
    observed_sha256 = _sha256_file(manifest_path)
    if str(metadata.get("manifest_sha256")) != observed_sha256:
        raise RuntimeError("Concealed manifest checksum does not match its metadata")
    if expected_sha256 is not None and observed_sha256 != str(expected_sha256):
        raise RuntimeError("Concealed manifest checksum does not match the protocol")
    manifest = pd.read_csv(manifest_path)
    if manifest["row_position"].duplicated().any():
        raise RuntimeError("Concealed manifest contains duplicate row positions")
    if manifest["row_id"].astype(str).duplicated().any():
        raise RuntimeError("Concealed manifest contains duplicate row identities")
    for field in ("dataset", "strategy", "seed"):
        values = manifest[field].drop_duplicates().tolist()
        if len(values) != 1 or str(values[0]) != str(metadata.get(field)):
            raise RuntimeError(
                f"Concealed manifest {field} does not match its metadata"
            )
    observed_role_rows = {
        str(role): int(count)
        for role, count in manifest["role"].value_counts().sort_index().items()
    }
    if observed_role_rows != metadata.get("role_rows"):
        raise RuntimeError("Concealed manifest role counts do not match its metadata")
    return manifest_path, metadata_path, metadata


def final_analysis_configuration_sha256(
    *,
    dataset_name: str,
    dataset_config: dict[str, Any],
    profile: dict[str, Any],
    models: Sequence[str],
) -> str:
    """Fingerprint the executable inputs that must be frozen before final access."""

    lock_path = PROJECT_ROOT / "requirements.lock"
    payload = {
        "schema_version": "1.0",
        "dataset": dataset_name,
        "dataset_configuration_sha256": configuration_sha256(dataset_config),
        "profile": profile,
        "models": list(models),
        "configuration_file_sha256": {
            relative: _sha256_file(PROJECT_ROOT / relative)
            for relative in (
                "config/datasets.yaml",
                "config/availability_scenarios.yaml",
                "config/feature_ontology.yaml",
                "config/output_schemas.yaml",
            )
        },
        "requirements_lock_sha256": (
            _sha256_file(lock_path) if lock_path.exists() else None
        ),
        "source_tree_sha256": source_tree_sha256(),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def write_development_concealment_test(
    dataset: LoadedDataset,
    *,
    seed: int = 42,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> tuple[Path, Path, dict[str, Any]]:
    """Exercise concealment using a known development split; never creates final evidence."""

    cfg = get_dataset_config(dataset.name)
    if cfg["evaluation_strategy"] not in {
        "stratified_holdout_cv",
        "stratified_group_holdout_cv",
    }:
        raise ValueError("Concealment tests require a configured holdout dataset")
    ordinary = build_split_manifest(dataset, cfg, seed=seed)
    validate_split_manifest(dataset, ordinary, cfg)
    safe = sanitize_holdout_manifest(ordinary)
    output_dir = output_root / "concealment_tests" / dataset.name
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / f"development_concealed_seed_{seed}.csv"
    metadata_path = manifest_path.with_suffix(".json")
    safe.to_csv(manifest_path, index=False)
    manifest_sha256 = _sha256_file(manifest_path)
    metadata = _concealed_metadata(
        safe,
        manifest_sha256=manifest_sha256,
        purpose="development_control_test_only",
    )
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    validate_concealed_manifest_files(manifest_path)
    return manifest_path, metadata_path, metadata


def write_final_concealed_manifest(
    dataset: LoadedDataset,
    *,
    profile: dict[str, Any],
    protocol_path: Path | str = DEFAULT_PROTOCOL_PATH,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> tuple[Path, Path, dict[str, Any]]:
    """Create one authorized outcome-blind final manifest without enabling access."""

    protocol_path = Path(protocol_path).resolve()
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    analysis = dict(protocol.get("analysis_plan", {}))
    failures: list[str] = []
    if not bool(protocol.get("protocol_frozen", False)):
        failures.append("protocol_frozen=false")
    if str(analysis.get("status")) != "frozen":
        failures.append("analysis_plan.status is not frozen")
    if not bool(analysis.get("final_split_creation_authorized", False)):
        failures.append("final split creation is not authorized")
    if bool(analysis.get("final_execution_authorized", False)):
        failures.append("final execution must remain unauthorized during split creation")
    if str(profile.get("name")) != "final":
        failures.append("loaded experiment profile is not named final")
    if not bool(profile.get("locked", False)):
        failures.append("final experiment profile is not locked")
    seed = analysis.get("final_holdout_seed")
    if seed is None:
        failures.append("final holdout seed is not configured")
    elif int(seed) == 42:
        failures.append("seed 42 is permanently reserved for development evidence")
    elif int(seed) != int(profile.get("seed", -1)):
        failures.append("profile seed does not match the authorized final holdout seed")
    if analysis.get("final_holdout_manifest") or analysis.get(
        "final_holdout_manifest_sha256"
    ):
        failures.append("a final holdout manifest is already registered")
    if failures:
        raise RuntimeError("Final manifest creation denied: " + "; ".join(failures))

    cfg = get_dataset_config(dataset.name)
    if cfg["evaluation_strategy"] not in {
        "stratified_holdout_cv",
        "stratified_group_holdout_cv",
    }:
        raise ValueError("Final concealment requires a configured holdout dataset")
    ordinary = build_split_manifest(dataset, cfg, seed=int(seed))
    validate_split_manifest(dataset, ordinary, cfg)
    safe = sanitize_holdout_manifest(ordinary)
    output_dir = output_root / "final_concealed" / dataset.name
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / f"final_concealed_seed_{seed}.csv"
    metadata_path = manifest_path.with_suffix(".json")
    if manifest_path.exists() or metadata_path.exists():
        raise RuntimeError("Final concealed manifest already exists; overwrite is prohibited")

    temporary_manifest = manifest_path.with_suffix(".csv.tmp")
    temporary_metadata = metadata_path.with_suffix(".json.tmp")
    safe.to_csv(temporary_manifest, index=False)
    manifest_sha256 = _sha256_file(temporary_manifest)
    metadata = _concealed_metadata(
        safe,
        manifest_sha256=manifest_sha256,
        purpose="final_locked_holdout",
    )
    temporary_metadata.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary_manifest, manifest_path)
    os.replace(temporary_metadata, metadata_path)
    validate_concealed_manifest_files(manifest_path)
    return manifest_path, metadata_path, metadata


def assert_final_execution_authorized(
    *,
    profile_name: str,
    profile: dict[str, Any],
    dataset_name: str | None = None,
    raw_data_sha256: str | None = None,
    analysis_configuration_sha256: str | None = None,
    requires_concealed_holdout: bool = True,
    protocol_path: Path | str = DEFAULT_PROTOCOL_PATH,
) -> Path | None:
    """Fail closed unless every final holdout authorization control is present."""

    if profile_name == "smoke":
        return None
    failures: list[str] = []
    try:
        validate_final_profile(profile)
    except ValueError as exc:
        failures.append(str(exc))
    if profile_name != "final":
        failures.append("holdout scientific execution requires the final profile")
    if str(profile.get("name")) != "final":
        failures.append("loaded experiment profile is not named final")
    if not bool(profile.get("locked", False)):
        failures.append("final experiment profile is not locked")

    protocol_path = Path(protocol_path).resolve()
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    analysis = dict(protocol.get("analysis_plan", {}))
    required_flags = (
        "protocol_frozen",
        "novelty_review_complete",
        "ablation_study_complete",
        "selective_prediction_evaluation_complete",
        "subgroup_analysis_complete",
    )
    failures.extend(
        f"{flag}=false" for flag in required_flags if not bool(protocol.get(flag, False))
    )
    if str(analysis.get("status")) != "frozen":
        failures.append("analysis_plan.status is not frozen")
    if not bool(analysis.get("final_execution_authorized", False)):
        failures.append("final execution is not authorized")
    authorized_hashes = dict(analysis.get("final_raw_data_sha256", {}))
    authorized_analysis_hashes = dict(
        analysis.get("final_analysis_configuration_sha256", {})
    )
    if dataset_name is not None:
        authorized_raw_hash = authorized_hashes.get(dataset_name)
        if not authorized_raw_hash:
            failures.append(
                f"authorized raw-data SHA-256 is not configured for {dataset_name}"
            )
        elif raw_data_sha256 != str(authorized_raw_hash):
            failures.append(
                f"raw-data SHA-256 does not match authorization for {dataset_name}"
            )
        authorized_analysis_hash = authorized_analysis_hashes.get(dataset_name)
        if not authorized_analysis_hash:
            failures.append(
                f"authorized analysis-configuration SHA-256 is not configured for {dataset_name}"
            )
        elif analysis_configuration_sha256 != str(authorized_analysis_hash):
            failures.append(
                f"analysis-configuration SHA-256 does not match authorization for {dataset_name}"
            )
    configured_seed = analysis.get("final_holdout_seed")
    if requires_concealed_holdout and (
        configured_seed is None
        or int(configured_seed) != int(profile.get("seed", -1))
    ):
        failures.append("profile seed does not match the authorized final holdout seed")

    authorization_path = analysis.get("final_authorization_record")
    authorization_sha256 = analysis.get("final_authorization_record_sha256")
    if not authorization_path:
        failures.append("final authorization record is not configured")
    else:
        authorization = Path(authorization_path)
        authorization = (
            authorization
            if authorization.is_absolute()
            else PROJECT_ROOT / authorization
        )
        if not authorization.exists():
            failures.append("final authorization record does not exist")
        elif not authorization_sha256:
            failures.append("final authorization record SHA-256 is not configured")
        elif _sha256_file(authorization) != str(authorization_sha256):
            failures.append("final authorization record checksum does not match")

    manifest_path: Path | None = None
    if requires_concealed_holdout:
        manifest_value = analysis.get("final_holdout_manifest")
        manifest_sha256 = analysis.get("final_holdout_manifest_sha256")
        if not manifest_value or not manifest_sha256:
            failures.append("final concealed manifest path/hash is not configured")
        else:
            manifest_path = Path(manifest_value)
            manifest_path = (
                manifest_path
                if manifest_path.is_absolute()
                else PROJECT_ROOT / manifest_path
            )
            try:
                _, _, manifest_metadata = validate_concealed_manifest_files(
                    manifest_path, expected_sha256=str(manifest_sha256)
                )
                if (
                    dataset_name is not None
                    and str(manifest_metadata.get("dataset")) != dataset_name
                ):
                    failures.append(
                        "final concealed manifest dataset does not match request"
                    )
                if configured_seed is not None and int(
                    manifest_metadata.get("seed", -1)
                ) != int(configured_seed):
                    failures.append(
                        "final concealed manifest seed does not match authorization"
                    )
                if str(manifest_metadata.get("purpose")) != "final_locked_holdout":
                    failures.append(
                        "final concealed manifest purpose is not final_locked_holdout"
                    )
            except (FileNotFoundError, RuntimeError) as exc:
                failures.append(str(exc))

    if failures:
        raise RuntimeError("Final study execution denied: " + "; ".join(failures))
    return manifest_path.resolve() if manifest_path is not None else None


def load_authorized_concealed_manifest(
    manifest_path: Path | str,
    dataset: LoadedDataset,
) -> pd.DataFrame:
    """Load a checksum-validated role manifest and attach labels only in memory."""

    manifest_path, _, _ = validate_concealed_manifest_files(manifest_path)
    manifest = pd.read_csv(manifest_path)
    positions = manifest["row_position"].to_numpy(dtype=int)
    if len(manifest) != len(dataset.X) or set(positions) != set(range(len(dataset.X))):
        raise RuntimeError("Concealed manifest does not cover the loaded dataset exactly")
    expected_rows = dataset.row_ids.iloc[positions].astype(str).to_numpy()
    if not (manifest["row_id"].astype(str).to_numpy() == expected_rows).all():
        raise RuntimeError("Concealed manifest row identities do not match the dataset")
    manifest["target"] = dataset.y.iloc[positions].to_numpy(dtype=int)
    cfg = get_dataset_config(dataset.name)
    validate_split_manifest(dataset, manifest, cfg)
    return manifest
