"""Plots for held-out SHAP values and fold-stability summaries."""

from __future__ import annotations

import os
import hashlib
import re
from pathlib import Path

from diabetes_pipeline.settings import PROJECT_ROOT


_MPL_CONFIG = PROJECT_ROOT / "outputs" / ".matplotlib"
_MPL_CONFIG.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CONFIG))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


DISPLAY_NAMES = {
    "catboost": "CatBoost",
    "lightgbm": "LightGBM",
    "logistic_regression": "Logistic regression",
    "random_forest": "Random forest",
    "xgboost": "XGBoost",
}


def _display_name(model_name: str) -> str:
    return DISPLAY_NAMES.get(model_name, model_name.replace("_", " ").title())


def _filename_token(value: str) -> str:
    """Return a deterministic path-safe token for a transformed feature name."""

    if re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        return value
    readable = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.-")
    readable = readable[:80] or "feature"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"{readable}_{digest}"


def _finish(figure: plt.Figure, output_path: Path) -> list[Path]:
    png_path = output_path.with_suffix(".png")
    svg_path = output_path.with_suffix(".svg")
    figure.tight_layout()
    figure.savefig(png_path, dpi=300, bbox_inches="tight")
    figure.savefig(svg_path, bbox_inches="tight")
    plt.close(figure)
    return [png_path, svg_path]


def save_shap_plots(
    shap_values: pd.DataFrame,
    global_importance: pd.DataFrame,
    stability_summary: pd.DataFrame,
    output_dir: Path,
    *,
    top_n: int = 10,
    dependence_features: int = 3,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    models = sorted(global_importance["model"].unique())
    outputs: list[Path] = []

    figure, axes = plt.subplots(
        len(models),
        1,
        figsize=(7.5, max(3.0 * len(models), 4.0)),
        squeeze=False,
    )
    for axis, model_name in zip(axes[:, 0], models, strict=False):
        frame = (
            global_importance[global_importance["model"] == model_name]
            .nsmallest(top_n, "rank")
            .sort_values("mean_absolute_shap")
        )
        axis.barh(frame["feature"], frame["mean_absolute_shap"], color="#4C78A8")
        axis.set_title(_display_name(model_name), loc="left", fontsize=10)
        axis.set_xlabel("Mean absolute SHAP value")
    outputs.extend(_finish(figure, output_dir / "global_shap_importance"))

    for model_index, model_name in enumerate(models):
        top_features = (
            global_importance[global_importance["model"] == model_name]
            .nsmallest(top_n, "rank")["feature"]
            .tolist()
        )
        figure, axis = plt.subplots(figsize=(8.0, max(5.0, 0.48 * len(top_features))))
        rng = np.random.default_rng(42 + model_index)
        scatter = None
        for feature_position, feature in enumerate(reversed(top_features)):
            frame = shap_values[
                (shap_values["model"] == model_name)
                & (shap_values["feature"] == feature)
            ]
            feature_value = frame["transformed_feature_value"].to_numpy(dtype=float)
            finite = np.isfinite(feature_value)
            normalized = np.full(len(feature_value), 0.5)
            if finite.any():
                lower, upper = np.quantile(feature_value[finite], [0.05, 0.95])
                if upper > lower:
                    normalized[finite] = np.clip(
                        (feature_value[finite] - lower) / (upper - lower), 0.0, 1.0
                    )
            jitter = rng.normal(0.0, 0.10, size=len(frame))
            scatter = axis.scatter(
                frame["shap_value"],
                feature_position + jitter,
                c=normalized,
                cmap="coolwarm",
                vmin=0,
                vmax=1,
                s=10,
                alpha=0.55,
                linewidths=0,
            )
        axis.axvline(0.0, color="0.45", linewidth=1)
        axis.set_yticks(range(len(top_features)), labels=list(reversed(top_features)))
        axis.set_xlabel("SHAP contribution to model output")
        axis.set_title(f"{_display_name(model_name)} held-out SHAP distribution")
        if scatter is not None:
            colorbar = figure.colorbar(scatter, ax=axis, pad=0.02)
            colorbar.set_label("Feature value: low to high")
        outputs.extend(_finish(figure, output_dir / f"shap_beeswarm_{model_name}"))

        for feature in top_features[:dependence_features]:
            frame = shap_values[
                (shap_values["model"] == model_name)
                & (shap_values["feature"] == feature)
            ].copy()
            x = frame["raw_feature_value"].where(
                frame["raw_feature_value"].notna(),
                frame["transformed_feature_value"],
            )
            finite = np.isfinite(x.to_numpy(dtype=float))
            if finite.sum() < 3:
                continue
            figure, axis = plt.subplots(figsize=(6.5, 4.8))
            axis.scatter(
                x[finite],
                frame.loc[finite, "shap_value"],
                s=13,
                alpha=0.35,
                color="#4C78A8",
                linewidths=0,
            )
            try:
                quantile_bin = pd.qcut(x[finite], q=min(10, finite.sum()), duplicates="drop")
                trend = (
                    pd.DataFrame(
                        {
                            "x": x[finite].to_numpy(dtype=float),
                            "shap": frame.loc[finite, "shap_value"].to_numpy(dtype=float),
                            "bin": quantile_bin,
                        }
                    )
                    .groupby("bin", observed=True)
                    .agg(x=("x", "median"), shap=("shap", "median"))
                )
                axis.plot(trend["x"], trend["shap"], color="#E45756", linewidth=2)
            except ValueError:
                pass
            axis.axhline(0.0, color="0.45", linestyle="--", linewidth=1)
            axis.set(
                xlabel=feature,
                ylabel="SHAP contribution to model output",
                title=f"{_display_name(model_name)}: {feature}",
            )
            outputs.extend(
                _finish(
                    figure,
                    output_dir
                    / f"shap_dependence_{model_name}_{_filename_token(feature)}",
                )
            )

    if not stability_summary.empty:
        frame = stability_summary.sort_values("model")
        positions = np.arange(len(frame))
        width = 0.36
        figure, axis = plt.subplots(figsize=(8.0, 4.8))
        axis.bar(
            positions - width / 2,
            frame["mean_feature_rank_spearman"],
            width,
            label="Rank Spearman",
            color="#4C78A8",
        )
        axis.bar(
            positions + width / 2,
            frame["mean_top_k_jaccard"],
            width,
            label="Top-k Jaccard",
            color="#F58518",
        )
        axis.set_xticks(
            positions,
            labels=[_display_name(name) for name in frame["model"]],
            rotation=20,
            ha="right",
        )
        axis.set_ylim(0, 1)
        axis.set_ylabel("Mean pairwise stability")
        axis.set_title("Fold-to-fold SHAP importance stability")
        axis.legend()
        outputs.extend(_finish(figure, output_dir / "shap_stability"))
    return outputs
