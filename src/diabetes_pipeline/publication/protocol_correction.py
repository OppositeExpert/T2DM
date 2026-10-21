"""Publication inference from retained predictions; never fits a predictor.

Calibration intercept/slope regressions are evaluation diagnostics, not fitted
probability calibrators. No development thresholds are selected in this module.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.bootstrap import bootstrap_metric_intervals
from diabetes_pipeline.evaluation.metrics import binary_metrics
from diabetes_pipeline.evaluation.repeated_cv import aggregate_repeated_predictions

REPEATED_DESIGNS = {
    "pidd": "repeated_nested_stratified_cv",
    "sylhet": "repeated_nested_stratified_group_cv",
}
PANEL_INTERVAL_METRICS = (
    "auroc", "average_precision", "brier_score", "log_loss",
    "calibration_intercept", "calibration_slope", "sensitivity", "specificity",
    "ppv", "npv", "f1", "mcc",
)


def publication_design(metadata: dict) -> str:
    dataset = metadata["dataset"]
    if dataset in REPEATED_DESIGNS:
        if metadata.get("evaluation_strategy") != REPEATED_DESIGNS[dataset]:
            raise ValueError("Repeated publication source requires explicit study design")
        return "repeated"
    if dataset in {"brfss", "hospital130"}:
        if metadata.get("runner") != "locked_internal_validation_holdout":
            raise ValueError("Fixed publication source requires internal holdout design")
        return "fixed"
    raise ValueError("Unsupported publication dataset")


def context(metadata: dict) -> dict:
    return {k: metadata[k] for k in (
        "dataset", "task", "endpoint", "experiment_id", "evidence_tier",
        "evaluation_role", "protocol_id",
    )}


def validate_prediction_bindings(frame: pd.DataFrame, metadata: dict) -> None:
    for key in ("dataset", "experiment_id", "task", "endpoint"):
        if key in frame and set(frame[key].dropna().astype(str)) != {str(metadata[key])}:
            raise ValueError(f"Prediction identity mismatch: {key}")
    manifest_path = metadata.get("split_manifest")
    if manifest_path:
        manifest = pd.read_csv(manifest_path, dtype={"row_id": str, "group_id": str})
        if publication_design(metadata) == "repeated":
            manifest = manifest[manifest.role.eq("validation")]
            keys = ["row_id", "repeat", "outer_fold"]
        else:
            manifest = manifest[manifest.role.eq("test")]
            keys = ["row_id"]
        observed = frame[keys + ["target", "group_id"]].drop_duplicates().copy()
        expected = manifest[keys + ["target", "group_id"]].copy()
        for f in (observed, expected):
            f["group_id"] = f.group_id.fillna("").astype(str)
        joined = observed.merge(expected, on=keys, how="outer", indicator=True,
                                suffixes=("_observed", "_expected"), validate="one_to_one")
        if not joined._merge.eq("both").all():
            raise ValueError("Prediction rows do not match validation manifest")
        for name in ("target", "group_id"):
            if not joined[f"{name}_observed"].eq(joined[f"{name}_expected"]).all():
                raise ValueError(f"Prediction/manifest {name} mismatch")


def verified_benchmark_tables(study: Path, metadata: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Select sources by study design, preserving fixed-cohort inputs."""
    if publication_design(metadata) == "fixed":
        return (pd.read_csv(study / "test_metrics.csv"),
                pd.read_csv(study / "confidence_intervals.csv"),
                pd.read_csv(study / "test_metrics.csv"))
    raw = pd.read_csv(study / "predictions.csv", dtype={"row_id": str, "group_id": str})
    validate_prediction_bindings(raw, metadata)
    if set(raw.model) != set(metadata["models"]):
        raise ValueError("Benchmark model registry mismatch")
    if set(raw.repeat) != set(range(5)):
        raise ValueError("Publication inference requires five complete repeats")
    aggregate = aggregate_repeated_predictions(raw).sort_values(["model", "row_id"]).reset_index(drop=True)
    retained = pd.read_csv(study / "participant_predictions.csv", dtype={"row_id": str, "group_id": str})
    retained["group_id"] = retained.group_id.fillna("")
    retained = retained.sort_values(["model", "row_id"]).reset_index(drop=True)
    for k in ("model", "row_id", "target", "group_id", "repeat_count"):
        if not np.array_equal(aggregate[k], retained[k]):
            raise ValueError(f"Retained participant identity mismatch: {k}")
    for k in ("probability_raw", "probability_calibrated"):
        if not np.allclose(aggregate[k], retained[k], rtol=0, atol=1e-14):
            raise ValueError(f"Retained participant probability mismatch: {k}")
    intervals = pd.read_csv(study / "participant_confidence_intervals.csv")
    expected_unit = "cluster" if metadata["dataset"] == "sylhet" else "individual"
    if not intervals.resampling_unit.eq(expected_unit).all():
        raise ValueError("Benchmark interval resampling unit violates protocol")
    if not intervals.n_bootstrap.eq(2000).all() or not intervals.confidence_level.eq(.95).all():
        raise ValueError("Benchmark interval count or confidence level violates protocol")
    if not intervals.estimation_scope.eq("participant_mean_across_repeats").all():
        raise ValueError("Benchmark interval aggregation mismatch")
    if not (intervals.valid_replicates + intervals.failed_replicates).eq(2000).all():
        raise ValueError("Benchmark bootstrap accounting mismatch")
    valid = intervals.valid_replicates.ge(1900)
    if not intervals.interval_status.eq("estimated").eq(valid).all():
        raise ValueError("Benchmark validity rule mismatch")
    rows = []
    for model, f in aggregate.groupby("model", sort=True):
        for version in ("raw", "calibrated"):
            metrics = binary_metrics(f.target.to_numpy(), f[f"probability_{version}"].to_numpy(), threshold=.5)
            ci = intervals[(intervals.model == model) & (intervals.probability_version == version)]
            if ci.empty or ci.metric.duplicated().any() or not ci.threshold_policy.eq("fixed_0_5").all():
                raise ValueError("Benchmark interval model/probability binding mismatch")
            for record in ci.itertuples():
                if not np.isclose(record.estimate, metrics[record.metric], rtol=1e-8, atol=1e-8, equal_nan=True):
                    raise ValueError(f"Benchmark retained interval estimate mismatch: {record.metric}")
            rows.append({**context(metadata), "model": model, "probability_version": version,
                         "threshold_policy": "fixed_0_5", "estimation_scope": "participant_mean_across_repeats",
                         "repeat_count": 5, **metrics})
    probability = pd.DataFrame(rows)
    legacy = pd.read_csv(study / "summary_metrics.csv")
    descriptive = legacy[legacy.threshold_policy.ne("fixed_0_5")].copy()
    descriptive["estimation_scope"] = "mean_outer_fold_descriptive_threshold_metrics"
    # The protocol does not define a unified repeated development threshold.
    # Keep original mean-fold operating summaries separate and labelled.
    thresholds = pd.concat([probability, descriptive], ignore_index=True)
    paired = pd.read_csv(study / "participant_paired_model_comparisons.csv")
    if not paired.n_bootstrap.eq(2000).all() or not paired.resampling_unit.eq(expected_unit).all():
        raise ValueError("Retained benchmark comparison protocol mismatch")
    for q in paired.itertuples():
        a = probability[(probability.model == q.model_a) & probability.probability_version.eq("calibrated")].iloc[0]
        b = probability[(probability.model == q.model_b) & probability.probability_version.eq("calibrated")].iloc[0]
        if not np.isclose(q.observed_difference_a_minus_b, a[q.metric] - b[q.metric], atol=1e-10):
            raise ValueError("Retained benchmark comparison estimate mismatch")
    return probability, intervals, thresholds


