"""Publication-oriented diagnostic plots from held-out predictions."""

from __future__ import annotations

import os
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
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    average_precision_score,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)


DISPLAY_NAMES = {
    "catboost": "CatBoost",
    "lightgbm": "LightGBM",
    "logistic_regression": "Logistic regression",
    "random_forest": "Random forest",
    "xgboost": "XGBoost",
}


def _display_name(model_name: str) -> str:
    return DISPLAY_NAMES.get(model_name, model_name.replace("_", " ").title())


def _finish(figure: plt.Figure, output_path: Path) -> list[Path]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    png_path = output_path.with_suffix(".png")
    svg_path = output_path.with_suffix(".svg")
    figure.tight_layout()
    figure.savefig(png_path, dpi=300, bbox_inches="tight")
    figure.savefig(svg_path, bbox_inches="tight")
    plt.close(figure)
    return [png_path, svg_path]


def save_evaluation_plots(
    predictions: pd.DataFrame,
    decision_curves: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    """Write ROC, PR, calibration, distribution, and decision-curve figures."""

    output_dir.mkdir(parents=True, exist_ok=True)
    model_names = sorted(predictions["model"].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, max(len(model_names), 1)))
    color_map = dict(zip(model_names, colors, strict=False))
    outputs: list[Path] = []

    figure, axis = plt.subplots(figsize=(6.4, 5.2))
    for model_name in model_names:
        frame = predictions[predictions["model"] == model_name]
        false_positive_rate, true_positive_rate, _ = roc_curve(
            frame["target"], frame["probability_calibrated"]
        )
        score = roc_auc_score(frame["target"], frame["probability_calibrated"])
        axis.plot(
            false_positive_rate,
            true_positive_rate,
            label=f"{_display_name(model_name)} ({score:.3f})",
            color=color_map[model_name],
        )
    axis.plot([0, 1], [0, 1], "--", color="0.55", linewidth=1)
    axis.set(xlabel="False-positive rate", ylabel="Sensitivity", title="ROC curves")
    axis.legend(fontsize=8)
    outputs.extend(_finish(figure, output_dir / "roc_curves"))

    figure, axis = plt.subplots(figsize=(6.4, 5.2))
    prevalence = float(predictions["target"].mean())
    for model_name in model_names:
        frame = predictions[predictions["model"] == model_name]
        precision, recall, _ = precision_recall_curve(
            frame["target"], frame["probability_calibrated"]
        )
        score = average_precision_score(
            frame["target"], frame["probability_calibrated"]
        )
        axis.plot(
            recall,
            precision,
            label=f"{_display_name(model_name)} ({score:.3f})",
            color=color_map[model_name],
        )
    axis.axhline(prevalence, linestyle="--", color="0.55", linewidth=1)
    axis.set(xlabel="Recall", ylabel="Precision", title="Precision-recall curves")
    axis.legend(fontsize=8)
    outputs.extend(_finish(figure, output_dir / "precision_recall_curves"))

    figure, axis = plt.subplots(figsize=(6.4, 5.2))
    for model_name in model_names:
        frame = predictions[predictions["model"] == model_name]
        observed, predicted = calibration_curve(
            frame["target"],
            frame["probability_calibrated"],
            n_bins=min(10, max(3, len(frame) // 20)),
            strategy="quantile",
        )
        axis.plot(
            predicted,
            observed,
            marker="o",
            markersize=3,
            label=_display_name(model_name),
            color=color_map[model_name],
        )
    axis.plot([0, 1], [0, 1], "--", color="0.55", linewidth=1)
    axis.set(
        xlabel="Mean predicted probability",
        ylabel="Observed event rate",
        title="Calibration curves",
        xlim=(0, 1),
        ylim=(0, 1),
    )
    axis.legend(fontsize=8)
    outputs.extend(_finish(figure, output_dir / "calibration_curves"))

    figure, axes = plt.subplots(
        len(model_names),
        1,
        figsize=(7.0, max(2.2 * len(model_names), 3.2)),
        sharex=True,
        squeeze=False,
    )
    bins = np.linspace(0, 1, 21)
    for axis, model_name in zip(axes[:, 0], model_names, strict=False):
        frame = predictions[predictions["model"] == model_name]
        axis.hist(
            frame.loc[frame["target"] == 0, "probability_calibrated"],
            bins=bins,
            alpha=0.65,
            label="No diabetes",
            color="#4C78A8",
        )
        axis.hist(
            frame.loc[frame["target"] == 1, "probability_calibrated"],
            bins=bins,
            alpha=0.65,
            label="Diabetes",
            color="#E45756",
        )
        axis.set_ylabel("Count")
        axis.set_title(_display_name(model_name), loc="left", fontsize=10)
    axes[0, 0].legend(fontsize=8)
    axes[-1, 0].set_xlabel("Calibrated predicted probability")
    outputs.extend(_finish(figure, output_dir / "probability_distributions"))

    figure, axis = plt.subplots(figsize=(7.0, 5.2))
    for model_name in model_names:
        frame = decision_curves[decision_curves["model"] == model_name]
        axis.plot(
            frame["threshold"],
            frame["model_net_benefit"],
            label=_display_name(model_name),
            color=color_map[model_name],
        )
    reference = decision_curves[decision_curves["model"] == model_names[0]]
    axis.plot(
        reference["threshold"],
        reference["treat_all_net_benefit"],
        "--",
        color="0.35",
        label="Treat all",
    )
    axis.axhline(0.0, linestyle=":", color="0.2", label="Treat none")
    axis.set(
        xlabel="Threshold probability",
        ylabel="Net benefit",
        title="Decision-curve analysis",
        xlim=(0.01, 0.80),
    )
    maximum_net_benefit = float(
        max(
            decision_curves["model_net_benefit"].max(),
            decision_curves["treat_all_net_benefit"].max(),
        )
    )
    axis.set_ylim(-0.05, max(0.10, maximum_net_benefit * 1.08))
    axis.legend(fontsize=8)
    outputs.extend(_finish(figure, output_dir / "decision_curve"))
    return outputs
