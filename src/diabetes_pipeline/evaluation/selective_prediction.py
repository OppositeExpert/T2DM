"""Development-only risk-coverage analysis for routing systems."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.bootstrap import bootstrap_metric_intervals
from diabetes_pipeline.settings import source_tree_sha256


DEFAULT_COVERAGES = (1.0, 0.95, 0.90, 0.80, 0.70)
SELECTIVE_METRICS = (
    "auroc",
    "average_precision",
    "brier_score",
    "log_loss",
    "calibration_intercept",
    "calibration_slope",
    "sensitivity",
    "specificity",
)


@dataclass(frozen=True)
class SelectivePredictionResult:
    study_dir: Path
    output_dir: Path
    metrics_path: Path
    decisions_path: Path
    report_path: Path


def aggregate_routing_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Return one probability per system, panel, and participant."""

    required = {
        "dataset",
        "system",
        "scenario",
        "row_id",
        "group_id",
        "target",
        "probability_calibrated",
    }
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Routing predictions lack columns: {missing}")
    frame = predictions.copy()
    if "repeat" not in frame:
        frame["repeat"] = 0
    frame["row_id"] = frame["row_id"].astype(str)
    frame["group_id"] = frame["group_id"].fillna("").astype(str)
    keys = ["system", "scenario", "row_id", "repeat"]
    if frame.duplicated(keys).any():
        raise ValueError("Routing predictions are duplicated within a repeat")
    stability = frame.groupby(["system", "scenario", "row_id"], sort=False).agg(
        outcomes=("target", "nunique"),
        groups=("group_id", "nunique"),
    )
    if stability["outcomes"].ne(1).any() or stability["groups"].ne(1).any():
        raise ValueError("Participant outcome or group changed across repeats")
    return (
        frame.groupby(["system", "scenario", "row_id"], as_index=False, sort=True)
        .agg(
            dataset=("dataset", "first"),
            group_id=("group_id", "first"),
            target=("target", "first"),
            probability_calibrated=("probability_calibrated", "mean"),
            repeat_count=("repeat", "nunique"),
        )
        .reset_index(drop=True)
    )


def _accepted_mask(frame: pd.DataFrame, target_coverage: float) -> np.ndarray:
    if not 0.0 < target_coverage <= 1.0:
        raise ValueError("Coverage levels must be in (0, 1]")
    target_rows = int(np.ceil(len(frame) * target_coverage))
    groups = frame["group_id"].fillna("").astype(str)
    if groups.str.len().gt(0).any():
        group_frame = (
            frame.assign(_group=groups)
            .groupby("_group", as_index=False)
            .agg(confidence=("confidence", "mean"), rows=("row_id", "size"))
            .sort_values(["confidence", "_group"], ascending=[False, True])
        )
        group_frame["cumulative_rows"] = group_frame["rows"].cumsum()
        accepted_groups = group_frame.loc[
            group_frame["cumulative_rows"].shift(fill_value=0).lt(target_rows),
            "_group",
        ]
        return groups.isin(set(accepted_groups)).to_numpy()
    ordered = frame.sort_values(
        ["confidence", "row_id"], ascending=[False, True]
    ).index[:target_rows]
    return frame.index.isin(ordered)


