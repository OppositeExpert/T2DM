"""Matched full-panel versus reduced-panel performance contrasts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.comparisons import (
    paired_bootstrap_model_comparisons,
)
from diabetes_pipeline.evaluation.metrics import binary_metrics


@dataclass(frozen=True)
class PanelContrastResult:
    study_dir: Path
    output_dir: Path
    predictions_path: Path
    contrasts_path: Path
    report_path: Path


REQUIRED_COLUMNS = {
    "dataset",
    "scenario",
    "available_feature_count",
    "model",
    "row_id",
    "group_id",
    "target",
    "probability_calibrated",
}


def aggregate_panel_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Return one probability per model, panel, and participant."""

    missing = sorted(REQUIRED_COLUMNS - set(predictions.columns))
    if missing:
        raise ValueError(f"Panel predictions are missing columns: {missing}")
    frame = predictions.copy()
    frame["row_id"] = frame["row_id"].astype(str)
    frame["group_id"] = frame["group_id"].fillna("").astype(str)
    has_repeats = "repeat" in frame.columns
    if has_repeats:
        duplicate = frame.duplicated(["model", "scenario", "row_id", "repeat"])
        if duplicate.any():
            raise ValueError(
                "Each model/panel/participant must have one prediction per repeat"
            )
        expected_repeats = int(frame["repeat"].nunique())
        stability = frame.groupby(
            ["model", "scenario", "row_id"], sort=False
        ).agg(
            target_values=("target", "nunique"),
            group_values=("group_id", "nunique"),
            repeat_count=("repeat", "nunique"),
        )
        if stability["target_values"].ne(1).any():
            raise ValueError("Participant outcome changed across panel predictions")
        if stability["group_values"].ne(1).any():
            raise ValueError("Participant group changed across panel predictions")
        if stability["repeat_count"].ne(expected_repeats).any():
            raise ValueError("A participant is missing from one or more repeats")
        aggregated = (
            frame.groupby(["model", "scenario", "row_id"], as_index=False, sort=True)
            .agg(
                dataset=("dataset", "first"),
                available_feature_count=("available_feature_count", "first"),
                group_id=("group_id", "first"),
                target=("target", "first"),
                probability_calibrated=("probability_calibrated", "mean"),
                probability_repeat_sd=("probability_calibrated", "std"),
                repeat_count=("repeat", "nunique"),
            )
            .reset_index(drop=True)
        )
        aggregated["probability_repeat_sd"] = aggregated[
            "probability_repeat_sd"
        ].fillna(0.0)
        aggregated["estimation_scope"] = "participant_mean_across_repeats"
        return aggregated

    if frame.duplicated(["model", "scenario", "row_id"]).any():
        raise ValueError("Holdout panel predictions contain duplicate participants")
    frame["repeat_count"] = 1
    frame["probability_repeat_sd"] = 0.0
    roles = frame.get("evaluation_role", pd.Series(dtype=str)).dropna().unique()
    frame["estimation_scope"] = str(roles[0]) if len(roles) == 1 else "holdout_test"
    return frame[
        [
            "model",
            "scenario",
            "row_id",
            "dataset",
            "available_feature_count",
            "group_id",
            "target",
            "probability_calibrated",
            "probability_repeat_sd",
            "repeat_count",
            "estimation_scope",
        ]
    ].sort_values(["model", "scenario", "row_id"]).reset_index(drop=True)


def _groups_for_reference(frame: pd.DataFrame) -> np.ndarray | None:
    values = frame.sort_values("row_id")["group_id"].to_numpy(dtype=str)
    return values if np.any(np.char.str_len(values) > 0) else None


