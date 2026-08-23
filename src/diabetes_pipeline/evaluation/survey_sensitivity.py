"""Survey-weighted BRFSS performance sensitivity analysis."""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import numpy as np
import pandas as pd
from scipy.special import logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

from diabetes_pipeline.evaluation.metrics import EPSILON
from diabetes_pipeline.settings import get_dataset_config


BRFSS_DESIGN_COLUMNS = ("_STATE", "_STSTR", "_PSU", "_LLCPWT", "DIABETE3")
BOOTSTRAP_METRICS = (
    "prevalence",
    "auroc",
    "average_precision",
    "brier_score",
    "scaled_brier_score",
    "log_loss",
    "observed_expected_ratio",
    "expected_calibration_error",
    "accuracy",
    "balanced_accuracy",
    "sensitivity",
    "specificity",
    "ppv",
    "npv",
    "f1",
    "mcc",
    "youden_index",
    "net_benefit",
)


@dataclass(frozen=True)
class SurveySensitivityResult:
    study_dir: Path
    output_dir: Path
    metrics_path: Path
    intervals_path: Path
    report_path: Path


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def _weighted_calibration_error(
    y: np.ndarray,
    probability: np.ndarray,
    weights: np.ndarray,
    *,
    n_bins: int = 10,
) -> float:
    bin_index = np.minimum((probability * n_bins).astype(int), n_bins - 1)
    total_weight = float(np.sum(weights))
    error = 0.0
    for index in range(n_bins):
        selected = bin_index == index
        bin_weight = float(np.sum(weights[selected]))
        if bin_weight:
            observed = float(np.average(y[selected], weights=weights[selected]))
            expected = float(
                np.average(probability[selected], weights=weights[selected])
            )
            error += bin_weight / total_weight * abs(observed - expected)
    return float(error)


def _weighted_calibration_intercept_slope(
    y: np.ndarray,
    probability: np.ndarray,
    weights: np.ndarray,
) -> tuple[float, float]:
    clipped = np.clip(probability, EPSILON, 1.0 - EPSILON)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            model = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=2_000)
            model.fit(
                logit(clipped).reshape(-1, 1),
                y,
                sample_weight=weights,
            )
            return float(model.intercept_[0]), float(model.coef_[0, 0])
        except Exception:
            return float("nan"), float("nan")


