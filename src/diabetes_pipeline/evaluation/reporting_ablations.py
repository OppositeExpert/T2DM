"""Artifact-based panel-size and explanation-reporting ablations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from diabetes_pipeline.settings import source_tree_sha256


@dataclass(frozen=True)
class ReportingAblationResult:
    output_dir: Path
    panel_path: Path
    explanation_path: Path
    report_path: Path


def panel_size_residuals(summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {"scenario", "available_feature_count", "system", "brier_score", "average_precision"}
    missing = sorted(required - set(summary.columns))
    if missing:
        raise ValueError(f"Routing summary lacks columns: {missing}")
    preferred = "robust_single_model"
    system = preferred if preferred in set(summary["system"]) else "availability_router"
    frame = summary[summary["system"] == system].copy().sort_values("available_feature_count")
    diagnostics = []
    for metric in ("brier_score", "average_precision"):
        x = frame["available_feature_count"].to_numpy(dtype=float)
        y = frame[metric].to_numpy(dtype=float)
        slope, intercept = np.polyfit(x, y, 1)
        fitted = intercept + slope * x
        denominator = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1.0 - np.sum((y - fitted) ** 2) / denominator if denominator else np.nan
        frame[f"{metric}_size_only_expected"] = fitted
        frame[f"{metric}_named_panel_residual"] = y - fitted
        diagnostics.append({"system": system, "metric": metric, "slope_per_feature": slope, "intercept": intercept, "r_squared": r_squared, "panel_count": len(frame)})
    return frame, pd.DataFrame(diagnostics)


def explanation_reporting_comparison(encoded: pd.DataFrame, grouped: pd.DataFrame) -> pd.DataFrame:
    required = {"model", "feature", "mean_absolute_shap", "rank"}
    if required - set(encoded) or required - set(grouped):
        raise ValueError("Explanation tables lack model, feature, importance, or rank")
    records = []
    for model in sorted(set(encoded["model"]) & set(grouped["model"])):
        left = encoded[encoded["model"] == model]
        right = grouped[grouped["model"] == model]
        merged = left[["feature", "rank"]].merge(
            right[["feature", "rank"]], on="feature", suffixes=("_encoded", "_grouped")
        )
        correlation = spearmanr(merged["rank_encoded"], merged["rank_grouped"]).statistic if len(merged) > 1 else np.nan
        records.append({
            "model": model,
            "encoded_feature_count": len(left),
            "grouped_original_feature_count": len(right),
            "shared_feature_count": len(merged),
            "rank_spearman_shared_features": correlation,
            "top_encoded_feature": str(left.sort_values("rank").iloc[0]["feature"]),
            "top_grouped_feature": str(right.sort_values("rank").iloc[0]["feature"]),
            "top_feature_agreement": str(left.sort_values("rank").iloc[0]["feature"]) == str(right.sort_values("rank").iloc[0]["feature"]),
        })
    return pd.DataFrame(records)


def run_reporting_ablations(study_dir: Path | str) -> ReportingAblationResult:
    study_dir = Path(study_dir).resolve()
    metadata = json.loads((study_dir / "experiment_metadata.json").read_text())
    profile = dict(metadata["profile"])
    if str(profile.get("name")) == "final" or bool(profile.get("locked", False)):
        raise PermissionError("Reporting ablations are development-only")
    routing_path = study_dir / "availability_routing" / "summary_metrics.csv"
    encoded_path = study_dir / "explanations" / "global_shap_importance.csv"
    grouped_path = study_dir / "explanations" / "global_shap_importance_original_features.csv"
    for required in (routing_path, encoded_path, grouped_path):
        if not required.exists():
            raise FileNotFoundError(f"Required artifact is missing: {required}")
    panel, panel_diagnostics = panel_size_residuals(pd.read_csv(routing_path))
    explanation = explanation_reporting_comparison(pd.read_csv(encoded_path), pd.read_csv(grouped_path))
    output_dir = study_dir / "ablations" / "reporting_ablations"
    output_dir.mkdir(parents=True, exist_ok=True)
    panel_path = output_dir / "panel_size_heuristic_ablation.csv"
    panel_diagnostics_path = output_dir / "panel_size_fit_diagnostics.csv"
    explanation_path = output_dir / "explanation_grouping_ablation.csv"
    metadata_path = output_dir / "metadata.json"
    report_path = output_dir / "Reporting_Ablations.md"
    panel.to_csv(panel_path, index=False)
    panel_diagnostics.to_csv(panel_diagnostics_path, index=False)
    explanation.to_csv(explanation_path, index=False)
    metadata_path.write_text(json.dumps({
        "dataset": metadata["dataset"], "source_study": str(study_dir),
        "profile": profile["name"], "development_only": True,
        "panel_size_only_is_descriptive_non_deployable": True,
        "grouped_original_feature_reporting_primary": True,
        "source_tree_sha256": source_tree_sha256(), "final_outcome_access_authorized": False,
    }, indent=2, sort_keys=True))
    r2 = panel_diagnostics.set_index("metric")["r_squared"].to_dict()
    report_path.write_text(
        "# Reporting Ablations\n\n"
        f"**Dataset:** `{metadata['dataset']}`\n\n"
        f"Panel size alone explained R-squared={r2.get('brier_score', np.nan):.3f} "
        f"for Brier and {r2.get('average_precision', np.nan):.3f} for AP across named panels. "
        "Residuals show the contribution of panel composition beyond feature count.\n\n"
        "Grouped original-feature SHAP is the primary explanation output; encoded-feature "
        "results are retained as an implementation diagnostic.\n"
    )
    return ReportingAblationResult(output_dir, panel_path, explanation_path, report_path)
