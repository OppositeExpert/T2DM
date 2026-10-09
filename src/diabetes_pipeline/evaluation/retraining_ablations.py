"""Retraining-dependent development ablations on identical nested-CV splits."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from diabetes_pipeline.calibration.calibrators import select_calibrator
from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.evaluation.comparisons import (
    paired_bootstrap_model_comparisons,
)
from diabetes_pipeline.models.registry import MODEL_NAMES, build_estimator
from diabetes_pipeline.preprocessing.builders import build_preprocessor
from diabetes_pipeline.runner import _selected_outer_splits
from diabetes_pipeline.settings import (
    get_dataset_config,
    source_tree_sha256,
)
from diabetes_pipeline.training.tuning import (
    cross_fitted_probabilities,
    positive_class_weight,
    tune_model,
)


LOGGER = logging.getLogger(__name__)
VARIANTS = {
    "missing_indicator_on": True,
    "missing_indicator_off": False,
}


@dataclass(frozen=True)
class MissingIndicatorAblationResult:
    study_dir: Path
    output_dir: Path
    predictions_path: Path
    contrasts_path: Path
    report_path: Path


def _holm_adjust(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["holm_adjusted_p_value"] = np.nan
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


def _aggregate_variant_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    required = {
        "model",
        "variant",
        "row_id",
        "group_id",
        "repeat",
        "target",
        "probability_raw",
        "probability_calibrated",
    }
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Missing-indicator predictions lack columns: {missing}")
    frame = predictions.copy()
    frame["row_id"] = frame["row_id"].astype(str)
    frame["group_id"] = frame["group_id"].fillna("").astype(str)
    if frame.duplicated(["model", "variant", "row_id", "repeat"]).any():
        raise ValueError("Variant predictions are duplicated within a repeat")
    expected_repeats = int(frame["repeat"].nunique())
    stability = frame.groupby(
        ["model", "variant", "row_id"], sort=False
    ).agg(
        outcomes=("target", "nunique"),
        groups=("group_id", "nunique"),
        repeats=("repeat", "nunique"),
    )
    if stability["outcomes"].ne(1).any():
        raise ValueError("Participant outcome changed across variant predictions")
    if stability["groups"].ne(1).any():
        raise ValueError("Participant group changed across variant predictions")
    if stability["repeats"].ne(expected_repeats).any():
        raise ValueError("Participant is missing from one or more variant repeats")
    return (
        frame.groupby(["model", "variant", "row_id"], as_index=False, sort=True)
        .agg(
            dataset=("dataset", "first"),
            group_id=("group_id", "first"),
            target=("target", "first"),
            probability_raw=("probability_raw", "mean"),
            probability_calibrated=("probability_calibrated", "mean"),
            repeat_count=("repeat", "nunique"),
        )
        .reset_index(drop=True)
    )


def missing_indicator_contrasts(
    predictions: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare indicator-on with indicator-off after participant aggregation."""

    aggregated = _aggregate_variant_predictions(predictions)
    if set(aggregated["variant"].unique()) != set(VARIANTS):
        raise ValueError("Both missing-indicator variants are required")
    records: list[dict[str, Any]] = []
    for model_index, (model, frame) in enumerate(
        aggregated.groupby("model", sort=True)
    ):
        reference = (
            frame[frame["variant"] == "missing_indicator_on"]
            .sort_values("row_id")
            .reset_index(drop=True)
        )
        group_values = reference["group_id"].to_numpy(dtype=str)
        groups = group_values if np.any(np.char.str_len(group_values) > 0) else None
        comparison_input = frame[
            ["variant", "row_id", "target", "probability_calibrated"]
        ].rename(columns={"variant": "model"})
        probability_wide = frame.pivot(
            index="row_id",
            columns="variant",
            values="probability_calibrated",
        ).sort_index()
        numerically_equivalent = bool(
            np.allclose(
                probability_wide["missing_indicator_on"].to_numpy(),
                probability_wide["missing_indicator_off"].to_numpy(),
                rtol=1e-12,
                atol=1e-12,
            )
        )
        if numerically_equivalent:
            # Prevent rank metrics and sign-count p-values from treating floating
            # point noise in functionally identical pipelines as scientific signal.
            on_probability = probability_wide[
                "missing_indicator_on"
            ].to_dict()
            off_mask = comparison_input["model"].eq(
                "missing_indicator_off"
            )
            comparison_input.loc[off_mask, "probability_calibrated"] = (
                comparison_input.loc[off_mask, "row_id"].map(on_probability)
            )
        comparison = paired_bootstrap_model_comparisons(
            comparison_input,
            n_bootstrap=int(n_bootstrap),
            seed=int(seed) + model_index,
            groups=groups,
        )
        for row in comparison.itertuples(index=False):
            # Alphabetical ordering gives missing_indicator_off - on.
            off_minus_on = float(row.observed_difference_a_minus_b)
            off_minus_on_lower = float(row.ci_lower_a_minus_b)
            off_minus_on_upper = float(row.ci_upper_a_minus_b)
            if row.direction == "higher":
                improvement = -off_minus_on
                lower = -off_minus_on_upper
                upper = -off_minus_on_lower
            else:
                improvement = off_minus_on
                lower = off_minus_on_lower
                upper = off_minus_on_upper
            records.append(
                {
                    "model": str(model),
                    "metric": str(row.metric),
                    "direction": str(row.direction),
                    "observed_improvement_indicators_on_over_off": improvement,
                    "ci_lower_improvement": lower,
                    "ci_upper_improvement": upper,
                    "positive_improvement_is_better": True,
                    "paired_bootstrap_p_value": float(
                        row.paired_bootstrap_p_value
                    ),
                    "n_bootstrap": int(row.n_bootstrap),
                    "resampling_unit": str(row.resampling_unit),
                    "estimation_scope": "participant_mean_across_repeats",
                    "numerically_equivalent_predictions_collapsed": (
                        numerically_equivalent
                    ),
                }
            )
    return aggregated, _holm_adjust(pd.DataFrame(records))


