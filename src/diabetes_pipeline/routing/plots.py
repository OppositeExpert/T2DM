"""Figures for feature-availability stress and routing results."""

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
import seaborn as sns  # noqa: E402


DISPLAY_NAMES = {
    "availability_router": "Availability router",
    "full_panel_champion": "Full-panel champion",
    "robust_single_model": "Robust single model",
    "catboost": "CatBoost",
    "lightgbm": "LightGBM",
    "random_forest": "Random forest",
    "xgboost": "XGBoost",
}


def _display(value: str) -> str:
    return DISPLAY_NAMES.get(value, value.replace("_", " ").title())


def _finish(figure: plt.Figure, path: Path) -> list[Path]:
    png = path.with_suffix(".png")
    svg = path.with_suffix(".svg")
    figure.tight_layout()
    figure.savefig(png, dpi=300, bbox_inches="tight")
    figure.savefig(svg, bbox_inches="tight")
    plt.close(figure)
    return [png, svg]


def save_routing_plots(
    summary: pd.DataFrame,
    selections: pd.DataFrame,
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    scenario_order = (
        summary[["scenario", "available_feature_count"]]
        .drop_duplicates()
        .sort_values(["available_feature_count", "scenario"])
        ["scenario"]
        .tolist()
    )
    systems = [
        "availability_router",
        "full_panel_champion",
        "robust_single_model",
        "catboost",
        "lightgbm",
        "random_forest",
        "xgboost",
    ]
    colors = plt.cm.tab10(np.linspace(0, 1, len(systems)))
    for metric, ylabel, higher_is_better in (
        ("average_precision", "Average precision", True),
        ("brier_score", "Brier score", False),
    ):
        figure, axis = plt.subplots(figsize=(9.0, 5.4))
        for system, color in zip(systems, colors, strict=False):
            frame = summary[summary["system"] == system].set_index("scenario")
            if frame.empty:
                continue
            values = [frame.loc[scenario, metric] for scenario in scenario_order]
            axis.plot(
                range(len(scenario_order)),
                values,
                marker="o",
                linewidth=2 if system == "availability_router" else 1.3,
                label=_display(system),
                color=color,
            )
        axis.set_xticks(
            range(len(scenario_order)),
            labels=[scenario.replace("_", " ") for scenario in scenario_order],
            rotation=25,
            ha="right",
        )
        axis.set_ylabel(ylabel)
        axis.set_title(
            f"Feature-availability stress: {ylabel.lower()} "
            f"({'higher' if higher_is_better else 'lower'} is better)"
        )
        axis.legend(fontsize=8, ncol=2)
        outputs.extend(_finish(figure, output_dir / f"routing_{metric}"))

    selection_counts = (
        selections.groupby(["scenario", "selected_model"])
        .size()
        .unstack(fill_value=0)
        .reindex(scenario_order)
    )
    figure, axis = plt.subplots(figsize=(7.5, 5.0))
    sns.heatmap(
        selection_counts,
        annot=True,
        fmt="d",
        cmap="Blues",
        cbar_kws={"label": "Outer folds selected"},
        ax=axis,
    )
    axis.set_xlabel("Selected model")
    axis.set_ylabel("Availability scenario")
    axis.set_xticklabels([_display(label) for label in selection_counts.columns])
    axis.set_yticklabels(
        [label.replace("_", " ") for label in selection_counts.index],
        rotation=0,
    )
    axis.set_title("Development-only availability-router selections")
    outputs.extend(_finish(figure, output_dir / "routing_selection_heatmap"))
    return outputs