def selective_prediction_analysis(
    predictions: pd.DataFrame,
    *,
    coverages: Sequence[float],
    n_bootstrap: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Evaluate outcome-blind probability certainty at fixed coverage levels."""

    aggregated = aggregate_routing_predictions(predictions)
    aggregated["confidence"] = (
        2.0 * (aggregated["probability_calibrated"] - 0.5).abs()
    )
    decision_frames: list[pd.DataFrame] = []
    metric_records: list[dict[str, Any]] = []
    interval_records: list[dict[str, Any]] = []
    analysis_index = 0
    for (system, scenario), frame in aggregated.groupby(
        ["system", "scenario"], sort=True
    ):
        frame = frame.reset_index(drop=True)
        for target_coverage in coverages:
            accepted = _accepted_mask(frame, float(target_coverage))
            decisions = frame.copy()
            decisions["target_coverage"] = float(target_coverage)
            decisions["accepted"] = accepted
            decisions["abstained"] = ~accepted
            decisions["abstention_reason"] = np.where(
                accepted, "accepted", "low_probability_certainty"
            )
            decision_frames.append(decisions)
            retained = decisions[decisions["accepted"]].reset_index(drop=True)
            rejected = decisions[~decisions["accepted"]].reset_index(drop=True)
            actual_coverage = len(retained) / len(decisions)
            total_positive_events = int(decisions["target"].sum())
            retained_positive_events = int(retained["target"].sum())
            rejected_positive_events = int(rejected["target"].sum())
            has_groups = decisions["group_id"].fillna("").astype(str).str.len().gt(0).any()
            base = {
                "dataset": str(frame["dataset"].iloc[0]),
                "system": str(system),
                "scenario": str(scenario),
                "confidence_definition": "two_times_absolute_probability_minus_0_5",
                "target_coverage": float(target_coverage),
                "actual_coverage": float(actual_coverage),
                "accepted_n": int(len(retained)),
                "abstained_n": int(len(decisions) - len(retained)),
                "total_group_count": (
                    int(decisions["group_id"].nunique()) if has_groups else None
                ),
                "accepted_group_count": (
                    int(retained["group_id"].nunique()) if has_groups else None
                ),
                "abstained_group_count": (
                    int(rejected["group_id"].nunique()) if has_groups else None
                ),
                "positive_events": retained_positive_events,
                "negative_events": int((retained["target"] == 0).sum()),
                "total_positive_events": total_positive_events,
                "positive_event_coverage": (
                    retained_positive_events / total_positive_events
                    if total_positive_events
                    else float("nan")
                ),
                "accepted_prevalence": (
                    retained_positive_events / len(retained)
                    if len(retained)
                    else float("nan")
                ),
                "rejected_prevalence": (
                    rejected_positive_events / len(rejected)
                    if len(rejected)
                    else float("nan")
                ),
            }
            if retained["target"].nunique() < 2:
                metric_records.append({**base, "status": "suppressed_single_class"})
                analysis_index += 1
                continue
            groups_array = retained["group_id"].to_numpy(dtype=str)
            groups = (
                groups_array
                if np.any(np.char.str_len(groups_array) > 0)
                else None
            )
            intervals = bootstrap_metric_intervals(
                retained["target"].to_numpy(dtype=int),
                retained["probability_calibrated"].to_numpy(dtype=float),
                threshold=0.5,
                n_bootstrap=int(n_bootstrap),
                seed=int(seed) + analysis_index,
                metric_names=SELECTIVE_METRICS,
                groups=groups,
            )
            estimates = {str(row["metric"]): float(row["estimate"]) for row in intervals}
            metric_records.append({**base, "status": "estimated", **estimates})
            for row in intervals:
                interval_records.append({**base, **row})
            analysis_index += 1
    return (
        pd.concat(decision_frames, ignore_index=True),
        pd.DataFrame(metric_records),
        pd.DataFrame(interval_records),
    )


def _render_report(metadata: dict[str, Any], metrics: pd.DataFrame) -> str:
    estimated = metrics[metrics["status"] == "estimated"].copy()
    lines = [
        "# Selective Prediction Development Analysis",
        "",
        f"**Dataset:** `{metadata['dataset']}`",
        "",
        f"**Profile:** `{metadata['profile']}`",
        "",
        "Acceptance is based only on calibrated probability certainty, defined as "
        "twice the absolute distance from 0.5. Outcome labels are used only after "
        "the accepted set is fixed. Complete groups are retained or rejected "
        "together where grouped inference is required.",
        "",
        "| System | Panel | Coverage | Event coverage | Accepted prevalence | Rejected prevalence | Brier | AP | Accepted encounters | Accepted groups |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in estimated.sort_values(
        ["system", "scenario", "target_coverage"],
        ascending=[True, True, False],
    ).iterrows():
        lines.append(
            f"| {row['system']} | {row['scenario']} | "
            f"{row['actual_coverage']:.3f} | "
            f"{row['positive_event_coverage']:.3f} | "
            f"{row['accepted_prevalence']:.3f} | "
            f"{row['rejected_prevalence']:.3f} | "
            f"{row['brier_score']:.4f} | "
            f"{row['average_precision']:.4f} | {int(row['accepted_n'])} | "
            f"{int(row['accepted_group_count']) if pd.notna(row['accepted_group_count']) else 'N/A'} |"
        )
    lines.extend(
        [
            "",
            "This is development-only evidence. Reduced-coverage performance must "
            "always be interpreted with both abstention rate and positive-event "
            "coverage; certainty selection can preferentially retain low-risk cases.",
            "",
        ]
    )
    return "\n".join(lines)


def run_selective_prediction_analysis(
    study_dir: Path | str,
    *,
    systems: Sequence[str] = ("availability_router", "robust_single_model"),
    coverages: Sequence[float] = DEFAULT_COVERAGES,
) -> SelectivePredictionResult:
    """Run selective-prediction analysis from completed routing predictions."""

    study_dir = Path(study_dir).resolve()
    study_metadata = json.loads(
        (study_dir / "experiment_metadata.json").read_text(encoding="utf-8")
    )
    profile = dict(study_metadata["profile"])
    if str(profile.get("name")) == "final" or bool(profile.get("locked", False)):
        raise PermissionError("Selective-prediction development analysis is not a final-run command")
    source_path = study_dir / "availability_routing" / "system_predictions.csv"
    if not source_path.exists():
        raise FileNotFoundError(f"Run availability routing first: {source_path}")
    source = pd.read_csv(source_path, low_memory=False)
    available_systems = set(source["system"].astype(str).unique())
    selected_systems = [system for system in systems if system in available_systems]
    if not selected_systems:
        raise ValueError(
            f"None of the requested systems are available: {sorted(available_systems)}"
        )
    filtered = source[source["system"].isin(selected_systems)].copy()
    decisions, metrics, intervals = selective_prediction_analysis(
        filtered,
        coverages=coverages,
        n_bootstrap=int(profile["n_bootstrap"]),
        seed=int(profile["seed"]) + 1_300_000,
    )
    output_dir = study_dir / "selective_prediction"
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": "1.0",
        "dataset": str(study_metadata["dataset"]),
        "source_study": str(study_dir),
        "profile": str(profile["name"]),
        "evidence_tier": (
            "execution_only"
            if str(profile["name"]) == "smoke"
            else "development_only"
        ),
        "systems": selected_systems,
        "coverages": [float(value) for value in coverages],
        "confidence_definition": "two_times_absolute_probability_minus_0_5",
        "outcome_blind_acceptance_rule": True,
        "group_preserving_acceptance": bool(
            decisions["group_id"].fillna("").astype(str).str.len().gt(0).any()
        ),
        "source_tree_sha256": source_tree_sha256(),
        "selective_prediction_evaluation_complete": False,
        "final_outcome_access_authorized": False,
    }
    decisions_path = output_dir / "acceptance_decisions.csv"
    metrics_path = output_dir / "risk_coverage_metrics.csv"
    intervals_path = output_dir / "risk_coverage_confidence_intervals.csv"
    metadata_path = output_dir / "metadata.json"
    report_path = output_dir / "Selective_Prediction_Analysis.md"
    decisions.to_csv(decisions_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    intervals.to_csv(intervals_path, index=False)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    report_path.write_text(_render_report(metadata, metrics), encoding="utf-8")
    return SelectivePredictionResult(
        study_dir=study_dir,
        output_dir=output_dir,
        metrics_path=metrics_path,
        decisions_path=decisions_path,
        report_path=report_path,
    )
