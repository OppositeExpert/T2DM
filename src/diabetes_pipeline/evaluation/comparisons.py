"""Paired, outer-fold model comparisons."""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import t, wilcoxon
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)

from diabetes_pipeline.evaluation.bootstrap import bootstrap_index_samples


COMPARISON_METRICS = {
    "auroc": "higher",
    "average_precision": "higher",
    "brier_score": "lower",
    "log_loss": "lower",
}


def _probability_metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    return {
        "auroc": float(roc_auc_score(y, probability)),
        "average_precision": float(average_precision_score(y, probability)),
        "brier_score": float(brier_score_loss(y, probability)),
        "log_loss": float(log_loss(y, probability, labels=[0, 1])),
    }


def paired_model_comparisons(
    fold_metrics: pd.DataFrame,
    *,
    metric_directions: dict[str, str] = COMPARISON_METRICS,
) -> pd.DataFrame:
    """Compare models on matched repeat/fold evaluations."""

    records: list[dict[str, float | int | str]] = []
    models = sorted(fold_metrics["model"].unique())
    for metric, direction in metric_directions.items():
        pivot = fold_metrics.pivot_table(
            index=["repeat", "outer_fold"],
            columns="model",
            values=metric,
            aggfunc="first",
        )
        for model_a, model_b in combinations(models, 2):
            paired = pivot[[model_a, model_b]].dropna()
            difference = (paired[model_a] - paired[model_b]).to_numpy(dtype=float)
            n_pairs = len(difference)
            mean_difference = float(np.mean(difference)) if n_pairs else float("nan")
            if n_pairs > 1:
                standard_error = float(np.std(difference, ddof=1) / np.sqrt(n_pairs))
                critical = float(t.ppf(0.975, df=n_pairs - 1))
                ci_lower = mean_difference - critical * standard_error
                ci_upper = mean_difference + critical * standard_error
                if np.allclose(difference, 0.0, rtol=0.0, atol=1e-15):
                    p_value = 1.0
                else:
                    try:
                        p_value = float(wilcoxon(difference).pvalue)
                    except ValueError:
                        p_value = float("nan")
            else:
                ci_lower = ci_upper = p_value = float("nan")
            improvement = (
                mean_difference if direction == "higher" else -mean_difference
            )
            records.append(
                {
                    "metric": metric,
                    "direction": direction,
                    "model_a": model_a,
                    "model_b": model_b,
                    "n_pairs": n_pairs,
                    "mean_difference_a_minus_b": mean_difference,
                    "mean_improvement_a_over_b": improvement,
                    "ci_lower_a_minus_b": ci_lower,
                    "ci_upper_a_minus_b": ci_upper,
                    "wilcoxon_p_value": p_value,
                }
            )
    result = pd.DataFrame(records)
    if result.empty:
        return result
    result["holm_adjusted_p_value"] = np.nan
    for metric in result["metric"].unique():
        p_values = (
            result.loc[result["metric"] == metric, "wilcoxon_p_value"]
            .dropna()
            .sort_values()
        )
        running_maximum = 0.0
        comparison_count = len(p_values)
        for rank, (index, p_value) in enumerate(p_values.items()):
            adjusted = min(1.0, float(p_value) * (comparison_count - rank))
            running_maximum = max(running_maximum, adjusted)
            result.loc[index, "holm_adjusted_p_value"] = running_maximum
    return result


