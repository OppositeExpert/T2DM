"""Canonical, fail-closed publication-results exporter."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

import pandas as pd
import yaml

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.publication.figure import build_consolidated_figure
from diabetes_pipeline.publication.protocol_correction import (
    verified_benchmark_tables, publication_panel_source, publication_panel_intervals,
)
from diabetes_pipeline.publication.governance import (
    DEFAULT_FINAL_PUBLICATION_PROTOCOL,
    final_protocol_sha256,
)
from diabetes_pipeline.publication.leakage_audit import run_final_leakage_audit
from diabetes_pipeline.settings import PROJECT_ROOT, get_dataset_config, source_tree_sha256


EXPECTED_DATASETS = ("pidd", "sylhet", "brfss", "hospital130")


@dataclass(frozen=True)
class FinalPublicationResult:
    output_dir: Path
    master_path: Path
    summary_path: Path
    figure_paths: tuple[Path, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join(["---"] * len(columns)) + "|",
    ]
    for row in frame.itertuples(index=False, name=None):
        values = []
        for value in row:
            if isinstance(value, float):
                values.append("" if pd.isna(value) else f"{value:.6g}")
            else:
                values.append(str(value).replace("|", "\\|"))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def _latex_escape(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.4f}"
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in str(value))


def _latex_table(frame: pd.DataFrame) -> str:
    columns = " & ".join(_latex_escape(column) for column in frame.columns)
    rows = [
        r"\begin{tabular}{" + ("l" * len(frame.columns)) + "}",
        r"\hline",
        columns + r" \\",
        r"\hline",
    ]
    for row in frame.itertuples(index=False, name=None):
        rows.append(" & ".join(_latex_escape(value) for value in row) + r" \\")
    rows.extend((r"\hline", r"\end{tabular}"))
    return "\n".join(rows) + "\n"


def _write_table(frame: pd.DataFrame, directory: Path, name: str) -> list[Path]:
    csv_path = directory / f"{name}.csv"
    markdown_path = directory / f"{name}.md"
    latex_path = directory / f"{name}.tex"
    frame.to_csv(csv_path, index=False)
    markdown_path.write_text(_markdown_table(frame), encoding="utf-8")
    latex_path.write_text(_latex_table(frame), encoding="utf-8")
    return [csv_path, markdown_path, latex_path]


def _attach_endpoint_context(
    frame: pd.DataFrame,
    *,
    dataset: str,
    task: str,
    endpoint: str,
) -> pd.DataFrame:
    """Add endpoint identity once and reject contradictory source artifacts."""

    frame = frame.copy()
    context = {
        "dataset": dataset,
        "task": task,
        "endpoint": endpoint,
    }
    for column, expected in context.items():
        if column in frame:
            observed = set(frame[column].dropna().astype(str).unique())
            if observed and observed != {str(expected)}:
                raise RuntimeError(
                    f"Source artifact has contradictory {column}: "
                    f"expected {expected!r}, observed {sorted(observed)!r}"
                )
        else:
            frame[column] = expected
    ordered = [*context, *(column for column in frame if column not in context)]
    return frame.loc[:, ordered]


def _validate_studies(
    study_dirs: Mapping[str, Path | str], protocol: dict[str, Any]
) -> dict[str, tuple[Path, dict[str, Any]]]:
    if tuple(sorted(study_dirs)) != tuple(sorted(EXPECTED_DATASETS)):
        raise ValueError("Publication export requires all four endpoint-separated datasets")
    if protocol.get("status") != "frozen":
        raise RuntimeError("Publication export requires a frozen protocol")
    if protocol.get("protocol_sha256") != final_protocol_sha256(protocol):
        raise RuntimeError("Frozen protocol checksum is invalid")
    validated: dict[str, tuple[Path, dict[str, Any]]] = {}
    for dataset_name in EXPECTED_DATASETS:
        study = Path(study_dirs[dataset_name]).resolve()
        metadata = json.loads(
            (study / "experiment_metadata.json").read_text(encoding="utf-8")
        )
        cfg = get_dataset_config(dataset_name)
        profile = dict(metadata.get("profile", {}))
        failures = []
        if metadata.get("dataset") != dataset_name:
            failures.append("dataset")
        if metadata.get("task") != cfg["task"] or metadata.get("endpoint") != cfg["endpoint"]:
            failures.append("endpoint")
        if metadata.get("protocol_id") != protocol["protocol_id"]:
            failures.append("protocol_id")
        if metadata.get("evidence_tier") != "final_internal_validation":
            failures.append("evidence_tier")
        if metadata.get("evaluation_role") != "locked_internal_validation":
            failures.append("evaluation_role")
        if profile.get("name") != "final_internal_validation" or profile.get("locked") is not True:
            failures.append("locked_profile")
        if profile.get("n_trials") != 75 or profile.get("n_bootstrap") != 2000:
            failures.append("final_budgets")
        if any(value is not None for value in profile.get("sample_limits", {}).values()):
            failures.append("sample_limits")
        bindings = protocol["frozen_bindings"]
        for key in (
            "raw_data_sha256",
            "split_manifest_sha256",
            "dataset_configuration_sha256",
            "analysis_configuration_sha256",
        ):
            if metadata.get(key) != bindings[key].get(dataset_name):
                failures.append(key)
        if metadata.get("source_tree_sha256") != bindings["source_tree_sha256"]:
            failures.append("source_tree_sha256")
        if metadata.get("requirements_lock_sha256") != bindings["requirements_lock_sha256"]:
            failures.append("requirements_lock_sha256")
        if dataset_name in {"brfss", "hospital130"} and "not_independent" not in str(metadata.get("test_access")):
            failures.append("internal_validation_disclosure")
        if failures:
            raise RuntimeError(
                f"{dataset_name} is not eligible for publication export: {sorted(set(failures))}"
            )
        validated[dataset_name] = (study, metadata)
    return validated


def export_final_publication_results(
    study_dirs: Mapping[str, Path | str],
    *,
    output_dir: Path | str = PROJECT_ROOT / "results" / "final_publication",
    protocol_path: Path | str = DEFAULT_FINAL_PUBLICATION_PROTOCOL,
) -> FinalPublicationResult:
    """Generate all canonical tables, figures, summaries, and provenance."""

    protocol_path = Path(protocol_path).resolve()
    protocol = yaml.safe_load(protocol_path.read_text(encoding="utf-8"))
    validated = _validate_studies(study_dirs, protocol)
    output_dir = Path(output_dir).resolve()
    tables_dir = output_dir / "tables"
    figure_dir = output_dir / "figure"
    provenance_dir = output_dir / "provenance"
    for path in (tables_dir, figure_dir, provenance_dir):
        path.mkdir(parents=True, exist_ok=True)

    characteristics = []
    full_performance = []
    calibration = []
    thresholds = []
    threshold_performance = []
    performance_intervals = []
    decision_curves = []
    decision_curve_intervals = []
    decision_curve_contrasts = []
    model_comparisons = []
    availability = []
    availability_intervals = []
    routing = []
    comparisons = []
    subgroup_metrics = []
    subgroup_intervals = []
    selective_metrics = []
    selective_intervals = []
    survey_metrics = []
    survey_intervals = []
    shap_rows = []
    source_artifacts: dict[str, dict[str, str]] = {}
    for dataset_name in EXPECTED_DATASETS:
        study, metadata = validated[dataset_name]
        cfg = get_dataset_config(dataset_name)
        dataset = load_dataset(dataset_name)
        characteristics.append(
            {
                "dataset": dataset_name,
                "task": cfg["task"],
                "endpoint": cfg["endpoint"],
                "n": len(dataset.X),
                "positive_events": int(dataset.y.sum()),
                "prevalence": float(dataset.y.mean()),
                "predictor_count": len(cfg["numeric_features"]) + len(cfg["categorical_features"]),
                "grouping_unit": cfg.get("group_strategy", "none"),
                "evidence_tier": metadata["evidence_tier"],
            }
        )
        is_holdout = metadata.get("runner") == "locked_internal_validation_holdout"
        performance_path = study / ("test_metrics.csv" if is_holdout else "participant_predictions.csv")
        probability_performance, benchmark_intervals, threshold_descriptive = verified_benchmark_tables(study, metadata)
        all_performance = _attach_endpoint_context(
            probability_performance,
            dataset=dataset_name,
            task=cfg["task"],
            endpoint=cfg["endpoint"],
        )
        threshold_performance.append(_attach_endpoint_context(
            threshold_descriptive, dataset=dataset_name, task=cfg["task"], endpoint=cfg["endpoint"]
        ))
        frame = all_performance[
            all_performance["probability_version"].eq("calibrated")
            & all_performance["threshold_policy"].eq("fixed_0_5")
        ].copy()
        performance_intervals.append(
            _attach_endpoint_context(
                benchmark_intervals,
                dataset=dataset_name,
                task=cfg["task"],
                endpoint=cfg["endpoint"],
            )
        )
        decision_curves.append(
            _attach_endpoint_context(
                pd.read_csv(study / "decision_curves.csv"),
                dataset=dataset_name,
                task=cfg["task"],
                endpoint=cfg["endpoint"],
            )
        )
        decision_curve_intervals.append(
            _attach_endpoint_context(
                pd.read_csv(study / "decision_curve_confidence_intervals.csv"),
                dataset=dataset_name,
                task=cfg["task"],
                endpoint=cfg["endpoint"],
            )
        )
        decision_curve_contrasts.append(
            _attach_endpoint_context(
                pd.read_csv(study / "decision_curve_paired_contrasts.csv"),
                dataset=dataset_name,
                task=cfg["task"],
                endpoint=cfg["endpoint"],
            )
        )
        model_comparison_name = (
            "paired_bootstrap_model_comparisons.csv"
            if is_holdout
            else "participant_paired_model_comparisons.csv"
        )
        model_comparisons.append(
            _attach_endpoint_context(
                pd.read_csv(study / model_comparison_name),
                dataset=dataset_name,
                task=cfg["task"],
                endpoint=cfg["endpoint"],
            )
        )
        subgroup_metrics.append(
            _attach_endpoint_context(
                pd.read_csv(study / "subgroup_analysis" / "subgroup_metrics.csv"),
                dataset=dataset_name,
                task=cfg["task"],
                endpoint=cfg["endpoint"],
            )
        )
        subgroup_intervals.append(
            _attach_endpoint_context(
                pd.read_csv(
                    study / "subgroup_analysis" / "subgroup_confidence_intervals.csv"
                ),
                dataset=dataset_name,
                task=cfg["task"],
                endpoint=cfg["endpoint"],
            )
        )
        selective_metrics.append(
            _attach_endpoint_context(
                pd.read_csv(
                    study / "selective_prediction" / "risk_coverage_metrics.csv"
                ),
                dataset=dataset_name,
                task=cfg["task"],
                endpoint=cfg["endpoint"],
            )
        )
        selective_intervals.append(
            _attach_endpoint_context(
                pd.read_csv(
                    study
                    / "selective_prediction"
                    / "risk_coverage_confidence_intervals.csv"
                ),
                dataset=dataset_name,
                task=cfg["task"],
                endpoint=cfg["endpoint"],
            )
        )
        if dataset_name == "brfss":
            survey_metrics.append(
                _attach_endpoint_context(
                    pd.read_csv(
                        study / "survey_sensitivity" / "survey_weighted_metrics.csv"
                    ),
                    dataset=dataset_name,
                    task=cfg["task"],
                    endpoint=cfg["endpoint"],
                )
            )
            survey_intervals.append(
                _attach_endpoint_context(
                    pd.read_csv(
                        study
                        / "survey_sensitivity"
                        / "survey_weighted_confidence_intervals.csv"
                    ),
                    dataset=dataset_name,
                    task=cfg["task"],
                    endpoint=cfg["endpoint"],
                )
            )
        keep = [
            "dataset", "task", "endpoint", "model", "n", "positives", "prevalence",
            "auroc", "average_precision", "brier_score", "scaled_brier_score", "log_loss",
            "calibration_intercept", "calibration_slope", "observed_expected_ratio",
            "expected_calibration_error", "evidence_tier",
        ]
        if "evidence_tier" not in frame:
            frame["evidence_tier"] = metadata["evidence_tier"]
        full_performance.append(frame[[column for column in keep if column in frame]])

        calibration_frame = pd.read_csv(study / "calibration_selection.csv")
        calibration_frame = _attach_endpoint_context(
            calibration_frame,
            dataset=dataset_name,
            task=cfg["task"],
            endpoint=cfg["endpoint"],
        )
        calibration.append(calibration_frame)
        threshold_frame = pd.read_csv(study / "selected_thresholds.csv")
        threshold_frame = _attach_endpoint_context(
            threshold_frame,
            dataset=dataset_name,
            task=cfg["task"],
            endpoint=cfg["endpoint"],
        )
        thresholds.append(threshold_frame)

        availability_frame = publication_panel_source(study, metadata)
        availability_frame = availability_frame[
            availability_frame["system"].eq("availability_router")
        ].copy()
        full = availability_frame[availability_frame["scenario"].eq("full")]
        availability_frame["auroc_degradation_from_full"] = float(full.iloc[0]["auroc"]) - availability_frame["auroc"]
        availability_frame["average_precision_degradation_from_full"] = float(full.iloc[0]["average_precision"]) - availability_frame["average_precision"]
        availability_frame = _attach_endpoint_context(
            availability_frame,
            dataset=dataset_name,
            task=cfg["task"],
            endpoint=cfg["endpoint"],
        )
        availability.append(availability_frame)
        availability_intervals.append(_attach_endpoint_context(
            publication_panel_intervals(study, metadata), dataset=dataset_name,
            task=cfg["task"], endpoint=cfg["endpoint"],
        ))

        routing_frame = pd.read_csv(
            study / "runtime_policy_evaluation" / "policy_metrics.csv"
        )
        routing_frame = _attach_endpoint_context(
            routing_frame,
            dataset=dataset_name,
            task=cfg["task"],
            endpoint=cfg["endpoint"],
        )
        routing.append(routing_frame)
        comparison_frame = pd.read_csv(
            study / "runtime_policy_evaluation" / "policy_paired_comparisons.csv"
        )
        comparison_frame = _attach_endpoint_context(
            comparison_frame,
            dataset=dataset_name,
            task=cfg["task"],
            endpoint=cfg["endpoint"],
        )
        comparisons.append(comparison_frame)
        explanation_dir = study / ("test_explanations" if is_holdout else "explanations")
        shap_frame = pd.read_csv(
            explanation_dir / "global_shap_importance_original_features.csv"
        )
        shap_frame = _attach_endpoint_context(
            shap_frame,
            dataset=dataset_name,
            task=cfg["task"],
            endpoint=cfg["endpoint"],
        )
        shap_rows.append(shap_frame)
        important_paths = [
            performance_path,
            study / ("confidence_intervals.csv" if is_holdout else "participant_confidence_intervals.csv"),
            study / "decision_curves.csv",
            study / ("availability_routing/summary_metrics.csv" if is_holdout else "publication_protocol_correction/panel_summary.csv"),
            study / "runtime_policy_evaluation" / "policy_metrics.csv",
            study / "runtime_policy_evaluation" / "policy_paired_comparisons.csv",
            explanation_dir / "shap_reconstruction_checks.csv",
        ]
        source_artifacts[dataset_name] = {
            str(path.relative_to(study)): _sha256(path) for path in important_paths
        }

    table_frames = {
        "dataset_characteristics": pd.DataFrame(characteristics),
        "full_panel_model_performance": pd.concat(full_performance, ignore_index=True),
        "threshold_performance": pd.concat(threshold_performance, ignore_index=True),
        "model_performance_confidence_intervals": pd.concat(
            performance_intervals, ignore_index=True
        ),
        "calibration_selection": pd.concat(calibration, ignore_index=True),
        "threshold_metrics": pd.concat(thresholds, ignore_index=True),
        "decision_curves": pd.concat(decision_curves, ignore_index=True),
        "decision_curve_confidence_intervals": pd.concat(
            decision_curve_intervals, ignore_index=True
        ),
        "decision_curve_paired_contrasts": pd.concat(
            decision_curve_contrasts, ignore_index=True
        ),
        "model_paired_comparisons": pd.concat(model_comparisons, ignore_index=True),
        "availability_panel_degradation": pd.concat(availability, ignore_index=True),
        "availability_panel_confidence_intervals": pd.concat(availability_intervals, ignore_index=True),
        "routing_fallback_performance": pd.concat(routing, ignore_index=True),
        "statistical_comparisons": pd.concat(comparisons, ignore_index=True),
        "subgroup_metrics": pd.concat(subgroup_metrics, ignore_index=True),
        "subgroup_confidence_intervals": pd.concat(
            subgroup_intervals, ignore_index=True
        ),
        "selective_prediction_metrics": pd.concat(
            selective_metrics, ignore_index=True
        ),
        "selective_prediction_confidence_intervals": pd.concat(
            selective_intervals, ignore_index=True
        ),
        "brfss_survey_weighted_metrics": pd.concat(survey_metrics, ignore_index=True),
        "brfss_survey_weighted_confidence_intervals": pd.concat(
            survey_intervals, ignore_index=True
        ),
        "shap_summary": pd.concat(shap_rows, ignore_index=True),
    }
    generated_paths: list[Path] = []
    for name, frame in table_frames.items():
        generated_paths.extend(_write_table(frame, tables_dir, name))

    figure_paths = tuple(build_consolidated_figure(study_dirs, figure_dir))
    generated_paths.extend(figure_paths)
    generated_paths.extend(sorted((figure_dir / "data").glob("*.csv")))
    leakage = run_final_leakage_audit(study_dirs, output_dir=output_dir / "audits")
    if not leakage.passed:
        raise RuntimeError(f"Final leakage audit failed: {leakage.json_path}")
    generated_paths.extend([leakage.json_path, leakage.markdown_path])

    comparison_table = table_frames["statistical_comparisons"]
    router_rows = comparison_table[
        comparison_table["model_a"].eq("availability_router")
        | comparison_table["model_b"].eq("availability_router")
    ]
    if not router_rows.empty:
        router_improvement = router_rows["observed_improvement_a_over_b"].where(
            router_rows["model_a"].eq("availability_router"),
            -router_rows["observed_improvement_a_over_b"],
        )
        corrected_superiority = bool(
            router_rows["holm_adjusted_p_value"].lt(0.05).all()
            and router_improvement.gt(0).all()
        )
    else:
        corrected_superiority = False
    protocol_snapshot = provenance_dir / "frozen_protocol.yaml"
    shutil.copy2(protocol_path, protocol_snapshot)
    provenance_paths = [protocol_snapshot]
    for decision_name in (
        "BRFSS_FINAL_EVALUATION_DECISION.md",
        "HOSPITAL130_FINAL_DECISION.md",
    ):
        destination = provenance_dir / decision_name
        shutil.copy2(PROJECT_ROOT / decision_name, destination)
        provenance_paths.append(destination)
    packaging_deviation_source = (
        PROJECT_ROOT
        / "docs"
        / "research"
        / "final_execution_deviations"
        / "2026-09-11-publication-export-context-columns.md"
    )
    packaging_deviation = provenance_dir / packaging_deviation_source.name
    shutil.copy2(packaging_deviation_source, packaging_deviation)
    provenance_paths.append(packaging_deviation)

    execution_provenance: dict[str, dict[str, str]] = {}
    execution_root = provenance_dir / "execution"
    for dataset_name in EXPECTED_DATASETS:
        study, metadata = validated[dataset_name]
        dataset_execution_dir = execution_root / dataset_name
        dataset_execution_dir.mkdir(parents=True, exist_ok=True)
        metadata_snapshot = dataset_execution_dir / "experiment_metadata.json"
        shutil.copy2(study / "experiment_metadata.json", metadata_snapshot)
        log_source = (
            PROJECT_ROOT
            / "outputs"
            / "publication_pipeline"
            / "final_execution_logs"
            / f"{dataset_name}_refrozen_dtype_fix.log"
        )
        if not log_source.is_file():
            raise FileNotFoundError(f"Missing final execution log: {log_source}")
        log_snapshot = dataset_execution_dir / "execution.log"
        shutil.copy2(log_source, log_snapshot)
        if dataset_name in {"brfss", "hospital130"}:
            access_source = study / "FINAL_TEST_ACCESS_STARTED.json"
        else:
            analysis_sha = str(metadata["analysis_configuration_sha256"])
            access_source = (
                PROJECT_ROOT
                / "outputs"
                / "publication_pipeline"
                / "final_execution_receipts"
                / f"{dataset_name}_{analysis_sha[:12]}.json"
            )
        if not access_source.is_file():
            raise FileNotFoundError(f"Missing final access receipt: {access_source}")
        access_snapshot = dataset_execution_dir / "outcome_access_receipt.json"
        shutil.copy2(access_source, access_snapshot)
        copied = [metadata_snapshot, log_snapshot, access_snapshot]
        if dataset_name == "brfss":
            survey_diagnostics = dataset_execution_dir / "survey_design_diagnostics.json"
            shutil.copy2(
                study / "survey_sensitivity" / "survey_design_diagnostics.json",
                survey_diagnostics,
            )
            copied.append(survey_diagnostics)
        provenance_paths.extend(copied)
        execution_provenance[dataset_name] = {
            "experiment_metadata": str(metadata_snapshot.relative_to(output_dir)),
            "execution_log": str(log_snapshot.relative_to(output_dir)),
            "outcome_access_receipt": str(access_snapshot.relative_to(output_dir)),
        }
        if dataset_name == "brfss":
            execution_provenance[dataset_name]["survey_design_diagnostics"] = str(
                survey_diagnostics.relative_to(output_dir)
            )

    study_source_tree_sha256 = protocol["frozen_bindings"]["source_tree_sha256"]
    packaging_source_tree_sha256 = source_tree_sha256()

    master = {
        "schema_version": "1.0",
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol["protocol_sha256"],
        "evidence_tier": "final_internal_validation",
        "independent_holdout_claim_allowed": False,
        "datasets_are_endpoint_separated": True,
        "cross_cohort_probability_pooling": False,
        "study_source_tree_sha256": study_source_tree_sha256,
        "packaging_source_tree_sha256": packaging_source_tree_sha256,
        "post_execution_packaging_source_drift": (
            packaging_source_tree_sha256 != study_source_tree_sha256
        ),
        "packaging_deviation": (
            f"provenance/{packaging_deviation.name}"
        ),
        "execution_provenance": execution_provenance,
        "brfss_final_strategy": "INTERNAL_VALIDATION_ONLY",
        "hospital130_final_strategy": "COMPLETE_FULL_INTERNAL_VALIDATION",
        "dynamic_model_switching": {
            "multiplicity_corrected_superiority_established": corrected_superiority,
            "reporting_role": (
                "statistically_supported_result"
                if corrected_superiority
                else "negative_result_no_established_corrected_superiority"
            ),
        },
        "studies": {
            name: {
                "experiment_id": metadata["experiment_id"],
                "task": metadata["task"],
                "endpoint": metadata["endpoint"],
                "path": str(study),
                "source_artifacts": source_artifacts[name],
            }
            for name, (study, metadata) in validated.items()
        },
        "tables": {name: f"tables/{name}.csv" for name in table_frames},
        "figure": {
            "png": "figure/consolidated_results.png",
            "pdf": "figure/consolidated_results.pdf",
            "svg": "figure/consolidated_results.svg",
            "data": [
                "figure/data/panel_a_calibration.csv",
                "figure/data/panel_b_decision_curves.csv",
                "figure/data/panel_c_availability_degradation.csv",
            ],
            "source": "src/diabetes_pipeline/publication/figure.py",
        },
        "leakage_audit": "audits/FINAL_DATA_LEAKAGE_AUDIT.json",
    }
    master_path = output_dir / "FINAL_RESULTS.json"
    master_path.write_text(json.dumps(master, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    generated_paths.append(master_path)

    routing_table = table_frames["routing_fallback_performance"]
    summary_lines = [
        "# Final Results Summary",
        "",
        f"**Protocol:** `{protocol['protocol_id']}`",
        "",
        "**Evidence:** finalized prespecified internal validation. No dataset is described as an untouched independent final test.",
        "",
        "PIDD, Sylhet, and BRFSS are separate diabetes screening/status cohorts. Hospital130 is a separate 30-day-readmission endpoint. Probabilities and rankings are not pooled across cohorts.",
        "",
        "## Dataset-specific fallback-policy results",
        "",
        "| Dataset | Endpoint | Coverage | AUROC | AP | Brier |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, row in routing_table[routing_table["system"].eq("availability_router")].iterrows():
        summary_lines.append(
            f"| {row['dataset']} | {row['endpoint']} | {row['coverage']:.4f} | "
            f"{row['auroc']:.4f} | {row['average_precision']:.4f} | {row['brier_score']:.4f} |"
        )
    summary_lines.extend(
        [
            "",
            "## Model-family switching",
            "",
            (
                "The prespecified paired, Holm-corrected comparisons established the configured superiority criterion."
                if corrected_superiority
                else "Dynamic model-family switching did not establish multiplicity-corrected superiority over the robust fixed comparators. Numerical rankings are reported separately from statistical support."
            ),
            "",
            "SHAP summaries are associational explanations of model output, not causal effects. Decision-curve estimates are retrospective and do not establish clinical utility.",
            "",
        ]
    )
    summary_path = output_dir / "FINAL_RESULTS_SUMMARY.md"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    generated_paths.append(summary_path)

    checksums = {
        str(path.relative_to(output_dir)): _sha256(path)
        for path in sorted(set(generated_paths + provenance_paths))
        if path.is_file()
    }
    (provenance_dir / "checksums.json").write_text(
        json.dumps(checksums, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return FinalPublicationResult(output_dir, master_path, summary_path, figure_paths)