def _render_report(metadata: dict[str, Any], contrasts: pd.DataFrame) -> str:
    brier = contrasts[contrasts["metric"] == "brier_score"]
    lines = [
        "# Missing-Indicator Retraining Ablation",
        "",
        f"**Dataset:** `{metadata['dataset']}`",
        "",
        f"**Profile:** `{metadata['profile']}`",
        "",
        f"**Evidence tier:** `{metadata['evidence_tier']}`",
        "",
        "Both variants use identical outer folds, inner folds, model families, "
        "hyperparameter search spaces, trial budgets, calibration candidates, and "
        "random seeds. Each variant is tuned separately because changing the "
        "preprocessing graph can change the optimal model parameters.",
        "",
        "| Model | Brier improvement with indicators on (95% CI) | Holm p |",
        "|---|---:|---:|",
    ]
    for _, row in brier.sort_values("model").iterrows():
        lines.append(
            f"| {row['model']} | "
            f"{row['observed_improvement_indicators_on_over_off']:.4f} "
            f"({row['ci_lower_improvement']:.4f}, {row['ci_upper_improvement']:.4f}) | "
            f"{row['holm_adjusted_p_value']:.4f} |"
        )
    lines.extend(
        [
            "",
            "Positive improvement favors missingness indicators. Smoke and pilot "
            "profiles verify the method but cannot close the ablation blocker or "
            "enter the final manuscript results.",
            "",
        ]
    )
    return "\n".join(lines)


