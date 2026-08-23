"""Participant-level inference for repeated held-out cross-validation predictions."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.bootstrap import bootstrap_metric_intervals
from diabetes_pipeline.evaluation.comparisons import paired_bootstrap_model_comparisons


REQUIRED_PREDICTION_COLUMNS = {
    "model",
    "row_id",
    "group_id",
    "repeat",
    "target",
    "probability_raw",
    "probability_calibrated",
}


def aggregate_repeated_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Average one held-out prediction per participant across completed repeats."""

    missing = sorted(REQUIRED_PREDICTION_COLUMNS - set(predictions.columns))
    if missing:
        raise ValueError(f"Repeated predictions are missing columns: {missing}")
    frame = predictions.copy()
    frame["row_id"] = frame["row_id"].astype(str)
    frame["group_id"] = frame["group_id"].fillna("").astype(str)
    duplicate_key = frame.duplicated(["model", "row_id", "repeat"])
    if duplicate_key.any():
        raise ValueError("Each model/participant must have one held-out prediction per repeat")

    stability = frame.groupby(["model", "row_id"], sort=False).agg(
        target_values=("target", "nunique"),
        group_values=("group_id", "nunique"),
        repeat_count=("repeat", "nunique"),
    )
    if stability["target_values"].ne(1).any():
        raise ValueError("Participant outcome changed across repeated predictions")
    if stability["group_values"].ne(1).any():
        raise ValueError("Participant group changed across repeated predictions")
    expected_repeats = int(frame["repeat"].nunique())
    if stability["repeat_count"].ne(expected_repeats).any():
        raise ValueError("A participant is missing from one or more completed repeats")

    first_columns = [
        column
        for column in ("experiment_id", "dataset", "task", "evaluation_role")
        if column in frame.columns
    ]
    aggregations: dict[str, Any] = {
        column: (column, "first") for column in first_columns
    }
    aggregations.update(
        {
            "group_id": ("group_id", "first"),
            "target": ("target", "first"),
            "repeat_count": ("repeat", "nunique"),
            "probability_raw": ("probability_raw", "mean"),
            "probability_raw_repeat_sd": ("probability_raw", "std"),
            "probability_calibrated": ("probability_calibrated", "mean"),
            "probability_calibrated_repeat_sd": (
                "probability_calibrated",
                "std",
            ),
        }
    )
    aggregated = (
        frame.groupby(["model", "row_id"], sort=True, as_index=False)
        .agg(**aggregations)
        .reset_index(drop=True)
    )
    for column in (
        "probability_raw_repeat_sd",
        "probability_calibrated_repeat_sd",
    ):
        aggregated[column] = aggregated[column].fillna(0.0)
    aggregated["estimation_scope"] = "participant_mean_across_repeats"
    return aggregated


def participant_level_repeated_cv_inference(
    predictions: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return participant predictions, CIs, and paired model comparisons."""

    aggregated = aggregate_repeated_predictions(predictions)
    interval_records: list[dict[str, Any]] = []
    for model_index, (model, frame) in enumerate(
        aggregated.groupby("model", sort=True)
    ):
        group_values = frame["group_id"].astype(str).to_numpy(dtype=str)
        groups = group_values if np.any(np.char.str_len(group_values) > 0) else None
        for probability_index, probability_version in enumerate(("raw", "calibrated")):
            probability_column = f"probability_{probability_version}"
            rows = bootstrap_metric_intervals(
                frame["target"].to_numpy(dtype=int),
                frame[probability_column].to_numpy(dtype=float),
                threshold=0.5,
                n_bootstrap=int(n_bootstrap),
                seed=int(seed) + model_index * 10_000 + probability_index,
                groups=groups,
            )
            for row in rows:
                interval_records.append(
                    {
                        "model": str(model),
                        "probability_version": probability_version,
                        "threshold_policy": "fixed_0_5",
                        "estimation_scope": "participant_mean_across_repeats",
                        **row,
                    }
                )
    intervals = pd.DataFrame(interval_records)

    reference_model = sorted(aggregated["model"].unique())[0]
    reference = (
        aggregated[aggregated["model"] == reference_model]
        .sort_values("row_id")
        .reset_index(drop=True)
    )
    group_values = reference["group_id"].astype(str).to_numpy(dtype=str)
    groups = group_values if np.any(np.char.str_len(group_values) > 0) else None
    comparisons = paired_bootstrap_model_comparisons(
        aggregated[["model", "row_id", "target", "probability_calibrated"]],
        n_bootstrap=int(n_bootstrap),
        seed=int(seed) + 500_000,
        groups=groups,
    )
    if not comparisons.empty:
        comparisons.insert(0, "estimation_scope", "participant_mean_across_repeats")
    return aggregated, intervals, comparisons
