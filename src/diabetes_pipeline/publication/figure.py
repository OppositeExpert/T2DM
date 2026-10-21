"""Journal-quality consolidated figure built from canonical study artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.decision_curve import decision_curve


DATASET_LABELS = {
    "pidd": "PIDD",
    "sylhet": "Sylhet",
    "brfss": "BRFSS",
    "hospital130": "Hospital130 (30-day readmission)",
}


def _attach_dataset_identity(frame: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Attach dataset identity once and reject contradictory source rows."""

    frame = frame.copy()
    if "dataset" in frame:
        observed = set(frame["dataset"].dropna().astype(str).unique())
        if observed and observed != {dataset_name}:
            raise RuntimeError(
                f"Source artifact has contradictory dataset: "
                f"expected {dataset_name!r}, observed {sorted(observed)!r}"
            )
    else:
        frame.insert(0, "dataset", dataset_name)
    return frame


def _calibration_bins(frame: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    ordered = frame.sort_values("probability_calibrated").reset_index(drop=True)
    records = []
    for index, positions in enumerate(np.array_split(np.arange(len(ordered)), bins)):
        if not len(positions):
            continue
        subset = ordered.iloc[positions]
        records.append(
            {
                "bin": index + 1,
                "n": len(subset),
                "mean_predicted_probability": float(
                    subset["probability_calibrated"].mean()
                ),
                "observed_event_rate": float(subset["target"].mean()),
            }
        )
    return pd.DataFrame(records)


def build_consolidated_figure(
    study_dirs: Mapping[str, Path | str],
    output_dir: Path | str,
) -> list[Path]:
    """Build calibration, decision-curve, and availability-degradation panels."""

    output_dir = Path(output_dir).resolve()
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    calibration_frames = []
    decision_frames = []
    degradation_frames = []
    for dataset_name, raw_study in sorted(study_dirs.items()):
        study = Path(raw_study).resolve()
        policy = pd.read_csv(
            study
            / "runtime_policy_evaluation"
            / "participant_policy_predictions.csv"
        )
        policy = policy[
            policy["system"].eq("availability_router")
            & policy["status"].eq("predicted")
        ].copy()
        calibration = _calibration_bins(policy)
        calibration = _attach_dataset_identity(calibration, dataset_name)
        calibration_frames.append(calibration)
        curve = decision_curve(
            policy["target"].to_numpy(dtype=int),
            policy["probability_calibrated"].to_numpy(dtype=float),
            thresholds=np.linspace(0.01, 0.50, 50),
        )
        curve = _attach_dataset_identity(curve, dataset_name)
        decision_frames.append(curve)

        from diabetes_pipeline.publication.protocol_correction import publication_panel_source
        import json
        metadata = json.loads((study / "experiment_metadata.json").read_text())
        routing = publication_panel_source(study, metadata)
        routing = routing[routing["system"].eq("availability_router")].copy()
        full = routing[routing["scenario"].eq("full")]
        if len(full) != 1:
            raise ValueError(f"{dataset_name}: expected one full-panel router row")
        routing["auroc_degradation_from_full"] = (
            float(full.iloc[0]["auroc"]) - routing["auroc"]
        )
        routing["average_precision_degradation_from_full"] = (
            float(full.iloc[0]["average_precision"]) - routing["average_precision"]
        )
        routing = _attach_dataset_identity(routing, dataset_name)
        degradation_frames.append(routing)

    calibration_data = pd.concat(calibration_frames, ignore_index=True)
    decision_data = pd.concat(decision_frames, ignore_index=True)
    degradation_data = pd.concat(degradation_frames, ignore_index=True)
    calibration_data.to_csv(data_dir / "panel_a_calibration.csv", index=False)
    decision_data.to_csv(data_dir / "panel_b_decision_curves.csv", index=False)
    degradation_data.to_csv(
        data_dir / "panel_c_availability_degradation.csv", index=False
    )

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "legend.fontsize": 7.5,
        }
    )
    colors = dict(zip(sorted(study_dirs), plt.get_cmap("tab10").colors))
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), constrained_layout=True)

    axes[0].plot([0, 1], [0, 1], linestyle="--", color="0.55", linewidth=1)
    for dataset_name, frame in calibration_data.groupby("dataset", sort=True):
        axes[0].plot(
            frame["mean_predicted_probability"],
            frame["observed_event_rate"],
            marker="o",
            markersize=3,
            linewidth=1.4,
            color=colors[dataset_name],
            label=DATASET_LABELS[dataset_name],
        )
    axes[0].set(xlabel="Mean predicted probability", ylabel="Observed event rate")
    axes[0].set_title("A  Calibration of the fallback policy", loc="left", weight="bold")
    axes[0].grid(alpha=0.18)

    for dataset_name, frame in decision_data.groupby("dataset", sort=True):
        axes[1].plot(
            frame["threshold"],
            frame["model_net_benefit"],
            linewidth=1.4,
            color=colors[dataset_name],
            label=DATASET_LABELS[dataset_name],
        )
    axes[1].axhline(0, color="0.55", linewidth=1)
    axes[1].set(xlabel="Decision threshold", ylabel="Net benefit")
    axes[1].set_title("B  Decision-curve analysis", loc="left", weight="bold")
    axes[1].grid(alpha=0.18)

    for dataset_name, frame in degradation_data.groupby("dataset", sort=True):
        ordered = frame.sort_values("available_feature_count")
        axes[2].plot(
            ordered["available_feature_count"],
            ordered["average_precision_degradation_from_full"],
            marker="o",
            markersize=3,
            linewidth=1.4,
            color=colors[dataset_name],
            label=DATASET_LABELS[dataset_name],
        )
    axes[2].axhline(0, color="0.55", linewidth=1)
    axes[2].set(xlabel="Available feature count", ylabel="AP loss versus full panel")
    axes[2].set_title("C  Feature-availability degradation", loc="left", weight="bold")
    axes[2].grid(alpha=0.18)
    axes[2].invert_xaxis()
    axes[2].legend(frameon=False, loc="best")

    caption = (
        "Finalized internal validation; datasets and endpoints are not pooled. "
        "Hospital130 is 30-day readmission."
    )
    fig.text(0.5, -0.02, caption, ha="center", va="top", fontsize=8)
    outputs = [
        output_dir / "consolidated_results.png",
        output_dir / "consolidated_results.pdf",
        output_dir / "consolidated_results.svg",
    ]
    fig.savefig(outputs[0], dpi=600, bbox_inches="tight")
    fig.savefig(outputs[1], bbox_inches="tight")
    fig.savefig(outputs[2], bbox_inches="tight")
    plt.close(fig)
    return outputs
