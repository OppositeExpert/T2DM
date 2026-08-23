"""Fold-to-fold stability summaries for SHAP feature importance."""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def importance_tables(
    shap_values: pd.DataFrame,
    *,
    top_k: int = 5,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return fold, global, pairwise-stability, and model-stability tables."""

    fold_importance = (
        shap_values.groupby(
            ["model", "repeat", "outer_fold", "feature"], as_index=False
        )
        .agg(
            mean_absolute_shap=("absolute_shap_value", "mean"),
            mean_shap_value=("shap_value", "mean"),
            explained_rows=("row_id", "nunique"),
        )
    )
    fold_importance["rank"] = fold_importance.groupby(
        ["model", "repeat", "outer_fold"]
    )["mean_absolute_shap"].rank(method="first", ascending=False)

    global_rows: list[dict[str, float | int | str]] = []
    for (model_name, feature), frame in shap_values.groupby(
        ["model", "feature"], sort=True
    ):
        finite = frame[["transformed_feature_value", "shap_value"]].dropna()
        if (
            len(finite) > 2
            and finite["transformed_feature_value"].nunique() > 1
            and finite["shap_value"].nunique() > 1
        ):
            association = float(
                spearmanr(
                    finite["transformed_feature_value"],
                    finite["shap_value"],
                ).statistic
            )
        else:
            association = float("nan")
        global_rows.append(
            {
                "model": model_name,
                "feature": feature,
                "mean_absolute_shap": float(frame["absolute_shap_value"].mean()),
                "mean_shap_value": float(frame["shap_value"].mean()),
                "feature_shap_spearman": association,
                "explained_rows": int(frame["row_id"].nunique()),
            }
        )
    global_importance = pd.DataFrame(global_rows)
    global_importance["rank"] = global_importance.groupby("model")[
        "mean_absolute_shap"
    ].rank(method="first", ascending=False)
    global_importance = global_importance.sort_values(["model", "rank"])

    stability_records: list[dict[str, float | int | str]] = []
    for model_name, model_frame in fold_importance.groupby("model", sort=True):
        model_frame = model_frame.copy()
        model_frame["fold_id"] = (
            "r"
            + model_frame["repeat"].astype(str)
            + "_f"
            + model_frame["outer_fold"].astype(str)
        )
        pivot = model_frame.pivot(
            index="feature", columns="fold_id", values="mean_absolute_shap"
        ).fillna(0.0)
        top_features = {
            fold_id: set(
                model_frame[model_frame["fold_id"] == fold_id]
                .nsmallest(top_k, "rank")["feature"]
            )
            for fold_id in pivot.columns
        }
        for fold_a, fold_b in combinations(pivot.columns, 2):
            correlation = float(spearmanr(pivot[fold_a], pivot[fold_b]).statistic)
            union = top_features[fold_a] | top_features[fold_b]
            jaccard = (
                len(top_features[fold_a] & top_features[fold_b]) / len(union)
                if union
                else float("nan")
            )
            stability_records.append(
                {
                    "model": model_name,
                    "fold_a": fold_a,
                    "fold_b": fold_b,
                    "feature_rank_spearman": correlation,
                    "top_k": int(top_k),
                    "top_k_jaccard": float(jaccard),
                    "top_k_overlap_count": int(
                        len(top_features[fold_a] & top_features[fold_b])
                    ),
                }
            )
    pairwise_stability = pd.DataFrame(stability_records)
    if pairwise_stability.empty:
        pairwise_stability = pd.DataFrame(
            columns=[
                "model",
                "fold_a",
                "fold_b",
                "feature_rank_spearman",
                "top_k",
                "top_k_jaccard",
                "top_k_overlap_count",
            ]
        )
        stability_summary = pd.DataFrame(
            columns=[
                "model",
                "fold_pairs",
                "mean_feature_rank_spearman",
                "minimum_feature_rank_spearman",
                "mean_top_k_jaccard",
                "minimum_top_k_jaccard",
            ]
        )
    else:
        stability_summary = (
            pairwise_stability.groupby("model", as_index=False)
            .agg(
                fold_pairs=("fold_a", "size"),
                mean_feature_rank_spearman=("feature_rank_spearman", "mean"),
                minimum_feature_rank_spearman=("feature_rank_spearman", "min"),
                mean_top_k_jaccard=("top_k_jaccard", "mean"),
                minimum_top_k_jaccard=("top_k_jaccard", "min"),
            )
        )
    return fold_importance, global_importance, pairwise_stability, stability_summary