def aggregate_panel_predictions(frame: pd.DataFrame, dataset: str, expected_repeats: int = 5) -> pd.DataFrame:
    """Preserve records within profiles, averaging repeated probabilities only."""
    frame = frame.copy()
    frame["row_id"] = frame.row_id.astype(str)
    frame["group_id"] = frame.group_id.fillna("").astype(str)
    keys = ["system", "scenario", "available_feature_count", "row_id"]
    if frame.duplicated(keys + ["repeat"]).any():
        raise ValueError("Duplicate panel record/repeat prediction")
    stability = frame.groupby(keys).agg(targets=("target", "nunique"), groups=("group_id", "nunique"), repeats=("repeat", "nunique"))
    if not stability.targets.eq(1).all() or not stability.groups.eq(1).all() or not stability.repeats.eq(expected_repeats).all():
        raise ValueError("Panel outcome, identity or repeat completeness mismatch")
    if set(frame.repeat) != set(range(expected_repeats)):
        raise ValueError("Panel repeat identifiers are incomplete")
    if dataset == "sylhet" and not frame.group_id.str.startswith("profile:").all():
        raise ValueError("Sylhet panel inference requires identical predictor profile IDs")
    return frame.groupby(keys, as_index=False, sort=True).agg(
        target=("target", "first"), group_id=("group_id", "first"),
        probability_raw=("probability_raw", "mean"), probability_calibrated=("probability_calibrated", "mean"),
        repeat_count=("repeat", "nunique"), selected_models=("selected_model", lambda v: "|".join(sorted(set(v)))),
        calibration_methods=("calibration_method", lambda v: "|".join(sorted(set(v)))),
    )