def weighted_binary_metrics(
    y: np.ndarray,
    probability: np.ndarray,
    weights: np.ndarray,
    *,
    threshold: float,
    include_calibration_model: bool = True,
) -> dict[str, float | int]:
    """Compute discrimination, calibration, classification, and utility metrics."""

    y = np.asarray(y, dtype=int)
    probability = np.clip(
        np.asarray(probability, dtype=float), EPSILON, 1.0 - EPSILON
    )
    weights = np.asarray(weights, dtype=float)
    valid = (
        np.isfinite(probability)
        & np.isfinite(weights)
        & (weights > 0.0)
        & np.isin(y, [0, 1])
    )
    y = y[valid]
    probability = probability[valid]
    weights = weights[valid]
    if len(y) == 0 or set(np.unique(y)) != {0, 1}:
        raise ValueError("Weighted metrics require positive-weight rows in both classes")
    # Scaling preserves every reported estimate and improves numerical stability.
    weights = weights / np.mean(weights)
    prediction = probability >= float(threshold)
    positive = y == 1
    negative = ~positive
    tp = float(np.sum(weights[prediction & positive]))
    fp = float(np.sum(weights[prediction & negative]))
    tn = float(np.sum(weights[~prediction & negative]))
    fn = float(np.sum(weights[~prediction & positive]))
    weight_sum = float(np.sum(weights))
    prevalence = float(np.sum(weights * y) / weight_sum)
    brier = float(np.sum(weights * (y - probability) ** 2) / weight_sum)
    prevalence_brier = prevalence * (1.0 - prevalence)
    sensitivity = _safe_divide(tp, tp + fn)
    specificity = _safe_divide(tn, tn + fp)
    ppv = _safe_divide(tp, tp + fp)
    npv = _safe_divide(tn, tn + fn)
    f1 = _safe_divide(2.0 * tp, 2.0 * tp + fp + fn)
    mcc_denominator = np.sqrt(
        (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    )
    mcc = _safe_divide(tp * tn - fp * fn, float(mcc_denominator))
    calibration_intercept, calibration_slope = (
        _weighted_calibration_intercept_slope(y, probability, weights)
        if include_calibration_model
        else (float("nan"), float("nan"))
    )
    odds = float(threshold / (1.0 - threshold))
    return {
        "n": int(len(y)),
        "weight_sum": weight_sum,
        "kish_effective_sample_size": float(
            weight_sum**2 / np.sum(np.square(weights))
        ),
        "prevalence": prevalence,
        "threshold": float(threshold),
        "auroc": float(roc_auc_score(y, probability, sample_weight=weights)),
        "average_precision": float(
            average_precision_score(y, probability, sample_weight=weights)
        ),
        "brier_score": brier,
        "scaled_brier_score": (
            float(1.0 - brier / prevalence_brier)
            if prevalence_brier
            else float("nan")
        ),
        "log_loss": float(
            log_loss(y, probability, labels=[0, 1], sample_weight=weights)
        ),
        "calibration_intercept": calibration_intercept,
        "calibration_slope": calibration_slope,
        "observed_expected_ratio": _safe_divide(
            float(np.sum(weights * y)),
            float(np.sum(weights * probability)),
        ),
        "expected_calibration_error": _weighted_calibration_error(
            y, probability, weights
        ),
        "accuracy": float((tp + tn) / weight_sum),
        "balanced_accuracy": float((sensitivity + specificity) / 2.0),
        "sensitivity": sensitivity,
        "specificity": specificity,
        "ppv": ppv,
        "npv": npv,
        "f1": f1,
        "mcc": mcc,
        "youden_index": float(sensitivity + specificity - 1.0),
        "net_benefit": float(tp / weight_sum - fp / weight_sum * odds),
        "weighted_tn": tn,
        "weighted_fp": fp,
        "weighted_fn": fn,
        "weighted_tp": tp,
    }


def load_brfss_design_rows(row_ids: pd.Series) -> pd.DataFrame:
    """Recover design variables for prediction rows using source-index row IDs."""

    identifiers = row_ids.astype(str)
    if not identifiers.str.match(r"^brfss:\d+$").all():
        raise ValueError("BRFSS prediction row IDs must use the brfss:<source-index> form")
    positions = identifiers.str.split(":", n=1).str[1].astype(int).to_numpy()
    cfg = get_dataset_config("brfss")
    raw = pd.read_csv(
        cfg["raw_path"],
        usecols=list(BRFSS_DESIGN_COLUMNS),
        low_memory=False,
    )
    if np.any(positions < 0) or np.any(positions >= len(raw)):
        raise ValueError("A BRFSS prediction row ID falls outside the raw file")
    selected = raw.iloc[positions].reset_index(drop=True).copy()
    selected.insert(0, "row_id", identifiers.to_numpy())
    for column in ("_STATE", "_STSTR", "_PSU", "_LLCPWT"):
        selected[column] = pd.to_numeric(selected[column], errors="coerce")
    if selected[list(BRFSS_DESIGN_COLUMNS[:-1])].isna().any().any():
        raise ValueError("Selected BRFSS rows contain missing survey-design values")
    if (selected["_LLCPWT"] <= 0.0).any():
        raise ValueError("Selected BRFSS rows contain non-positive final weights")
    return selected


def _psu_bootstrap_weight_chunks(
    design: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
    chunk_size: int = 16,
) -> Iterator[tuple[int, np.ndarray]]:
    """Yield stratified with-replacement PSU bootstrap respondent weights."""

    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be positive")
    cluster_key = (
        design["_STSTR"].astype(str) + "|" + design["_PSU"].astype(str)
    )
    cluster_names, row_cluster = np.unique(cluster_key, return_inverse=True)
    cluster_frame = pd.DataFrame(
        {
            "cluster": cluster_names,
            "stratum": [name.split("|", 1)[0] for name in cluster_names],
            "cluster_position": np.arange(len(cluster_names)),
        }
    )
    stratum_clusters = [
        frame["cluster_position"].to_numpy(dtype=int)
        for _, frame in cluster_frame.groupby("stratum", sort=True)
    ]
    base_weights = design["_LLCPWT"].to_numpy(dtype=float)
    rng = np.random.default_rng(int(seed))
    for start in range(0, n_bootstrap, chunk_size):
        size = min(chunk_size, n_bootstrap - start)
        cluster_multipliers = np.ones((size, len(cluster_names)), dtype=float)
        for cluster_positions in stratum_clusters:
            count = len(cluster_positions)
            if count > 1:
                cluster_multipliers[:, cluster_positions] = rng.multinomial(
                    count,
                    np.full(count, 1.0 / count),
                    size=size,
                )
        yield start, base_weights[None, :] * cluster_multipliers[:, row_cluster]


def _evaluation_specifications(
    predictions: pd.DataFrame,
    selected_thresholds: pd.DataFrame,
) -> list[dict[str, Any]]:
    specifications: list[dict[str, Any]] = []
    for model in sorted(predictions["model"].astype(str).unique()):
        specifications.append(
            {
                "model": model,
                "probability_version": "raw",
                "probability_column": "probability_raw",
                "threshold_policy": "fixed_0_5",
                "threshold": 0.5,
            }
        )
        model_thresholds = selected_thresholds[
            selected_thresholds["model"].astype(str) == model
        ]
        for _, row in model_thresholds.sort_values("threshold_policy").iterrows():
            specifications.append(
                {
                    "model": model,
                    "probability_version": "calibrated",
                    "probability_column": "probability_calibrated",
                    "threshold_policy": str(row["threshold_policy"]),
                    "threshold": float(row["threshold"]),
                }
            )
    return specifications


def _render_report(
    diagnostics: dict[str, Any],
    metrics: pd.DataFrame,
    intervals: pd.DataFrame,
) -> str:
    calibrated = metrics[
        (metrics["probability_version"] == "calibrated")
        & (metrics["threshold_policy"] == "fixed_0_5")
    ].copy()
    lines = [
        "# BRFSS Survey-Weighted Prediction Sensitivity Analysis",
        "",
        "**Evidence tier:** development sensitivity analysis",
        "",
        "**Role:** secondary population-weighted sensitivity; not a replacement for the sample-conditional primary analysis",
        "",
        "## Design diagnostics",
        "",
        f"- Evaluated respondents: {diagnostics['rows']:,}",
        f"- States/reporting areas represented: {diagnostics['state_count']:,}",
        f"- Sampling strata represented: {diagnostics['stratum_count']:,}",
        f"- PSU-within-stratum clusters represented: {diagnostics['psu_count']:,}",
        f"- Single-PSU represented strata: {diagnostics['lonely_stratum_count']:,}",
        f"- Kish effective sample size from `_LLCPWT`: {diagnostics['kish_effective_sample_size']:,.1f}",
        f"- Unweighted prevalence: {diagnostics['unweighted_prevalence']:.4f}",
        f"- `_LLCPWT`-weighted prevalence: {diagnostics['weighted_prevalence']:.4f}",
        "",
        "## Fixed-0.5 calibrated sensitivity table",
        "",
        "| Model | Estimand | AUROC | Average precision | Brier | Calibration intercept | Calibration slope | Sensitivity | Specificity |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in calibrated.sort_values(["model", "estimand"]).iterrows():
        lines.append(
            f"| {row['model']} | {row['estimand']} | {row['auroc']:.4f} | "
            f"{row['average_precision']:.4f} | {row['brier_score']:.4f} | "
            f"{row['calibration_intercept']:.4f} | {row['calibration_slope']:.4f} | "
            f"{row['sensitivity']:.4f} | {row['specificity']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Uncertainty",
            "",
            f"The interval table contains {len(intervals):,} pointwise percentile intervals from "
            f"{diagnostics['n_bootstrap']:,} stratified with-replacement PSU bootstrap replicates. "
            "All models and operating policies share the same replicate weights.",
            "",
            "Single-PSU strata represented in the evaluated partition are treated as certainty "
            "clusters. The random respondent-level development holdout was not created as a "
            "survey-design partition, so these intervals are a prespecified sensitivity analysis, "
            "not an official CDC variance estimate and not evidence of external validation.",
            "",
        ]
    )
    return "\n".join(lines)


def run_brfss_survey_sensitivity(
    study_dir: Path,
    *,
    n_bootstrap: int = 200,
    seed: int = 42,
) -> SurveySensitivityResult:
    """Evaluate an existing BRFSS holdout study under the complex survey design."""

    study_dir = Path(study_dir).resolve()
    metadata_path = study_dir / "experiment_metadata.json"
    predictions_path = study_dir / "test_predictions.csv"
    thresholds_path = study_dir / "selected_thresholds.csv"
    for path in (metadata_path, predictions_path, thresholds_path):
        if not path.exists():
            raise FileNotFoundError(f"Required BRFSS study artifact is missing: {path}")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("dataset") != "brfss":
        raise ValueError("Survey sensitivity is implemented only for BRFSS studies")
    predictions = pd.read_csv(predictions_path, low_memory=False)
    selected_thresholds = pd.read_csv(thresholds_path, low_memory=False)
    reference_model = sorted(predictions["model"].astype(str).unique())[0]
    reference = (
        predictions[predictions["model"].astype(str) == reference_model]
        .sort_values("row_id")
        .reset_index(drop=True)
    )
    design = load_brfss_design_rows(reference["row_id"])
    target_map = {1: 1, 3: 0}
    design_target = design["DIABETE3"].map(target_map)
    if design_target.isna().any() or not np.array_equal(
        design_target.to_numpy(dtype=int), reference["target"].to_numpy(dtype=int)
    ):
        raise ValueError("BRFSS raw target does not match stored study predictions")

    model_frames: dict[str, pd.DataFrame] = {}
    for model in sorted(predictions["model"].astype(str).unique()):
        frame = (
            predictions[predictions["model"].astype(str) == model]
            .sort_values("row_id")
            .reset_index(drop=True)
        )
        if not frame["row_id"].astype(str).equals(reference["row_id"].astype(str)):
            raise ValueError("BRFSS models do not share identical survey rows")
        if not frame["target"].astype(int).equals(reference["target"].astype(int)):
            raise ValueError("BRFSS models do not share identical outcomes")
        model_frames[model] = frame

    y = reference["target"].to_numpy(dtype=int)
    survey_weights = design["_LLCPWT"].to_numpy(dtype=float)
    unweighted = np.ones(len(reference), dtype=float)
    specifications = _evaluation_specifications(predictions, selected_thresholds)
    point_records: list[dict[str, Any]] = []
    for specification in specifications:
        frame = model_frames[specification["model"]]
        probability = frame[specification["probability_column"]].to_numpy(dtype=float)
        for estimand, weights in (
            ("sample_conditional_unweighted", unweighted),
            ("brfss_population_weighted", survey_weights),
        ):
            point_records.append(
                {
                    "model": specification["model"],
                    "probability_version": specification["probability_version"],
                    "threshold_policy": specification["threshold_policy"],
                    "estimand": estimand,
                    **weighted_binary_metrics(
                        y,
                        probability,
                        weights,
                        threshold=specification["threshold"],
                    ),
                }
            )
    point_metrics = pd.DataFrame(point_records)

    bootstrap_values: dict[tuple[str, str, str], dict[str, np.ndarray]] = {}
    for specification in specifications:
        key = (
            specification["model"],
            specification["probability_version"],
            specification["threshold_policy"],
        )
        bootstrap_values[key] = {
            metric: np.full(n_bootstrap, np.nan, dtype=float)
            for metric in BOOTSTRAP_METRICS
        }
    for start, replicate_weights in _psu_bootstrap_weight_chunks(
        design,
        n_bootstrap=int(n_bootstrap),
        seed=int(seed),
    ):
        for local_index, weights in enumerate(replicate_weights):
            replicate_index = start + local_index
            for specification in specifications:
                frame = model_frames[specification["model"]]
                values = weighted_binary_metrics(
                    y,
                    frame[specification["probability_column"]].to_numpy(dtype=float),
                    weights,
                    threshold=specification["threshold"],
                    include_calibration_model=False,
                )
                key = (
                    specification["model"],
                    specification["probability_version"],
                    specification["threshold_policy"],
                )
                for metric in BOOTSTRAP_METRICS:
                    bootstrap_values[key][metric][replicate_index] = float(
                        values[metric]
                    )

    weighted_points = point_metrics[
        point_metrics["estimand"] == "brfss_population_weighted"
    ].set_index(["model", "probability_version", "threshold_policy"])
    interval_records: list[dict[str, Any]] = []
    for key, metric_samples in bootstrap_values.items():
        for metric, samples in metric_samples.items():
            finite = samples[np.isfinite(samples)]
            lower, upper = (
                np.quantile(finite, [0.025, 0.975])
                if len(finite)
                else (float("nan"), float("nan"))
            )
            interval_records.append(
                {
                    "model": key[0],
                    "probability_version": key[1],
                    "threshold_policy": key[2],
                    "metric": metric,
                    "estimate": float(weighted_points.loc[key, metric]),
                    "ci_lower": float(lower),
                    "ci_upper": float(upper),
                    "confidence_level": 0.95,
                    "n_bootstrap": int(n_bootstrap),
                    "resampling_unit": "psu_within_stratum",
                    "estimand": "brfss_population_weighted_sensitivity",
                }
            )
    intervals = pd.DataFrame(interval_records)

    stratum_psus = (
        design.assign(
            cluster=design["_STSTR"].astype(str) + "|" + design["_PSU"].astype(str)
        )
        .groupby("_STSTR")["cluster"]
        .nunique()
    )
    diagnostics = {
        "schema_version": "1.0",
        "study_dir": str(study_dir),
        "evidence_tier": "development_survey_sensitivity",
        "rows": int(len(design)),
        "state_count": int(design["_STATE"].nunique()),
        "stratum_count": int(design["_STSTR"].nunique()),
        "psu_count": int(
            (
                design["_STSTR"].astype(str)
                + "|"
                + design["_PSU"].astype(str)
            ).nunique()
        ),
        "lonely_stratum_count": int((stratum_psus == 1).sum()),
        "unweighted_prevalence": float(np.mean(y)),
        "weighted_prevalence": float(np.average(y, weights=survey_weights)),
        "kish_effective_sample_size": float(
            np.sum(survey_weights) ** 2 / np.sum(np.square(survey_weights))
        ),
        "weight_min": float(np.min(survey_weights)),
        "weight_median": float(np.median(survey_weights)),
        "weight_max": float(np.max(survey_weights)),
        "n_bootstrap": int(n_bootstrap),
        "seed": int(seed),
        "variance_method": "stratified_with_replacement_psu_bootstrap",
        "lonely_psu_handling": "certainty_multiplier_one",
        "final_outcome_access_authorized": False,
        "limitations": [
            "The evaluated holdout was formed by respondent-level random splitting, not by a survey-design partition.",
            "Intervals are sensitivity estimates and are not an official CDC variance calculation.",
            "Survey weights are used for evaluation, not model fitting.",
            "This analysis does not provide temporal or external validation.",
        ],
    }

    output_dir = study_dir / "survey_sensitivity"
    paper_table_dir = study_dir / "paper_tables"
    output_dir.mkdir(parents=True, exist_ok=True)
    paper_table_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "survey_weighted_metrics.csv"
    intervals_path = output_dir / "survey_weighted_confidence_intervals.csv"
    diagnostics_path = output_dir / "survey_design_diagnostics.json"
    report_path = output_dir / "survey_sensitivity_report.md"
    point_metrics.to_csv(metrics_path, index=False)
    intervals.to_csv(intervals_path, index=False)
    diagnostics_path.write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True), encoding="utf-8"
    )
    report_path.write_text(
        _render_report(diagnostics, point_metrics, intervals), encoding="utf-8"
    )
    point_metrics.to_csv(
        paper_table_dir / "brfss_survey_weighted_metrics.csv", index=False
    )
    intervals.to_csv(
        paper_table_dir / "brfss_survey_weighted_confidence_intervals.csv",
        index=False,
    )
    return SurveySensitivityResult(
        study_dir=study_dir,
        output_dir=output_dir,
        metrics_path=metrics_path,
        intervals_path=intervals_path,
        report_path=report_path,
    )
