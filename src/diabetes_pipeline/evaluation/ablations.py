"""Artifact-based, paired development ablations for the publication pipeline."""

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
from diabetes_pipeline.evaluation.repeated_cv import aggregate_repeated_predictions


@dataclass(frozen=True)
class AblationResult:
    study_dir: Path
    output_dir: Path
    inventory_path: Path
    report_path: Path


def _holm_adjust(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["holm_adjusted_p_value"] = np.nan
    if result.empty:
        return result
    for metric in result["metric"].unique():
        values = (
            result.loc[result["metric"] == metric, "paired_bootstrap_p_value"]
            .dropna()
            .sort_values()
        )
        count = len(values)
        running_maximum = 0.0
        for rank, (index, p_value) in enumerate(values.items()):
            adjusted = min(1.0, float(p_value) * (count - rank))
            running_maximum = max(running_maximum, adjusted)
            result.loc[index, "holm_adjusted_p_value"] = running_maximum
    return result


def _groups(frame: pd.DataFrame) -> np.ndarray | None:
    values = frame.sort_values("row_id")["group_id"].fillna("").to_numpy(dtype=str)
    return values if np.any(np.char.str_len(values) > 0) else None


def _aggregate_base_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    if "repeat" in predictions.columns:
        return aggregate_repeated_predictions(predictions)
    required = {
        "model",
        "row_id",
        "group_id",
        "target",
        "probability_raw",
        "probability_calibrated",
    }
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Base predictions are missing columns: {missing}")
    frame = predictions.copy()
    frame["row_id"] = frame["row_id"].astype(str)
    frame["group_id"] = frame["group_id"].fillna("").astype(str)
    if frame.duplicated(["model", "row_id"]).any():
        raise ValueError("Holdout predictions contain duplicate model/row pairs")
    roles = frame.get("evaluation_role", pd.Series(dtype=str)).dropna().unique()
    frame["estimation_scope"] = str(roles[0]) if len(roles) == 1 else "holdout_test"
    return frame


def calibration_ablation(
    predictions: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
) -> pd.DataFrame:
    """Compare selected calibration with the identical raw model scores."""

    aggregated = _aggregate_base_predictions(predictions)
    records: list[dict[str, Any]] = []
    for model_index, (model, frame) in enumerate(
        aggregated.groupby("model", sort=True)
    ):
        raw = frame[["row_id", "target", "probability_raw"]].rename(
            columns={"probability_raw": "probability_calibrated"}
        )
        raw["model"] = "raw"
        calibrated = frame[
            ["row_id", "target", "probability_calibrated"]
        ].copy()
        calibrated["model"] = "selected_calibration"
        comparison = paired_bootstrap_model_comparisons(
            pd.concat([raw, calibrated], ignore_index=True),
            n_bootstrap=int(n_bootstrap),
            seed=int(seed) + model_index,
            groups=_groups(frame),
        )
        for row in comparison.itertuples(index=False):
            # Alphabetical labels yield raw - selected_calibration.
            raw_minus_selected = float(row.observed_difference_a_minus_b)
            raw_minus_selected_lower = float(row.ci_lower_a_minus_b)
            raw_minus_selected_upper = float(row.ci_upper_a_minus_b)
            if row.direction == "higher":
                improvement = -raw_minus_selected
                lower = -raw_minus_selected_upper
                upper = -raw_minus_selected_lower
            else:
                improvement = raw_minus_selected
                lower = raw_minus_selected_lower
                upper = raw_minus_selected_upper
            records.append(
                {
                    "model": str(model),
                    "metric": str(row.metric),
                    "direction": str(row.direction),
                    "observed_improvement_selected_over_raw": improvement,
                    "ci_lower_improvement": lower,
                    "ci_upper_improvement": upper,
                    "positive_improvement_is_better": True,
                    "paired_bootstrap_p_value": float(
                        row.paired_bootstrap_p_value
                    ),
                    "n_bootstrap": int(row.n_bootstrap),
                    "resampling_unit": str(row.resampling_unit),
                    "estimation_scope": str(frame["estimation_scope"].iloc[0]),
                }
            )
    return _holm_adjust(pd.DataFrame(records))


def model_family_ablation(
    predictions: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
) -> pd.DataFrame:
    """Compare every available tree family with Logistic Regression."""

    aggregated = _aggregate_base_predictions(predictions)
    models = sorted(aggregated["model"].astype(str).unique())
    if "logistic_regression" not in models:
        raise ValueError("Model-family ablation requires logistic_regression")
    reference = (
        aggregated[aggregated["model"] == "logistic_regression"]
        .sort_values("row_id")
        .reset_index(drop=True)
    )
    comparison = paired_bootstrap_model_comparisons(
        aggregated[["model", "row_id", "target", "probability_calibrated"]],
        n_bootstrap=int(n_bootstrap),
        seed=int(seed),
        groups=_groups(reference),
    )
    records: list[dict[str, Any]] = []
    for row in comparison.itertuples(index=False):
        if "logistic_regression" not in {row.model_a, row.model_b}:
            continue
        tree_model = row.model_b if row.model_a == "logistic_regression" else row.model_a
        tree_minus_logistic = (
            float(row.observed_difference_a_minus_b)
            if row.model_a == tree_model
            else -float(row.observed_difference_a_minus_b)
        )
        if row.model_a == tree_model:
            tree_minus_logistic_lower = float(row.ci_lower_a_minus_b)
            tree_minus_logistic_upper = float(row.ci_upper_a_minus_b)
        else:
            tree_minus_logistic_lower = -float(row.ci_upper_a_minus_b)
            tree_minus_logistic_upper = -float(row.ci_lower_a_minus_b)
        if row.direction == "higher":
            improvement = tree_minus_logistic
            lower = tree_minus_logistic_lower
            upper = tree_minus_logistic_upper
        else:
            improvement = -tree_minus_logistic
            lower = -tree_minus_logistic_upper
            upper = -tree_minus_logistic_lower
        records.append(
            {
                "tree_model": str(tree_model),
                "reference_model": "logistic_regression",
                "metric": str(row.metric),
                "direction": str(row.direction),
                "observed_improvement_tree_over_logistic": improvement,
                "ci_lower_improvement": lower,
                "ci_upper_improvement": upper,
                "positive_improvement_is_better": True,
                "paired_bootstrap_p_value": float(row.paired_bootstrap_p_value),
                "n_bootstrap": int(row.n_bootstrap),
                "resampling_unit": str(row.resampling_unit),
                "estimation_scope": str(reference["estimation_scope"].iloc[0]),
            }
        )
    return _holm_adjust(pd.DataFrame(records))


def _selector_choice(scores: pd.DataFrame, criterion: str) -> str:
    if criterion == "brier":
        ordered = scores.sort_values(
            ["brier_score", "log_loss", "average_precision", "model"],
            ascending=[True, True, False, True],
        )
    elif criterion == "average_precision":
        ordered = scores.sort_values(
            ["average_precision", "brier_score", "log_loss", "model"],
            ascending=[False, True, True, True],
        )
    elif criterion == "log_loss":
        ordered = scores.sort_values(
            ["log_loss", "brier_score", "average_precision", "model"],
            ascending=[True, True, False, True],
        )
    else:
        raise ValueError(f"Unknown selector criterion: {criterion}")
    return str(ordered.iloc[0]["model"])


def build_selector_predictions(
    development_scores: pd.DataFrame,
    stress_predictions: pd.DataFrame,
) -> pd.DataFrame:
    """Construct label-blind selector systems from development-only scores."""

    criteria = ("brier", "average_precision", "log_loss")
    repeated = "repeat" in development_scores.columns
    group_columns = (
        ["repeat", "outer_fold", "scenario"] if repeated else ["scenario"]
    )
    frames: list[pd.DataFrame] = []
    for keys, scores in development_scores.groupby(group_columns, sort=True):
        key_tuple = keys if isinstance(keys, tuple) else (keys,)
        filters = pd.Series(True, index=stress_predictions.index)
        for column, value in zip(group_columns, key_tuple, strict=True):
            filters &= stress_predictions[column] == value
        candidates = stress_predictions[filters]
        for criterion in criteria:
            selected_model = _selector_choice(scores, criterion)
            selected = candidates[candidates["model"] == selected_model].copy()
            if selected.empty:
                raise ValueError(
                    f"No stress predictions for selector {criterion}/{selected_model}"
                )
            selected["system"] = f"selector_{criterion}"
            selected["selected_model"] = selected_model
            frames.append(selected)
    return pd.concat(frames, ignore_index=True)


def _aggregate_system_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    frame = predictions.copy()
    frame["row_id"] = frame["row_id"].astype(str)
    frame["group_id"] = frame["group_id"].fillna("").astype(str)
    if "repeat" in frame.columns:
        if frame.duplicated(["system", "scenario", "row_id", "repeat"]).any():
            raise ValueError("System predictions are duplicated within a repeat")
        expected_repeats = int(frame["repeat"].nunique())
        aggregated = (
            frame.groupby(["system", "scenario", "row_id"], as_index=False, sort=True)
            .agg(
                dataset=("dataset", "first"),
                group_id=("group_id", "first"),
                target=("target", "first"),
                probability_calibrated=("probability_calibrated", "mean"),
                repeat_count=("repeat", "nunique"),
                selected_model=("selected_model", lambda values: "|".join(sorted(set(values)))),
            )
            .reset_index(drop=True)
        )
        if aggregated["repeat_count"].ne(expected_repeats).any():
            raise ValueError("System/participant predictions are incomplete across repeats")
        aggregated["estimation_scope"] = "participant_mean_across_repeats"
        return aggregated
    if frame.duplicated(["system", "scenario", "row_id"]).any():
        raise ValueError("Holdout system predictions contain duplicate rows")
    frame["repeat_count"] = 1
    roles = frame.get("evaluation_role", pd.Series(dtype=str)).dropna().unique()
    frame["estimation_scope"] = str(roles[0]) if len(roles) == 1 else "holdout_test"
    return frame


def _system_comparisons(
    predictions: pd.DataFrame,
    *,
    reference_system: str,
    n_bootstrap: int,
    seed: int,
    ablation_name: str,
) -> pd.DataFrame:
    aggregated = _aggregate_system_predictions(predictions)
    records: list[dict[str, Any]] = []
    for scenario_index, (scenario, frame) in enumerate(
        aggregated.groupby("scenario", sort=True)
    ):
        systems = set(frame["system"].astype(str))
        if reference_system not in systems:
            raise ValueError(
                f"Scenario {scenario!r} has no reference system {reference_system!r}"
            )
        reference = (
            frame[frame["system"] == reference_system]
            .sort_values("row_id")
            .reset_index(drop=True)
        )
        comparison_input = frame[
            ["system", "row_id", "target", "probability_calibrated"]
        ].rename(columns={"system": "model"})
        comparison = paired_bootstrap_model_comparisons(
            comparison_input,
            n_bootstrap=int(n_bootstrap),
            seed=int(seed) + scenario_index,
            groups=_groups(reference),
        )
        for row in comparison.itertuples(index=False):
            if reference_system not in {row.model_a, row.model_b}:
                continue
            alternative = row.model_b if row.model_a == reference_system else row.model_a
            reference_minus_alternative = (
                float(row.observed_difference_a_minus_b)
                if row.model_a == reference_system
                else -float(row.observed_difference_a_minus_b)
            )
            if row.model_a == reference_system:
                difference_lower = float(row.ci_lower_a_minus_b)
                difference_upper = float(row.ci_upper_a_minus_b)
            else:
                difference_lower = -float(row.ci_upper_a_minus_b)
                difference_upper = -float(row.ci_lower_a_minus_b)
            if row.direction == "higher":
                improvement = reference_minus_alternative
                lower = difference_lower
                upper = difference_upper
            else:
                improvement = -reference_minus_alternative
                lower = -difference_upper
                upper = -difference_lower
            records.append(
                {
                    "ablation": ablation_name,
                    "scenario": str(scenario),
                    "reference_system": reference_system,
                    "alternative_system": str(alternative),
                    "metric": str(row.metric),
                    "direction": str(row.direction),
                    "observed_improvement_reference_over_alternative": improvement,
                    "ci_lower_improvement": lower,
                    "ci_upper_improvement": upper,
                    "positive_improvement_is_better": True,
                    "paired_bootstrap_p_value": float(
                        row.paired_bootstrap_p_value
                    ),
                    "n_bootstrap": int(row.n_bootstrap),
                    "resampling_unit": str(row.resampling_unit),
                    "estimation_scope": str(frame["estimation_scope"].iloc[0]),
                }
            )
    return _holm_adjust(pd.DataFrame(records))


def selector_metric_ablation(
    development_scores: pd.DataFrame,
    stress_predictions: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
) -> pd.DataFrame:
    selected = build_selector_predictions(development_scores, stress_predictions)
    return _system_comparisons(
        selected,
        reference_system="selector_brier",
        n_bootstrap=n_bootstrap,
        seed=seed,
        ablation_name="router_selection_metric",
    )


def router_baseline_ablation(
    system_predictions: pd.DataFrame,
    development_scores: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
) -> pd.DataFrame:
    frame = system_predictions.copy()
    if "robust_single_model" not in set(frame["system"].astype(str)):
        robust_scores = (
            development_scores.groupby("model", as_index=False)
            .agg(
                brier_score=("brier_score", "mean"),
                log_loss=("log_loss", "mean"),
                average_precision=("average_precision", "mean"),
            )
        )
        robust_model = _selector_choice(robust_scores, "brier")
        robust = frame[frame["system"].astype(str) == robust_model].copy()
        robust["system"] = "robust_single_model"
        robust["selected_model"] = robust_model
        if "selected_model" not in frame.columns:
            frame["selected_model"] = frame["model"].astype(str)
        frame = pd.concat([frame, robust], ignore_index=True)
    candidates = frame[
        frame["system"].isin(["availability_router", "robust_single_model"])
    ].copy()
    if "selected_model" not in candidates.columns:
        candidates["selected_model"] = candidates["model"].astype(str)
    return _system_comparisons(
        candidates,
        reference_system="availability_router",
        n_bootstrap=n_bootstrap,
        seed=seed,
        ablation_name="routing_vs_robust_single_model",
    )


def _render_report(
    metadata: dict[str, Any],
    calibration: pd.DataFrame,
    router: pd.DataFrame,
    selector: pd.DataFrame,
    family: pd.DataFrame,
) -> str:
    def significant_count(frame: pd.DataFrame) -> int:
        if frame.empty:
            return 0
        return int((frame["holm_adjusted_p_value"] < 0.05).sum())

    lines = [
        "# Development Ablation Results",
        "",
        f"**Dataset:** `{metadata['dataset']}`",
        "",
        f"**Evidence tier:** `{metadata['evidence_tier']}`",
        "",
        "**Ablation phase complete:** `false`",
        "",
        "## Completed artifact-based components",
        "",
        "| Component | Contrasts | Holm-significant contrasts |",
        "|---|---:|---:|",
        f"| Selected calibration versus raw | {len(calibration)} | {significant_count(calibration)} |",
        f"| Availability router versus robust fixed model | {len(router)} | {significant_count(router)} |",
        f"| Brier selector versus AP/log-loss selectors | {len(selector)} | {significant_count(selector)} |",
        f"| Tree families versus Logistic Regression | "
        f"{'unavailable' if family.empty else len(family)} | "
        f"{significant_count(family)} |",
        "| Matched full versus reduced panels | existing paired artifact | see `availability_routing/matched_panel_contrasts.csv` |",
        "",
        "All comparisons use identical held-out participants, paired bootstrap "
        "resampling, and metric-wise Holm correction. Positive improvement columns "
        "always favor the named reference system.",
        "",
        "## Still required before the ablation blocker can close",
        "",
    ]
    for name, reason in metadata["pending"].items():
        if reason != "not_applicable":
            lines.append(f"- `{name}`: {reason}.")
    lines.extend(
        [
            "",
            "No protocol completion flag is changed by this development report.",
            "",
        ]
    )
    return "\n".join(lines)


def run_artifact_ablation_suite(
    study_dir: Path | str,
    *,
    n_bootstrap: int | None = None,
    seed: int | None = None,
) -> AblationResult:
    """Run all ablations supported by already held-out prediction artifacts."""

    study_dir = Path(study_dir).resolve()
    experiment_metadata = json.loads(
        (study_dir / "experiment_metadata.json").read_text(encoding="utf-8")
    )
    profile = dict(experiment_metadata["profile"])
    bootstrap_count = int(
        profile["n_bootstrap"] if n_bootstrap is None else n_bootstrap
    )
    analysis_seed = int(profile["seed"] + 1_000_000 if seed is None else seed)
    base_predictions_path = (
        study_dir / "test_predictions.csv"
        if (study_dir / "test_predictions.csv").exists()
        else study_dir / "predictions.csv"
    )
    routing_dir = study_dir / "availability_routing"
    required = [
        base_predictions_path,
        routing_dir / "development_scores.csv",
        routing_dir / "stress_predictions.csv",
        routing_dir / "system_predictions.csv",
        routing_dir / "matched_panel_contrasts.csv",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Required ablation artifacts are missing: {missing}")
    base_predictions = pd.read_csv(base_predictions_path, low_memory=False)
    development_scores = pd.read_csv(
        routing_dir / "development_scores.csv", low_memory=False
    )
    stress_predictions = pd.read_csv(
        routing_dir / "stress_predictions.csv", low_memory=False
    )
    system_predictions = pd.read_csv(
        routing_dir / "system_predictions.csv", low_memory=False
    )

    calibration = calibration_ablation(
        base_predictions,
        n_bootstrap=bootstrap_count,
        seed=analysis_seed + 10_000,
    )
    family_unavailable_reason = None
    try:
        family = model_family_ablation(
            base_predictions,
            n_bootstrap=bootstrap_count,
            seed=analysis_seed + 20_000,
        )
    except ValueError as exc:
        if "requires logistic_regression" not in str(exc):
            raise
        family_unavailable_reason = str(exc)
        family = pd.DataFrame(
            columns=[
                "tree_model",
                "reference_model",
                "metric",
                "direction",
                "observed_improvement_tree_over_logistic",
                "ci_lower_improvement",
                "ci_upper_improvement",
                "positive_improvement_is_better",
                "paired_bootstrap_p_value",
                "n_bootstrap",
                "resampling_unit",
                "estimation_scope",
                "holm_adjusted_p_value",
            ]
        )
    selector = selector_metric_ablation(
        development_scores,
        stress_predictions,
        n_bootstrap=bootstrap_count,
        seed=analysis_seed + 30_000,
    )
    router = router_baseline_ablation(
        system_predictions,
        development_scores,
        n_bootstrap=bootstrap_count,
        seed=analysis_seed + 40_000,
    )
    evidence_tier = (
        "publication_candidate"
        if str(profile.get("name")) == "final" and bool(profile.get("locked"))
        else "execution_only"
        if str(profile.get("name")) == "smoke"
        else "development_only"
    )
    completed = {
        "calibration_vs_raw": "calibration_ablation.csv",
        "router_vs_robust_single_model": "router_baseline_ablation.csv",
        "selector_brier_vs_ap_and_log_loss": "selector_metric_ablation.csv",
        "full_vs_reduced_panels": "../availability_routing/matched_panel_contrasts.csv",
    }
    pending = {
        "missing_indicator_retraining": "identical-fold retraining required",
        "panel_specific_training": "identical-fold retraining required",
        "random_feature_dropout": "prespecified stress generation required",
        "applicability_guards": "selective-prediction phase dependency",
        "global_preprocessing_leakage_demo": "non-deployable retraining demonstration",
        "sylhet_naive_split_demo": (
            "non-deployable retraining demonstration"
            if experiment_metadata["dataset"] == "sylhet"
            else "not_applicable"
        ),
    }
    if family_unavailable_reason is None:
        completed["tree_families_vs_logistic_regression"] = (
            "model_family_ablation.csv"
        )
    else:
        pending["tree_families_vs_logistic_regression"] = (
            family_unavailable_reason + "; regenerate a study containing the baseline"
        )
    inventory = {
        "schema_version": "1.0",
        "dataset": experiment_metadata["dataset"],
        "experiment_id": experiment_metadata["experiment_id"],
        "profile": profile.get("name"),
        "evidence_tier": evidence_tier,
        "n_bootstrap": bootstrap_count,
        "seed": analysis_seed,
        "ablation_study_complete": False,
        "completed": completed,
        "pending": pending,
        "final_outcome_access_authorized": False,
    }
    output_dir = study_dir / "ablations"
    output_dir.mkdir(parents=True, exist_ok=True)
    calibration.to_csv(output_dir / "calibration_ablation.csv", index=False)
    router.to_csv(output_dir / "router_baseline_ablation.csv", index=False)
    selector.to_csv(output_dir / "selector_metric_ablation.csv", index=False)
    family.to_csv(output_dir / "model_family_ablation.csv", index=False)
    inventory_path = output_dir / "ablation_inventory.json"
    inventory_path.write_text(
        json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8"
    )
    report_path = output_dir / "Ablation_Results.md"
    report_path.write_text(
        _render_report(inventory, calibration, router, selector, family),
        encoding="utf-8",
    )
    paper_table_dir = study_dir / "paper_tables"
    paper_table_dir.mkdir(parents=True, exist_ok=True)
    for source, name in (
        (calibration, "calibration_ablation.csv"),
        (router, "router_baseline_ablation.csv"),
        (selector, "selector_metric_ablation.csv"),
        (family, "model_family_ablation.csv"),
    ):
        source.to_csv(paper_table_dir / name, index=False)
    return AblationResult(
        study_dir=study_dir,
        output_dir=output_dir,
        inventory_path=inventory_path,
        report_path=report_path,
    )