def panel_summary(aggregated: pd.DataFrame, metadata: dict) -> pd.DataFrame:
    rows = []
    for (scenario, count, system), f in aggregated.groupby(["scenario", "available_feature_count", "system"], sort=True):
        rows.append({**context(metadata), "scenario": scenario, "available_feature_count": count,
                     "system": system, "estimation_scope": "participant_mean_across_repeats",
                     **binary_metrics(f.target.to_numpy(), f.probability_calibrated.to_numpy(), threshold=.5)})
    return pd.DataFrame(rows)


def panel_interval_task(task: tuple) -> pd.DataFrame:
    metadata, keys, frame, seed, resamples = task
    scenario, count, system = keys
    groups = None
    if metadata["dataset"] == "sylhet":
        if not frame.group_id.astype(str).str.startswith("profile:").all():
            raise ValueError("Sylhet panel intervals cannot use individual resampling")
        groups = frame.group_id.to_numpy(dtype=str)
    rows = bootstrap_metric_intervals(frame.target.to_numpy(), frame.probability_calibrated.to_numpy(),
                                     threshold=.5, n_bootstrap=resamples, seed=seed,
                                     groups=groups, metric_names=PANEL_INTERVAL_METRICS)
    return pd.DataFrame([{**context(metadata), "scenario": scenario, "available_feature_count": count,
                          "system": system, "estimation_scope": "participant_mean_across_repeats",
                          "protocol_resampling_unit": "identical_predictor_profile" if groups is not None else "participant",
                          **r} for r in rows])


def publication_panel_source(study: Path, metadata: dict) -> pd.DataFrame:
    if publication_design(metadata) == "fixed":
        return pd.read_csv(study / "availability_routing/summary_metrics.csv")
    path = study / "publication_protocol_correction/panel_summary.csv"
    table = pd.read_csv(path)
    if not table.estimation_scope.eq("participant_mean_across_repeats").all():
        raise ValueError("Publication panels must use repeated-probability metrics")
    raw = pd.read_csv(study / "availability_routing/system_predictions.csv", dtype={"row_id": str, "group_id": str})
    validate_prediction_bindings(raw, metadata)
    expected = panel_summary(aggregate_panel_predictions(raw, metadata["dataset"]), metadata)
    keys = ["scenario", "available_feature_count", "system"]
    actual = table.sort_values(keys).reset_index(drop=True)
    expected = expected.sort_values(keys).reset_index(drop=True)
    if not actual[keys].equals(expected[keys]):
        raise ValueError("Publication panel configuration mismatch")
    for metric in binary_metrics(np.array([0, 1]), np.array([.2, .8])):
        if metric not in actual or not np.allclose(actual[metric], expected[metric], rtol=1e-10, atol=1e-10, equal_nan=True):
            raise ValueError(f"Publication panel metric must be calculated from averaged probabilities: {metric}")
    return table


def publication_panel_intervals(study: Path, metadata: dict) -> pd.DataFrame:
    if publication_design(metadata) == "fixed":
        # Fixed-cohort stress studies retained point estimates, but no panel CI
        # artifact. Never substitute runtime-policy or full-benchmark intervals.
        path = study / "availability_routing/confidence_intervals.csv"
        return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["dataset", "task", "endpoint"])
    intervals = pd.read_csv(study / "publication_protocol_correction/panel_confidence_intervals.csv")
    unit = "cluster" if metadata["dataset"] == "sylhet" else "individual"
    if not intervals.resampling_unit.eq(unit).all():
        raise ValueError("Publication panel interval resampling violates protocol")
    if not intervals.n_bootstrap.eq(2000).all() or not intervals.estimation_scope.eq("participant_mean_across_repeats").all():
        raise ValueError("Publication panel interval count or aggregation violates protocol")
    return intervals
