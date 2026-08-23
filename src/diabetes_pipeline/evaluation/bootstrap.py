"""Deterministic individual- and cluster-bootstrap confidence intervals."""

from __future__ import annotations

import numpy as np

from diabetes_pipeline.evaluation.metrics import binary_metrics


DEFAULT_INTERVAL_METRICS = (
    "auroc",
    "average_precision",
    "brier_score",
    "scaled_brier_score",
    "log_loss",
    "calibration_intercept",
    "calibration_slope",
    "observed_expected_ratio",
    "expected_calibration_error",
    "accuracy",
    "balanced_accuracy",
    "sensitivity",
    "specificity",
    "false_positive_rate",
    "false_negative_rate",
    "ppv",
    "npv",
    "f1",
    "mcc",
    "youden_index",
    "positive_likelihood_ratio",
    "negative_likelihood_ratio",
    "diagnostic_odds_ratio",
)


def bootstrap_index_samples(
    y: np.ndarray,
    *,
    n_bootstrap: int,
    seed: int,
    groups: np.ndarray | None = None,
) -> list[np.ndarray]:
    """Create paired resamples for individuals or complete patient clusters."""

    y = np.asarray(y, dtype=int)
    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be positive")
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("Bootstrap intervals require both outcome classes")
    rng = np.random.default_rng(int(seed))
    samples: list[np.ndarray] = []
    if groups is None:
        negative = np.flatnonzero(y == 0)
        positive = np.flatnonzero(y == 1)
        for _ in range(n_bootstrap):
            indexes = np.concatenate(
                (
                    rng.choice(negative, size=len(negative), replace=True),
                    rng.choice(positive, size=len(positive), replace=True),
                )
            )
            rng.shuffle(indexes)
            samples.append(indexes)
        return samples

    groups = np.asarray(groups).astype(str)
    if groups.shape != y.shape:
        raise ValueError("Bootstrap groups must match the outcome shape")
    unique_groups = np.unique(groups)
    group_rows = {group: np.flatnonzero(groups == group) for group in unique_groups}
    for _ in range(n_bootstrap):
        for attempt in range(100):
            sampled_groups = rng.choice(
                unique_groups, size=len(unique_groups), replace=True
            )
            indexes = np.concatenate([group_rows[group] for group in sampled_groups])
            if len(np.unique(y[indexes])) == 2:
                samples.append(indexes)
                break
        else:
            raise RuntimeError(
                "Cluster bootstrap could not create a two-class resample after 100 attempts"
            )
    return samples


def bootstrap_metric_intervals(
    y: np.ndarray,
    probability: np.ndarray,
    *,
    threshold: float | np.ndarray,
    n_bootstrap: int,
    seed: int,
    confidence_level: float = 0.95,
    metric_names: tuple[str, ...] = DEFAULT_INTERVAL_METRICS,
    groups: np.ndarray | None = None,
) -> list[dict[str, float | int | str]]:
    """Compute percentile CIs using individual or complete-cluster resampling."""

    y = np.asarray(y, dtype=int)
    probability = np.asarray(probability, dtype=float)
    threshold_array = np.asarray(threshold, dtype=float)
    if threshold_array.ndim and threshold_array.shape != probability.shape:
        raise ValueError("Row-specific thresholds must match the probability shape")
    estimate = binary_metrics(y, probability, threshold=threshold)
    samples = {metric: np.empty(n_bootstrap, dtype=float) for metric in metric_names}
    index_samples = bootstrap_index_samples(
        y,
        n_bootstrap=n_bootstrap,
        seed=seed,
        groups=groups,
    )
    for bootstrap_index, indexes in enumerate(index_samples):
        resampled_threshold = (
            threshold_array[indexes] if threshold_array.ndim else float(threshold_array)
        )
        values = binary_metrics(
            y[indexes],
            probability[indexes],
            threshold=resampled_threshold,
        )
        for metric in metric_names:
            samples[metric][bootstrap_index] = float(values[metric])

    alpha = (1.0 - confidence_level) / 2.0
    records: list[dict[str, float | int | str]] = []
    for metric in metric_names:
        finite = samples[metric][np.isfinite(samples[metric])]
        lower, upper = (
            np.quantile(finite, [alpha, 1.0 - alpha])
            if len(finite)
            else (float("nan"), float("nan"))
        )
        records.append(
            {
                "metric": metric,
                "estimate": float(estimate[metric]),
                "ci_lower": float(lower),
                "ci_upper": float(upper),
                "confidence_level": float(confidence_level),
                "n_bootstrap": int(n_bootstrap),
                "resampling_unit": "cluster" if groups is not None else "individual",
            }
        )
    return records
