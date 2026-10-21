"""Bootstrap uncertainty and paired contrasts for decision-curve analysis."""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd


DEFAULT_DECISION_THRESHOLDS = np.linspace(0.01, 0.80, 80)


def _validate_thresholds(thresholds: np.ndarray | None) -> np.ndarray:
    values = np.asarray(
        DEFAULT_DECISION_THRESHOLDS if thresholds is None else thresholds,
        dtype=float,
    )
    if values.ndim != 1 or len(values) == 0:
        raise ValueError("Decision thresholds must be a non-empty one-dimensional array")
    if np.any(~np.isfinite(values)) or np.any((values <= 0.0) | (values >= 1.0)):
        raise ValueError("Decision thresholds must lie strictly between zero and one")
    if np.any(np.diff(values) <= 0.0):
        raise ValueError("Decision thresholds must be unique and strictly increasing")
    return values


def _net_benefit(
    y: np.ndarray,
    probability: np.ndarray,
    thresholds: np.ndarray,
) -> np.ndarray:
    predictions = probability[:, None] >= thresholds[None, :]
    true_positive = np.sum(predictions & (y[:, None] == 1), axis=0)
    false_positive = np.sum(predictions & (y[:, None] == 0), axis=0)
    odds = thresholds / (1.0 - thresholds)
    return true_positive / len(y) - false_positive / len(y) * odds


