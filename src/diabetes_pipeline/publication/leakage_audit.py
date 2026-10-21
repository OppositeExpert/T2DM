"""Executable leakage and provenance checks for final publication studies."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
from sklearn.exceptions import NotFittedError
from sklearn.utils.validation import check_is_fitted

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.preprocessing.builders import build_preprocessor
from diabetes_pipeline.settings import PROJECT_ROOT, get_dataset_config
from diabetes_pipeline.splitting.registry import (
    create_and_write_split_manifest,
    validate_split_manifest,
)


@dataclass(frozen=True)
class LeakageAuditResult:
    output_dir: Path
    json_path: Path
    markdown_path: Path
    passed: bool


def _check(
    checks: list[dict[str, Any]],
    identifier: str,
    passed: bool,
    evidence: str,
) -> None:
    checks.append(
        {
            "id": identifier,
            "status": "pass" if passed else "fail",
            "evidence": evidence,
        }
    )


def _group_overlap(manifest: pd.DataFrame, strategy: str) -> int:
    if strategy == "stratified_group_holdout_cv":
        development = set(
            manifest.loc[manifest["role"] == "development", "group_id"].astype(str)
        )
        test = set(manifest.loc[manifest["role"] == "test", "group_id"].astype(str))
        return len((development & test) - {""})
    if strategy == "repeated_nested_stratified_group_cv":
        maximum = 0
        for _, frame in manifest.groupby(["repeat", "outer_fold"]):
            training = set(
                frame.loc[frame["role"] == "train", "group_id"].astype(str)
            )
            validation = set(
                frame.loc[frame["role"] == "validation", "group_id"].astype(str)
            )
            maximum = max(maximum, len((training & validation) - {""}))
        return maximum
    return 0


def run_final_leakage_audit(
    study_dirs: Mapping[str, Path | str],
    *,
    output_dir: Path | str = PROJECT_ROOT / "results" / "final_publication" / "audits",
) -> LeakageAuditResult:
    """Run data, split, preprocessing, study, SHAP, and policy checks."""

    expected_datasets = {"pidd", "sylhet", "brfss", "hospital130"}
    if set(study_dirs) != expected_datasets:
        raise ValueError(
            "Leakage audit requires exactly pidd, sylhet, brfss, and hospital130"
        )
    checks: list[dict[str, Any]] = []
    datasets: dict[str, Any] = {}
    manifests: dict[str, pd.DataFrame] = {}
    for name in sorted(expected_datasets):
        dataset = load_dataset(name)
        cfg = get_dataset_config(name)
        split_path, _, manifest = create_and_write_split_manifest(
            dataset, seed=42
        )
        validate_split_manifest(dataset, manifest, cfg)
        datasets[name] = dataset
        manifests[name] = manifest
        _check(
            checks,
            f"{name}_split_identity_binding",
            True,
            f"{len(manifest)} rows validated against {split_path}",
        )
        overlap = _group_overlap(manifest, str(cfg["evaluation_strategy"]))
        _check(
            checks,
            f"{name}_group_boundary",
            overlap == 0,
            f"maximum prohibited-boundary group overlap={overlap}",
        )
        preprocessor = build_preprocessor(cfg, "logistic_regression")
        try:
            check_is_fitted(preprocessor)
            unfitted = False
        except NotFittedError:
            unfitted = True
        _check(
            checks,
            f"{name}_preprocessor_factory_unfitted",
            unfitted,
            "preprocessing factory returned an unfitted graph",
        )

    pidd = datasets["pidd"]
    zero_fields = get_dataset_config("pidd")["zero_as_missing"]
    surviving_zeros = int((pidd.X[zero_fields] == 0).sum().sum())
    _check(
        checks,
        "pidd_zero_sentinel_handling",
        surviving_zeros == 0,
        f"surviving physiological zero sentinels={surviving_zeros}",
    )

    sylhet = datasets["sylhet"]
    unique_profiles = int(sylhet.X.astype(str).drop_duplicates().shape[0])
    unique_groups = int(sylhet.groups.astype(str).nunique())
    _check(
        checks,
        "sylhet_identical_profile_grouping",
        unique_profiles == unique_groups,
        f"unique predictor profiles={unique_profiles}, unique groups={unique_groups}",
    )

    for name in ("brfss", "hospital130"):
        manifest = manifests[name]
        development = set(
            manifest.loc[manifest["role"] == "development", "row_position"]
        )
        test = set(manifest.loc[manifest["role"] == "test", "row_position"])
        _check(
            checks,
            f"{name}_partition_position_disjointness",
            not (development & test),
            f"position overlap={len(development & test)}; evidence remains internal validation",
        )

    hospital = datasets["hospital130"]
    _check(
        checks,
        "hospital130_encounter_identity",
        hospital.row_ids.astype(str).is_unique,
        f"encounters={len(hospital.row_ids)}, unique={hospital.row_ids.nunique()}",
    )

    for name, raw_path in sorted(study_dirs.items()):
        study = Path(raw_path).resolve()
        metadata_path = study / "experiment_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        profile = dict(metadata.get("profile", {}))
        cfg = get_dataset_config(name)
        identity_ok = (
            metadata.get("dataset") == name
            and metadata.get("task") in {None, cfg["task"]}
            and metadata.get("endpoint") in {None, cfg["endpoint"]}
            and metadata.get("evidence_tier") == "final_internal_validation"
            and metadata.get("evaluation_role") == "locked_internal_validation"
            and metadata.get("protocol_id") == "t2dm-final-internal-validation-v1"
        )
        _check(
            checks,
            f"{name}_final_identity",
            identity_ok,
            (
                f"dataset={metadata.get('dataset')}, endpoint={metadata.get('endpoint')}, "
                f"tier={metadata.get('evidence_tier')}, role={metadata.get('evaluation_role')}"
            ),
        )
        budget_ok = (
            profile.get("name") == "final_internal_validation"
            and profile.get("n_trials") == 75
            and profile.get("n_bootstrap") == 2000
            and profile.get("locked") is True
            and all(
                value is None for value in profile.get("sample_limits", {}).values()
            )
        )
        _check(
            checks,
            f"{name}_final_budgets",
            budget_ok,
            f"profile={profile.get('name')}, trials={profile.get('n_trials')}, bootstrap={profile.get('n_bootstrap')}",
        )
        required = [
            study / "confidence_intervals.csv",
            study / "calibration_selection.csv",
            study / "selected_thresholds.csv",
            study / "decision_curves.csv",
            study / "availability_routing" / "summary_metrics.csv",
            study / "runtime_policy_evaluation" / "policy_metrics.csv",
            study / "runtime_policy_evaluation" / "policy_paired_comparisons.csv",
            study / "selective_prediction" / "risk_coverage_metrics.csv",
            study / "subgroup_analysis" / "subgroup_metrics.csv",
        ]
        explanation_dir = (
            study / "test_explanations"
            if metadata.get("runner") == "locked_internal_validation_holdout"
            else study / "explanations"
        )
        required.extend(
            [
                explanation_dir / "global_shap_importance_original_features.csv",
                explanation_dir / "shap_reconstruction_checks.csv",
            ]
        )
        absent = [str(path.relative_to(study)) for path in required if not path.exists() or path.stat().st_size == 0]
        _check(
            checks,
            f"{name}_required_final_artifacts",
            not absent,
            "missing_or_empty=" + (", ".join(absent) if absent else "none"),
        )
        interval_path = study / "confidence_intervals.csv"
        interval_columns = set(pd.read_csv(interval_path, nrows=1).columns)
        replicate_columns = {"valid_replicates", "failed_replicates", "interval_status"}
        _check(
            checks,
            f"{name}_bootstrap_accounting",
            replicate_columns.issubset(interval_columns),
            f"columns_present={sorted(replicate_columns & interval_columns)}",
        )
        reconstruction_path = explanation_dir / "shap_reconstruction_checks.csv"
        if reconstruction_path.exists():
            reconstruction = pd.read_csv(reconstruction_path)
            maximum = float(reconstruction["maximum_absolute_reconstruction_error"].max())
        else:
            maximum = float("inf")
        _check(
            checks,
            f"{name}_shap_reconstruction",
            maximum <= 1e-4,
            f"maximum_absolute_error={maximum}",
        )

    passed = all(row["status"] == "pass" for row in checks)
    payload = {
        "schema_version": "1.0",
        "status": "pass" if passed else "fail",
        "passed": passed,
        "check_count": len(checks),
        "failed_checks": [row["id"] for row in checks if row["status"] == "fail"],
        "claim_boundary": "finalized internal validation; not external, temporal, prospective, clinical, or causal validation",
        "checks": checks,
    }
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "FINAL_DATA_LEAKAGE_AUDIT.json"
    markdown_path = output_dir / "FINAL_DATA_LEAKAGE_AUDIT.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Final End-to-End Leakage Audit",
        "",
        f"**Verdict:** {'PASS' if passed else 'FAIL'}",
        "",
        "**Evidence boundary:** finalized internal validation; not external, temporal, prospective, clinical, or causal validation.",
        "",
        "| Check | Status | Evidence |",
        "|---|---|---|",
    ]
    for row in checks:
        evidence = str(row["evidence"]).replace("|", "\\|")
        lines.append(f"| `{row['id']}` | **{row['status'].upper()}** | {evidence} |")
    lines.append("")
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return LeakageAuditResult(output_dir, json_path, markdown_path, passed)
