"""Machine-readable publication-readiness audit for frozen study artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from diabetes_pipeline.settings import PROJECT_ROOT, source_tree_sha256


DEFAULT_PROTOCOL_PATH = PROJECT_ROOT / "config" / "publication_protocol.yaml"


def _check(
    identifier: str,
    passed: bool,
    evidence: str,
    remediation: str,
    *,
    severity: str = "blocker",
) -> dict[str, Any]:
    return {
        "id": identifier,
        "status": "pass" if passed else ("warn" if severity == "warning" else "fail"),
        "severity": severity,
        "evidence": evidence,
        "remediation": "" if passed else remediation,
    }


def audit_publication_readiness(
    study_dirs: Iterable[Path | str],
    *,
    protocol_path: Path | str = DEFAULT_PROTOCOL_PATH,
) -> dict[str, Any]:
    """Audit whether supplied artifacts meet the frozen conference-study gate."""

    protocol_path = Path(protocol_path).resolve()
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    resolved = [Path(path).resolve() for path in study_dirs]
    if not resolved:
        raise ValueError("At least one study directory is required")

    metadata_by_dataset: dict[str, tuple[Path, dict[str, Any]]] = {}
    duplicate_datasets: list[str] = []
    for study_dir in resolved:
        metadata_path = study_dir / "experiment_metadata.json"
        if not metadata_path.exists():
            raise FileNotFoundError(f"Missing experiment metadata: {metadata_path}")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        dataset = str(metadata["dataset"])
        if dataset in metadata_by_dataset:
            duplicate_datasets.append(dataset)
        metadata_by_dataset[dataset] = (study_dir, metadata)

    checks: list[dict[str, Any]] = []
    expected = set(str(value) for value in protocol["primary_datasets"])
    supplied = set(metadata_by_dataset)
    checks.append(
        _check(
            "primary_dataset_coverage",
            supplied == expected and not duplicate_datasets,
            f"expected={sorted(expected)} supplied={sorted(supplied)} duplicates={sorted(duplicate_datasets)}",
            "Supply exactly one frozen study for each primary screening dataset.",
        )
    )

    for dataset in sorted(expected & supplied):
        study_dir, metadata = metadata_by_dataset[dataset]
        profile = dict(metadata.get("profile", {}))
        profile_name = str(profile.get("name", "unknown"))
        checks.append(
            _check(
                f"{dataset}_final_profile",
                profile_name == "final",
                f"profile={profile_name}",
                "Run the full prespecified final profile; pilot and smoke estimates cannot enter the paper's primary table.",
            )
        )
        checks.append(
            _check(
                f"{dataset}_profile_locked",
                bool(profile.get("locked", False)),
                f"locked={bool(profile.get('locked', False))}",
                "Freeze the protocol and set locked=true before the one permitted final run.",
            )
        )
        sample_limit = metadata.get("sample_limit_per_partition")
        checks.append(
            _check(
                f"{dataset}_full_sample",
                sample_limit is None,
                f"sample_limit_per_partition={sample_limit}",
                "Use the complete prespecified cohort rather than a smoke sample.",
            )
        )
        test_access = str(metadata.get("test_access", "not_applicable"))
        checks.append(
            _check(
                f"{dataset}_test_access",
                not test_access.startswith("smoke"),
                f"test_access={test_access}",
                "Create a fresh locked final study whose test set is accessed only after every choice is frozen.",
            )
        )

        runner = str(metadata.get("runner", "nested_cv"))
        required = [
            "confidence_intervals.csv",
            "decision_curves.csv",
            "decision_curve_confidence_intervals.csv",
            "decision_curve_paired_contrasts.csv",
            "availability_routing/summary_metrics.csv",
            "availability_routing/router_selections.csv",
        ]
        if dataset == "brfss":
            required.extend(
                [
                    "survey_sensitivity/survey_weighted_metrics.csv",
                    "survey_sensitivity/survey_weighted_confidence_intervals.csv",
                    "survey_sensitivity/survey_design_diagnostics.json",
                    "survey_sensitivity/survey_sensitivity_report.md",
                ]
            )
        if runner == "development_locked_holdout":
            required.extend(
                ["test_predictions.csv", "paired_bootstrap_model_comparisons.csv"]
            )
        else:
            required.extend(
                [
                    "predictions.csv",
                    "paired_model_comparisons.csv",
                    "participant_predictions.csv",
                    "participant_confidence_intervals.csv",
                    "participant_paired_model_comparisons.csv",
                ]
            )
        missing = [relative for relative in required if not (study_dir / relative).exists()]
        checks.append(
            _check(
                f"{dataset}_required_artifacts",
                not missing,
                f"missing={missing}",
                "Regenerate the complete metrics, uncertainty, comparison, decision-curve, and routing artifact set.",
            )
        )

    protocol_requirements = {
        "protocol_frozen": "Approve and freeze the statistical analysis plan before final execution.",
        "novelty_review_complete": "Complete the structured literature matrix and narrow the novelty claim.",
        "claim_evidence_table_complete": "Link every abstract/conclusion claim to a frozen result, figure, or citation.",
        "tripod_ai_checklist_complete": "Complete the TRIPOD+AI checklist and manuscript crosswalk.",
        "probast_ai_assessment_complete": "Complete and disclose the PROBAST+AI risk-of-bias/applicability assessment.",
        "ablation_study_complete": "Complete the prespecified component ablations on identical folds and tuning budgets.",
        "selective_prediction_evaluation_complete": "Report risk-coverage behavior and performance at prespecified acceptance levels.",
        "subgroup_analysis_complete": "Report supported subgroup performance and abstention coverage with uncertainty.",
    }
    for key, remediation in protocol_requirements.items():
        checks.append(
            _check(
                key,
                bool(protocol.get(key, False)),
                f"{key}={bool(protocol.get(key, False))}",
                remediation,
            )
        )

    mixed_demonstration_only = (
        str(protocol.get("mixed_router_role")) == "software_demonstration_only"
        and not bool(protocol.get("cross_dataset_selector_validated", False))
    )
    checks.append(
        _check(
            "mixed_router_claim_scope",
            mixed_demonstration_only,
            (
                f"mixed_router_role={protocol.get('mixed_router_role')} "
                f"selector_validated={bool(protocol.get('cross_dataset_selector_validated', False))}"
            ),
            "Exclude automatic cross-dataset selection from efficacy claims unless it is validated on matched multi-environment patients.",
        )
    )
    dynamic_selection_scoped = (
        str(protocol.get("dynamic_model_selection_role"))
        == "secondary_negative_result"
    )
    checks.append(
        _check(
            "dynamic_model_selection_claim_scope",
            dynamic_selection_scoped,
            f"dynamic_model_selection_role={protocol.get('dynamic_model_selection_role')}",
            "Do not claim algorithm switching is superior unless the locked paired analysis demonstrates a prespecified meaningful benefit.",
        )
    )
    checks.append(
        _check(
            "external_or_temporal_validation",
            bool(protocol.get("external_or_temporal_validation_complete", False)),
            (
                "external_or_temporal_validation_complete="
                f"{bool(protocol.get('external_or_temporal_validation_complete', False))}"
            ),
            "Add independent or temporal validation before journal-strength, transportability, or clinical-generalization claims.",
            severity="warning",
        )
    )

    blockers = [row for row in checks if row["status"] == "fail"]
    warnings = [row for row in checks if row["status"] == "warn"]
    return {
        "schema_version": "1.0",
        "target_readiness": str(protocol.get("target_readiness")),
        "status": "ready" if not blockers else "not_ready",
        "ready_for_submission": not blockers,
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
        "checks": checks,
        "blockers": [row["id"] for row in blockers],
        "warnings": [row["id"] for row in warnings],
        "protocol_path": str(protocol_path),
        "study_directories": [str(path) for path in resolved],
        "pipeline_source_tree_sha256": source_tree_sha256(),
    }


def render_publication_readiness_markdown(result: dict[str, Any]) -> str:
    verdict = "READY" if result["ready_for_submission"] else "NOT READY"
    lines = [
        "# Publication Readiness Audit",
        "",
        f"**Verdict:** {verdict}",
        "",
        f"**Blocking checks:** {result['blocker_count']}",
        "",
        f"**Warnings:** {result['warning_count']}",
        "",
        "| Check | Status | Evidence | Required action |",
        "|---|---|---|---|",
    ]
    for row in result["checks"]:
        evidence = str(row["evidence"]).replace("|", "\\|")
        remediation = str(row["remediation"]).replace("|", "\\|")
        lines.append(
            f"| `{row['id']}` | **{str(row['status']).upper()}** | "
            f"{evidence} | {remediation} |"
        )
    lines.extend(
        [
            "",
            "A passing software test suite is necessary but not sufficient for a "
            "publishable clinical-prediction study. Final locked experiments, a "
            "frozen protocol, claim-to-evidence traceability, and reporting/bias "
            "checklists are separate requirements.",
            "",
        ]
    )
    return "\n".join(lines)