def _holm_adjust(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["holm_adjusted_p_value"] = np.nan
    for metric in result["metric"].unique():
        values = (
            result.loc[result["metric"] == metric, "paired_bootstrap_p_value"]
            .dropna()
            .sort_values()
        )
        running_maximum = 0.0
        count = len(values)
        for rank, (index, p_value) in enumerate(values.items()):
            adjusted = min(1.0, float(p_value) * (count - rank))
            running_maximum = max(running_maximum, adjusted)
            result.loc[index, "holm_adjusted_p_value"] = running_maximum
    return result


def matched_panel_bootstrap_contrasts(
    predictions: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare every reduced panel with full on identical participants."""

    aggregated = aggregate_panel_predictions(predictions)
    scenarios = set(aggregated["scenario"].astype(str))
    if "full" not in scenarios:
        raise ValueError("Matched panel inference requires a 'full' scenario")
    reduced_scenarios = sorted(scenarios - {"full"})
    if not reduced_scenarios:
        raise ValueError("Matched panel inference requires at least one reduced panel")

    contrast_records: list[dict[str, Any]] = []
    comparison_index = 0
    for model in sorted(aggregated["model"].astype(str).unique()):
        model_frame = aggregated[aggregated["model"].astype(str) == model]
        full = model_frame[model_frame["scenario"] == "full"].copy()
        full_rows = set(full["row_id"])
        if not len(full):
            raise ValueError(f"Model {model!r} has no full-panel predictions")
        for scenario in reduced_scenarios:
            reduced = model_frame[model_frame["scenario"] == scenario].copy()
            if set(reduced["row_id"]) != full_rows:
                raise ValueError(
                    f"Model {model!r} panel {scenario!r} is not matched to full rows"
                )
            full_comparison = full[
                ["row_id", "target", "probability_calibrated"]
            ].copy()
            full_comparison["model"] = "full_panel"
            reduced_comparison = reduced[
                ["row_id", "target", "probability_calibrated"]
            ].copy()
            reduced_comparison["model"] = "reduced_panel"
            comparison_index += 1
            comparison = paired_bootstrap_model_comparisons(
                pd.concat([full_comparison, reduced_comparison], ignore_index=True),
                n_bootstrap=int(n_bootstrap),
                seed=int(seed) + comparison_index,
                groups=_groups_for_reference(full),
            )
            full_metrics = binary_metrics(
                full["target"].to_numpy(dtype=int),
                full["probability_calibrated"].to_numpy(dtype=float),
                threshold=0.5,
            )
            reduced_metrics = binary_metrics(
                reduced["target"].to_numpy(dtype=int),
                reduced["probability_calibrated"].to_numpy(dtype=float),
                threshold=0.5,
            )
            for row in comparison.itertuples(index=False):
                # Model labels guarantee full_panel - reduced_panel orientation.
                full_minus_reduced = float(row.observed_difference_a_minus_b)
                full_minus_reduced_lower = float(row.ci_lower_a_minus_b)
                full_minus_reduced_upper = float(row.ci_upper_a_minus_b)
                reduced_minus_full = -full_minus_reduced
                reduced_minus_full_lower = -full_minus_reduced_upper
                reduced_minus_full_upper = -full_minus_reduced_lower
                if row.direction == "higher":
                    degradation = full_minus_reduced
                    degradation_lower = full_minus_reduced_lower
                    degradation_upper = full_minus_reduced_upper
                else:
                    degradation = reduced_minus_full
                    degradation_lower = reduced_minus_full_lower
                    degradation_upper = reduced_minus_full_upper
                contrast_records.append(
                    {
                        "dataset": str(full["dataset"].iloc[0]),
                        "model": model,
                        "full_scenario": "full",
                        "reduced_scenario": scenario,
                        "full_feature_count": int(
                            full["available_feature_count"].iloc[0]
                        ),
                        "reduced_feature_count": int(
                            reduced["available_feature_count"].iloc[0]
                        ),
                        "metric": str(row.metric),
                        "direction": str(row.direction),
                        "full_estimate": float(full_metrics[str(row.metric)]),
                        "reduced_estimate": float(reduced_metrics[str(row.metric)]),
                        "observed_reduced_minus_full": reduced_minus_full,
                        "ci_lower_reduced_minus_full": reduced_minus_full_lower,
                        "ci_upper_reduced_minus_full": reduced_minus_full_upper,
                        "observed_degradation": degradation,
                        "ci_lower_degradation": degradation_lower,
                        "ci_upper_degradation": degradation_upper,
                        "positive_degradation_is_worse": True,
                        "paired_bootstrap_p_value": float(
                            row.paired_bootstrap_p_value
                        ),
                        "n_bootstrap": int(row.n_bootstrap),
                        "resampling_unit": str(row.resampling_unit),
                        "estimation_scope": str(full["estimation_scope"].iloc[0]),
                    }
                )
    contrasts = _holm_adjust(pd.DataFrame(contrast_records))
    return aggregated, contrasts


def _render_report(metadata: dict[str, Any], contrasts: pd.DataFrame) -> str:
    brier = contrasts[contrasts["metric"] == "brier_score"].copy()
    average_precision = contrasts[contrasts["metric"] == "average_precision"][
        [
            "model",
            "reduced_scenario",
            "observed_degradation",
            "ci_lower_degradation",
            "ci_upper_degradation",
        ]
    ].rename(
        columns={
            "observed_degradation": "ap_degradation",
            "ci_lower_degradation": "ap_ci_lower",
            "ci_upper_degradation": "ap_ci_upper",
        }
    )
    table = brier.merge(
        average_precision,
        on=["model", "reduced_scenario"],
        how="left",
    )
    lines = [
        "# Matched Full-Panel Versus Reduced-Panel Contrasts",
        "",
        f"**Dataset:** `{metadata['dataset']}`",
        "",
        f"**Evidence tier:** `{metadata['evidence_tier']}`",
        "",
        f"**Estimation scope:** `{metadata['estimation_scope']}`",
        "",
        "Every comparison uses the same model family, the same participants, and "
        "panel-specific development-selected calibration. Positive degradation means "
        "the reduced panel performed worse than the full panel.",
        "",
        "| Model | Reduced panel | Brier degradation (95% CI) | AP degradation (95% CI) | Holm p for Brier |",
        "|---|---|---:|---:|---:|",
    ]
    for _, row in table.sort_values(["model", "reduced_scenario"]).iterrows():
        lines.append(
            f"| {row['model']} | {row['reduced_scenario']} | "
            f"{row['observed_degradation']:.4f} "
            f"({row['ci_lower_degradation']:.4f}, {row['ci_upper_degradation']:.4f}) | "
            f"{row['ap_degradation']:.4f} "
            f"({row['ap_ci_lower']:.4f}, {row['ap_ci_upper']:.4f}) | "
            f"{row['holm_adjusted_p_value']:.4f} |"
        )
    lines.extend(
        [
            "",
            "These contrasts isolate feature-panel availability from algorithm routing. "
            "Smoke and development-pilot outputs are engineering evidence only and cannot "
            "support a final superiority, non-inferiority, or clinical claim.",
            "",
        ]
    )
    return "\n".join(lines)


def run_matched_panel_contrasts(
    study_dir: Path | str,
    *,
    n_bootstrap: int | None = None,
    seed: int | None = None,
) -> PanelContrastResult:
    """Backfill matched panel contrasts for a completed routing study."""

    study_dir = Path(study_dir).resolve()
    experiment_metadata = json.loads(
        (study_dir / "experiment_metadata.json").read_text(encoding="utf-8")
    )
    profile = dict(experiment_metadata["profile"])
    output_dir = study_dir / "availability_routing"
    stress_path = output_dir / "stress_predictions.csv"
    if not stress_path.exists():
        raise FileNotFoundError(
            f"Run availability routing before panel contrasts: {stress_path}"
        )
    predictions = pd.read_csv(stress_path, low_memory=False)
    bootstrap_count = int(
        profile["n_bootstrap"] if n_bootstrap is None else n_bootstrap
    )
    analysis_seed = int(profile["seed"] + 900_000 if seed is None else seed)
    aggregated, contrasts = matched_panel_bootstrap_contrasts(
        predictions,
        n_bootstrap=bootstrap_count,
        seed=analysis_seed,
    )
    evidence_tier = (
        "publication_candidate"
        if str(profile.get("name")) == "final" and bool(profile.get("locked"))
        else "execution_only"
        if str(profile.get("name")) == "smoke"
        else "development_only"
    )
    metadata = {
        "schema_version": "1.0",
        "experiment_id": experiment_metadata["experiment_id"],
        "dataset": experiment_metadata["dataset"],
        "profile": profile.get("name"),
        "evidence_tier": evidence_tier,
        "estimation_scope": str(aggregated["estimation_scope"].iloc[0]),
        "n_bootstrap": bootstrap_count,
        "seed": analysis_seed,
        "same_model_family": True,
        "matched_participants": True,
        "panel_specific_calibration": True,
        "multiplicity_family": "all model-by-reduced-panel contrasts within metric",
        "final_outcome_access_authorized": False,
    }
    predictions_path = output_dir / "participant_panel_predictions.csv"
    contrasts_path = output_dir / "matched_panel_contrasts.csv"
    metadata_path = output_dir / "matched_panel_contrast_metadata.json"
    report_path = output_dir / "matched_panel_contrast_report.md"
    aggregated.to_csv(predictions_path, index=False)
    contrasts.to_csv(contrasts_path, index=False)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    report_path.write_text(_render_report(metadata, contrasts), encoding="utf-8")
    paper_table_dir = study_dir / "paper_tables"
    paper_table_dir.mkdir(parents=True, exist_ok=True)
    contrasts.to_csv(paper_table_dir / "matched_panel_contrasts.csv", index=False)
    return PanelContrastResult(
        study_dir=study_dir,
        output_dir=output_dir,
        predictions_path=predictions_path,
        contrasts_path=contrasts_path,
        report_path=report_path,
    )