def run_missing_indicator_retraining_ablation(
    study_dir: Path | str,
    *,
    models: Sequence[str] = ("logistic_regression", "random_forest"),
) -> MissingIndicatorAblationResult:
    """Retrain indicator-on/off variants using an existing development split contract."""

    study_dir = Path(study_dir).resolve()
    study_metadata = json.loads(
        (study_dir / "experiment_metadata.json").read_text(encoding="utf-8")
    )
    profile = dict(study_metadata["profile"])
    if str(profile.get("name")) == "final" or bool(profile.get("locked", False)):
        raise PermissionError("Retraining ablations are development-only")
    dataset_name = str(study_metadata["dataset"])
    dataset_cfg = get_dataset_config(dataset_name)
    if not dataset_cfg["evaluation_strategy"].startswith("repeated_nested"):
        raise NotImplementedError(
            "The first missing-indicator runner supports repeated nested-CV datasets"
        )
    unknown = sorted(set(models) - set(MODEL_NAMES))
    if unknown:
        raise ValueError(f"Unknown models: {unknown}")
    dataset = load_dataset(dataset_name)
    manifest = pd.read_csv(study_metadata["split_manifest"], low_memory=False)
    selected_splits = _selected_outer_splits(manifest, profile)
    if not selected_splits:
        raise ValueError("The source study contains no selected outer splits")
    inner_folds = int(
        profile.get("inner_folds_override") or dataset_cfg["inner_folds"]
    )
    model_n_jobs = int(profile.get("model_n_jobs", 1))
    output_dir = study_dir / "ablations" / "missing_indicator_retraining"
    trial_dir = output_dir / "trials"
    output_dir.mkdir(parents=True, exist_ok=True)
    trial_dir.mkdir(parents=True, exist_ok=True)
    prediction_frames: list[pd.DataFrame] = []
    tuning_records: list[dict[str, Any]] = []

    for repeat, outer_fold in selected_splits:
        fold_manifest = manifest[
            (manifest["repeat"] == repeat)
            & (manifest["outer_fold"] == outer_fold)
        ]
        training_positions = fold_manifest.loc[
            fold_manifest["role"] == "train", "row_position"
        ].to_numpy(dtype=int)
        validation_manifest = fold_manifest[
            fold_manifest["role"] == "validation"
        ].copy()
        validation_positions = validation_manifest["row_position"].to_numpy(
            dtype=int
        )
        X_training = dataset.X.iloc[training_positions].reset_index(drop=True)
        y_training = dataset.y.iloc[training_positions].to_numpy(dtype=int)
        X_validation = dataset.X.iloc[validation_positions].reset_index(drop=True)
        y_validation = dataset.y.iloc[validation_positions].to_numpy(dtype=int)
        training_groups = (
            dataset.groups.iloc[training_positions].to_numpy()
            if dataset.groups is not None
            else None
        )
        split_seed = int(profile["seed"]) + repeat * 1_000 + outer_fold
        for model_name in models:
            for variant, add_indicators in VARIANTS.items():
                LOGGER.info(
                    "Missing-indicator ablation dataset=%s model=%s variant=%s repeat=%d fold=%d",
                    dataset_name,
                    model_name,
                    variant,
                    repeat,
                    outer_fold,
                )
                tuning_start = time.perf_counter()
                tuning = tune_model(
                    X_training,
                    y_training,
                    dataset_cfg,
                    model_name,
                    n_trials=int(profile["n_trials"]),
                    n_splits=inner_folds,
                    seed=split_seed,
                    groups=training_groups,
                    n_jobs=model_n_jobs,
                    add_numeric_missing_indicators=add_indicators,
                )
                tuning_seconds = time.perf_counter() - tuning_start
                tuning.trials.to_csv(
                    trial_dir
                    / f"{model_name}_{variant}_repeat_{repeat}_fold_{outer_fold}.csv",
                    index=False,
                )
                inner_probability = cross_fitted_probabilities(
                    X_training,
                    y_training,
                    dataset_cfg,
                    model_name,
                    tuning.best_params,
                    n_splits=inner_folds,
                    seed=split_seed,
                    groups=training_groups,
                    n_jobs=model_n_jobs,
                    add_numeric_missing_indicators=add_indicators,
                )
                calibration = select_calibrator(
                    [str(method) for method in profile["calibration_methods"]],
                    inner_probability,
                    y_training,
                    n_splits=inner_folds,
                    seed=split_seed + 10_000,
                    groups=training_groups,
                    minimum_samples_by_method={
                        str(method): int(minimum)
                        for method, minimum in profile.get(
                            "calibration_minimum_samples", {}
                        ).items()
                    },
                )
                preprocessor = build_preprocessor(
                    dataset_cfg,
                    model_name,
                    add_numeric_missing_indicators=add_indicators,
                )
                transformed_training = preprocessor.fit_transform(X_training)
                transformed_validation = preprocessor.transform(X_validation)
                model = build_estimator(
                    model_name,
                    tuning.best_params,
                    seed=split_seed + 20_000,
                    n_jobs=model_n_jobs,
                    positive_class_weight=positive_class_weight(y_training),
                )
                model.fit(transformed_training, y_training)
                probability_raw = model.predict_proba(transformed_validation)
                probability_calibrated = calibration.calibrator.predict(
                    probability_raw
                )
                prediction_frames.append(
                    pd.DataFrame(
                        {
                            "dataset": dataset_name,
                            "model": model_name,
                            "variant": variant,
                            "row_id": validation_manifest["row_id"].to_numpy(),
                            "group_id": validation_manifest["group_id"].to_numpy(),
                            "repeat": repeat,
                            "outer_fold": outer_fold,
                            "target": y_validation,
                            "probability_raw": probability_raw,
                            "probability_calibrated": probability_calibrated,
                            "calibration_method": calibration.method,
                        }
                    )
                )
                tuning_records.append(
                    {
                        "dataset": dataset_name,
                        "model": model_name,
                        "variant": variant,
                        "add_numeric_missing_indicators": add_indicators,
                        "repeat": repeat,
                        "outer_fold": outer_fold,
                        "n_trials": int(profile["n_trials"]),
                        "inner_folds": inner_folds,
                        "seed": split_seed,
                        "best_average_precision": tuning.best_score,
                        "best_params": json.dumps(
                            tuning.best_params, sort_keys=True
                        ),
                        "calibration_method": calibration.method,
                        "tuning_seconds": tuning_seconds,
                    }
                )
    predictions = pd.concat(prediction_frames, ignore_index=True)
    participant_predictions, contrasts = missing_indicator_contrasts(
        predictions,
        n_bootstrap=int(profile["n_bootstrap"]),
        seed=int(profile["seed"]) + 1_100_000,
    )
    evidence_tier = (
        "execution_only"
        if str(profile.get("name")) == "smoke"
        else "development_only"
    )
    metadata = {
        "schema_version": "1.0",
        "dataset": dataset_name,
        "source_study": str(study_dir),
        "profile": profile["name"],
        "evidence_tier": evidence_tier,
        "models": list(models),
        "variants": VARIANTS,
        "selected_outer_splits": selected_splits,
        "identical_outer_splits": True,
        "identical_inner_folds": True,
        "identical_tuning_budgets": True,
        "identical_search_spaces": True,
        "identical_seeds": True,
        "separate_tuning_per_variant": True,
        "source_tree_sha256": source_tree_sha256(),
        "ablation_study_complete": False,
        "final_outcome_access_authorized": False,
    }
    predictions_path = output_dir / "outer_predictions.csv"
    participant_path = output_dir / "participant_predictions.csv"
    contrasts_path = output_dir / "paired_contrasts.csv"
    tuning_path = output_dir / "tuning_summary.csv"
    metadata_path = output_dir / "metadata.json"
    report_path = output_dir / "Missing_Indicator_Ablation.md"
    predictions.to_csv(predictions_path, index=False)
    participant_predictions.to_csv(participant_path, index=False)
    contrasts.to_csv(contrasts_path, index=False)
    pd.DataFrame(tuning_records).to_csv(tuning_path, index=False)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    report_path.write_text(_render_report(metadata, contrasts), encoding="utf-8")
    return MissingIndicatorAblationResult(
        study_dir=study_dir,
        output_dir=output_dir,
        predictions_path=predictions_path,
        contrasts_path=contrasts_path,
        report_path=report_path,
    )