def _individual_bootstrap_net_benefits(
    y: np.ndarray,
    probabilities: np.ndarray,
    thresholds: np.ndarray,
    *,
    n_bootstrap: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Exact pointwise paired stratified bootstrap using joint model patterns."""

    model_count = probabilities.shape[1]
    positive_count = int(np.sum(y == 1))
    negative_count = int(np.sum(y == 0))
    sample_count = len(y)
    samples = np.empty((n_bootstrap, model_count, len(thresholds)), dtype=float)
    odds = thresholds / (1.0 - thresholds)
    for threshold_index, threshold in enumerate(thresholds):
        predicted = probabilities >= threshold
        positive_patterns, positive_pattern_counts = np.unique(
            predicted[y == 1], axis=0, return_counts=True
        )
        negative_patterns, negative_pattern_counts = np.unique(
            predicted[y == 0], axis=0, return_counts=True
        )
        sampled_positive_patterns = rng.multinomial(
            positive_count,
            positive_pattern_counts / positive_count,
            size=n_bootstrap,
        )
        sampled_negative_patterns = rng.multinomial(
            negative_count,
            negative_pattern_counts / negative_count,
            size=n_bootstrap,
        )
        true_positive = sampled_positive_patterns @ positive_patterns.astype(float)
        false_positive = sampled_negative_patterns @ negative_patterns.astype(float)
        samples[:, :, threshold_index] = (
            true_positive / sample_count
            - false_positive / sample_count * odds[threshold_index]
        )
    return samples


def _cluster_bootstrap_net_benefits(
    y: np.ndarray,
    probabilities: np.ndarray,
    thresholds: np.ndarray,
    groups: np.ndarray,
    *,
    n_bootstrap: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Resample complete groups and retain variable cluster-bootstrap sample sizes."""

    unique_groups, inverse = np.unique(groups.astype(str), return_inverse=True)
    group_count = len(unique_groups)
    group_sizes = np.bincount(inverse).astype(float)
    model_count = probabilities.shape[1]
    group_true_positive = np.zeros(
        (model_count, group_count, len(thresholds)), dtype=float
    )
    group_false_positive = np.zeros(
        (model_count, group_count, len(thresholds)), dtype=float
    )
    for model_index in range(model_count):
        predictions = probabilities[:, model_index, None] >= thresholds[None, :]
        np.add.at(
            group_true_positive[model_index],
            inverse,
            predictions & (y[:, None] == 1),
        )
        np.add.at(
            group_false_positive[model_index],
            inverse,
            predictions & (y[:, None] == 0),
        )

    odds = thresholds / (1.0 - thresholds)
    samples = np.empty((n_bootstrap, model_count, len(thresholds)), dtype=float)
    probabilities = np.full(group_count, 1.0 / group_count)
    chunk_size = 32
    for start in range(0, n_bootstrap, chunk_size):
        stop = min(start + chunk_size, n_bootstrap)
        counts = rng.multinomial(
            group_count,
            probabilities,
            size=stop - start,
        )
        sample_sizes = counts @ group_sizes
        for model_index in range(model_count):
            true_positive = counts @ group_true_positive[model_index]
            false_positive = counts @ group_false_positive[model_index]
            samples[start:stop, model_index] = (
                true_positive / sample_sizes[:, None]
                - false_positive / sample_sizes[:, None] * odds[None, :]
            )
    return samples


def decision_curve_bootstrap_inference(
    predictions: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
    thresholds: np.ndarray | None = None,
    groups: np.ndarray | None = None,
    confidence_level: float = 0.95,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return model net-benefit intervals and paired model contrasts.

    All models must contain the same row IDs and labels. The same bootstrap
    random stream is used for every model, preserving paired inference.
    """

    required = {"model", "row_id", "target", "probability_calibrated"}
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Decision-curve predictions are missing columns: {missing}")
    if n_bootstrap < 1:
        raise ValueError("n_bootstrap must be positive")
    if not 0.0 < confidence_level < 1.0:
        raise ValueError("confidence_level must lie strictly between zero and one")
    threshold_values = _validate_thresholds(thresholds)

    models = sorted(predictions["model"].astype(str).unique())
    aligned: dict[str, pd.DataFrame] = {}
    reference_rows: np.ndarray | None = None
    reference_y: np.ndarray | None = None
    for model in models:
        frame = (
            predictions[predictions["model"].astype(str) == model]
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
            raise ValueError("Models do not share identical paired rows and labels")
        aligned[model] = frame
    if reference_y is None or set(np.unique(reference_y)) != {0, 1}:
        raise ValueError("Decision-curve inference requires both outcome classes")

    aligned_groups = None
    if groups is not None:
        aligned_groups = np.asarray(groups).astype(str)
        if aligned_groups.shape != reference_y.shape:
            raise ValueError("Decision-curve groups must follow row_id-sorted rows")

    probability_matrix = np.column_stack(
        [
            aligned[model]["probability_calibrated"].to_numpy(dtype=float)
            for model in models
        ]
    )
    observed = {
        model: _net_benefit(
            reference_y, probability_matrix[:, model_index], threshold_values
        )
        for model_index, model in enumerate(models)
    }
    rng = np.random.default_rng(int(seed))
    if aligned_groups is None:
        bootstrap_array = _individual_bootstrap_net_benefits(
            reference_y,
            probability_matrix,
            threshold_values,
            n_bootstrap=int(n_bootstrap),
            rng=rng,
        )
    else:
        bootstrap_array = _cluster_bootstrap_net_benefits(
            reference_y,
            probability_matrix,
            threshold_values,
            aligned_groups,
            n_bootstrap=int(n_bootstrap),
            rng=rng,
        )
    bootstrap = {
        model: bootstrap_array[:, model_index, :]
        for model_index, model in enumerate(models)
    }

    alpha = (1.0 - confidence_level) / 2.0
    interval_records: list[dict[str, float | int | str]] = []
    for model in models:
        lower, upper = np.quantile(bootstrap[model], [alpha, 1.0 - alpha], axis=0)
        for index, threshold in enumerate(threshold_values):
            interval_records.append(
                {
                    "model": model,
                    "threshold": float(threshold),
                    "model_net_benefit": float(observed[model][index]),
                    "ci_lower": float(lower[index]),
                    "ci_upper": float(upper[index]),
                    "confidence_level": float(confidence_level),
                    "n_bootstrap": int(n_bootstrap),
                    "resampling_unit": (
                        "cluster" if aligned_groups is not None else "individual"
                    ),
                }
            )

    contrast_records: list[dict[str, float | int | str]] = []
    for model_a, model_b in combinations(models, 2):
        differences = bootstrap[model_a] - bootstrap[model_b]
        lower, upper = np.quantile(differences, [alpha, 1.0 - alpha], axis=0)
        for index, threshold in enumerate(threshold_values):
            values = differences[:, index]
            p_value = min(
                1.0,
                2.0
                * min(
                    (np.sum(values <= 0.0) + 1) / (len(values) + 1),
                    (np.sum(values >= 0.0) + 1) / (len(values) + 1),
                ),
            )
            contrast_records.append(
                {
                    "model_a": model_a,
                    "model_b": model_b,
                    "threshold": float(threshold),
                    "observed_difference_a_minus_b": float(
                        observed[model_a][index] - observed[model_b][index]
                    ),
                    "ci_lower_a_minus_b": float(lower[index]),
                    "ci_upper_a_minus_b": float(upper[index]),
                    "paired_bootstrap_p_value": float(p_value),
                    "confidence_level": float(confidence_level),
                    "n_bootstrap": int(n_bootstrap),
                    "resampling_unit": (
                        "cluster" if aligned_groups is not None else "individual"
                    ),
                }
            )
    return pd.DataFrame(interval_records), pd.DataFrame(contrast_records)