def paired_bootstrap_model_comparisons(
    predictions: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
    groups: np.ndarray | None = None,
    metric_directions: dict[str, str] = COMPARISON_METRICS,
) -> pd.DataFrame:
    """Compare models on one locked test set with paired bootstrap resampling."""

    required = {"model", "row_id", "target", "probability_calibrated"}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Comparison predictions are missing columns: {missing}")
    models = sorted(predictions["model"].unique())
    aligned: dict[str, pd.DataFrame] = {}
    reference_rows: np.ndarray | None = None
    reference_y: np.ndarray | None = None
    for model in models:
        frame = (
            predictions[predictions["model"] == model]
            .sort_values("row_id")
            .reset_index(drop=True)
        )
        rows = frame["row_id"].astype(str).to_numpy()
        y = frame["target"].to_numpy(dtype=int)
        if reference_rows is None:
            reference_rows = rows
            reference_y = y
        elif not np.array_equal(rows, reference_rows) or not np.array_equal(
            y, reference_y
        ):
            raise ValueError("Models do not share identical paired test rows and labels")
        aligned[str(model)] = frame
    if reference_y is None:
        raise ValueError("No model predictions were supplied")

    aligned_groups = None
    if groups is not None:
        groups = np.asarray(groups).astype(str)
        if groups.shape != reference_y.shape:
            raise ValueError("Comparison groups must follow row_id-sorted prediction rows")
        aligned_groups = groups
    index_samples = bootstrap_index_samples(
        reference_y,
        n_bootstrap=n_bootstrap,
        seed=seed,
        groups=aligned_groups,
    )
    metric_values: dict[str, dict[str, float]] = {}
    bootstrap_values: dict[str, dict[str, np.ndarray]] = {}
    for model, frame in aligned.items():
        probability = frame["probability_calibrated"].to_numpy(dtype=float)
        metric_values[model] = _probability_metrics(reference_y, probability)
        bootstrap_values[model] = {
            metric: np.empty(n_bootstrap, dtype=float)
            for metric in metric_directions
        }
        for bootstrap_index, indexes in enumerate(index_samples):
            sampled = _probability_metrics(reference_y[indexes], probability[indexes])
            for metric in metric_directions:
                bootstrap_values[model][metric][bootstrap_index] = float(
                    sampled[metric]
                )

    records: list[dict[str, float | int | str]] = []
    alpha = 0.025
    for metric, direction in metric_directions.items():
        for model_a, model_b in combinations(models, 2):
            differences = (
                bootstrap_values[str(model_a)][metric]
                - bootstrap_values[str(model_b)][metric]
            )
            finite = differences[np.isfinite(differences)]
            observed = (
                metric_values[str(model_a)][metric]
                - metric_values[str(model_b)][metric]
            )
            if len(finite):
                lower, upper = np.quantile(finite, [alpha, 1.0 - alpha])
                p_value = min(
                    1.0,
                    2.0
                    * min(
                        (np.sum(finite <= 0.0) + 1) / (len(finite) + 1),
                        (np.sum(finite >= 0.0) + 1) / (len(finite) + 1),
                    ),
                )
            else:
                lower = upper = p_value = float("nan")
            records.append(
                {
                    "metric": metric,
                    "direction": direction,
                    "model_a": model_a,
                    "model_b": model_b,
                    "observed_difference_a_minus_b": float(observed),
                    "observed_improvement_a_over_b": float(
                        observed if direction == "higher" else -observed
                    ),
                    "ci_lower_a_minus_b": float(lower),
                    "ci_upper_a_minus_b": float(upper),
                    "paired_bootstrap_p_value": float(p_value),
                    "n_bootstrap": int(n_bootstrap),
                    "resampling_unit": (
                        "cluster" if aligned_groups is not None else "individual"
                    ),
                }
            )
    result = pd.DataFrame(records)
    if result.empty:
        return pd.DataFrame(
            columns=[
                "metric",
                "direction",
                "model_a",
                "model_b",
                "observed_difference_a_minus_b",
                "observed_improvement_a_over_b",
                "ci_lower_a_minus_b",
                "ci_upper_a_minus_b",
                "paired_bootstrap_p_value",
                "n_bootstrap",
                "resampling_unit",
                "holm_adjusted_p_value",
            ]
        )
    result["holm_adjusted_p_value"] = np.nan
    for metric in result["metric"].unique():
        p_values = (
            result.loc[result["metric"] == metric, "paired_bootstrap_p_value"]
            .dropna()
            .sort_values()
        )
        running_maximum = 0.0
        comparison_count = len(p_values)
        for rank, (index, p_value) in enumerate(p_values.items()):
            adjusted = min(1.0, float(p_value) * (comparison_count - rank))
            running_maximum = max(running_maximum, adjusted)
            result.loc[index, "holm_adjusted_p_value"] = running_maximum
    return result
