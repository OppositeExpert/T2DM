#!/usr/bin/env python3
"""Build the tracked evidence registry from local authoritative study artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform

import yaml


ROOT = Path(__file__).resolve().parents[1]
STUDIES = ROOT / "outputs" / "publication_pipeline" / "studies"
CONFIG = ROOT / "config" / "authoritative_studies.yaml"
OUTPUT = ROOT / "evidence" / "study_registry.json"

ARTIFACTS = {
    "metadata": "experiment_metadata.json",
    "metrics": "summary_metrics.csv",
    "predictions_nested_cv": "participant_predictions.csv",
    "predictions_holdout": "test_predictions.csv",
    "confidence_intervals": "confidence_intervals.csv",
    "participant_confidence_intervals": "participant_confidence_intervals.csv",
    "paired_comparisons_holdout": "paired_bootstrap_model_comparisons.csv",
    "paired_comparisons_nested_cv": "participant_paired_model_comparisons.csv",
    "calibration_selection": "calibration_selection.csv",
    "thresholds": "selected_thresholds.csv",
    "decision_curves": "decision_curves.csv",
    "decision_curve_intervals": "decision_curve_confidence_intervals.csv",
    "decision_curve_comparisons": "decision_curve_paired_contrasts.csv",
    "routing_metrics": "availability_routing/summary_metrics.csv",
    "routing_predictions": "availability_routing/system_predictions.csv",
    "matched_panel_comparisons": "availability_routing/matched_panel_contrasts.csv",
    "artifact_ablation": "ablations/ablation_inventory.json",
    "selective_prediction": "selective_prediction/risk_coverage_metrics.csv",
    "subgroup_analysis": "subgroup_analysis/subgroup_metrics.csv",
    "survey_sensitivity": "survey_sensitivity/survey_weighted_metrics.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_record(study: Path, relative: str) -> dict[str, object]:
    path = study / relative
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "tracked_in_git": False,
        "present_locally": path.exists(),
        "bytes": path.stat().st_size if path.exists() else None,
        "sha256": sha256(path) if path.exists() else None,
        "regeneration_required_after_clone": True,
    }


def analysis_configuration_record(metadata: dict[str, object]) -> tuple[str, str]:
    recorded = metadata.get("analysis_configuration_sha256")
    if recorded:
        return str(recorded), "study_metadata"
    # Older completed studies predate the dedicated analysis hash. Preserve that
    # fact while supplying a deterministic registry descriptor from the exact
    # configuration-bearing metadata that is available.
    payload = {
        "dataset_configuration_sha256": metadata.get(
            "dataset_configuration_sha256"
        ),
        "profile": metadata.get("profile"),
        "models": metadata.get("models"),
        "split_manifest_sha256": metadata.get("split_manifest_sha256"),
        "source_tree_sha256": metadata.get("source_tree_sha256"),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return digest, "registry_reconstructed_from_study_metadata"


def test_access_record(metadata: dict[str, object]) -> str:
    recorded = metadata.get("test_access")
    if recorded:
        return str(recorded)
    if metadata.get("primary_repeated_cv_inference"):
        return "repeated_outer_evaluation_no_single_concealed_test"
    return "not_recorded_in_legacy_study_metadata"


def main() -> None:
    configured = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    dataset_contracts = yaml.safe_load(
        (ROOT / "config" / "datasets.yaml").read_text(encoding="utf-8")
    )["datasets"]
    registry: dict[str, object] = {
        "schema_version": "2.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_scope": "final_internal_validation_and_historical_engineering",
        "protocol_id": configured.get("protocol_id"),
        "independent_holdout_claim_allowed": bool(
            configured.get("independent_holdout_claim_allowed", False)
        ),
        "canonical_results": configured.get("canonical_results"),
        "requirements_lock_sha256": sha256(ROOT / "requirements.lock"),
        "environment_used_to_build_registry": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "large_artifact_policy": (
            "Study outputs and model bundles remain ignored. This tracked registry "
            "identifies their hashes and regeneration commands but does not replace them."
        ),
        "studies": {},
        "historical_engineering_studies": configured.get(
            "historical_engineering_studies", {}
        ),
    }
    for dataset, declaration in configured["studies"].items():
        study_id = str(declaration["study_id"])
        study = STUDIES / study_id
        metadata_path = study / "experiment_metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Authoritative study is incomplete: {metadata_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("dataset") != dataset or metadata.get("experiment_id") != study_id:
            raise RuntimeError(f"Study identity mismatch for {study_id}")
        artifacts = {
            name: artifact_record(study, relative)
            for name, relative in ARTIFACTS.items()
        }
        shap_relative = (
            "test_explanations/global_shap_importance_original_features.csv"
            if str(metadata.get("runner", "")).endswith("holdout")
            else "explanations/global_shap_importance_original_features.csv"
        )
        artifacts["shap_original_features"] = artifact_record(
            study, shap_relative
        )
        model_bundles = {
            path.stem: artifact_record(study, path.relative_to(study).as_posix())
            for path in sorted((study / "models").glob("*.joblib"))
        }
        analysis_hash, analysis_hash_origin = analysis_configuration_record(metadata)
        registry["studies"][dataset] = {
            "study_id": study_id,
            "dataset": dataset,
            "endpoint": metadata.get("endpoint")
            or dataset_contracts[dataset].get("endpoint"),
            "evidence_tier": declaration["evidence_tier"],
            "execution_profile": metadata.get("profile", {}).get("name"),
            "command": declaration["command"],
            "study_directory": study.relative_to(ROOT).as_posix(),
            "created_at_utc": metadata.get("run_started_at_utc")
            or datetime.fromtimestamp(
                metadata_path.stat().st_mtime, timezone.utc
            ).isoformat(),
            "updated_at_utc": metadata.get("run_completed_at_utc") or datetime.fromtimestamp(
                metadata_path.stat().st_mtime, timezone.utc
            ).isoformat(),
            "dataset_configuration_sha256": metadata.get(
                "dataset_configuration_sha256"
            ),
            "raw_data_sha256": metadata.get("raw_data_sha256"),
            "split_manifest_sha256": metadata.get("split_manifest_sha256"),
            "source_tree_sha256": metadata.get("source_tree_sha256"),
            "analysis_configuration_sha256": analysis_hash,
            "analysis_configuration_hash_origin": analysis_hash_origin,
            "manifest_sha256": metadata.get("split_manifest_sha256"),
            "requirements_lock_sha256": registry["requirements_lock_sha256"],
            "profile_locked": bool(metadata.get("profile", {}).get("locked", False)),
            "test_access": test_access_record(metadata),
            "eligible_for_final_internal_validation_claims": (
                declaration["evidence_tier"] == "final_internal_validation"
            ),
            "independent_holdout_claim_allowed": False,
            "artifacts": artifacts,
            "model_bundles": model_bundles,
        }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
