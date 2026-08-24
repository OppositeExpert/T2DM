"""Panel-specific training versus full-panel masked inference ablations."""

from __future__ import annotations

import hashlib
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
from diabetes_pipeline.evaluation.comparisons import paired_bootstrap_model_comparisons
from diabetes_pipeline.models.registry import MODEL_NAMES, build_estimator
from diabetes_pipeline.preprocessing.builders import build_preprocessor
from diabetes_pipeline.routing.evaluator import _read_routing_config
from diabetes_pipeline.runner import _selected_outer_splits
from diabetes_pipeline.settings import get_dataset_config, source_tree_sha256
from diabetes_pipeline.training.tuning import (
    cross_fitted_probabilities,
    positive_class_weight,
    tune_model,
)


LOGGER = logging.getLogger(__name__)
MASKED_STRATEGY = "full_panel_masked"
PANEL_STRATEGY = "panel_specific_trained"
CHECKPOINT_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class PanelTrainingAblationResult:
    study_dir: Path
    output_dir: Path
    predictions_path: Path
    contrasts_path: Path
    report_path: Path


def _checkpoint_signature(payload: dict[str, Any]) -> str:
    """Return a stable signature for one resumable training task."""

    serialized = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _write_task_checkpoint(
    checkpoint_dir: Path,
    *,
    signature_payload: dict[str, Any],
    predictions: pd.DataFrame,
    tuning_record: dict[str, Any],
) -> None:
    """Atomically persist a completed task so interrupted runs can resume."""

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    prediction_path = checkpoint_dir / "predictions.csv"
    metadata_path = checkpoint_dir / "metadata.json"
    prediction_tmp = checkpoint_dir / "predictions.csv.tmp"
    metadata_tmp = checkpoint_dir / "metadata.json.tmp"
    predictions.to_csv(prediction_tmp, index=False)
    metadata_tmp.write_text(
        json.dumps(
            {
                "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
                "signature": _checkpoint_signature(signature_payload),
                "signature_payload": signature_payload,
                "prediction_rows": int(len(predictions)),
                "tuning_record": tuning_record,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    prediction_tmp.replace(prediction_path)
    metadata_tmp.replace(metadata_path)


def _load_task_checkpoint(
    checkpoint_dir: Path,
    *,
    signature_payload: dict[str, Any],
    expected_rows: int,
) -> tuple[pd.DataFrame, dict[str, Any]] | None:
    """Load a complete compatible task checkpoint, otherwise recompute it."""

    prediction_path = checkpoint_dir / "predictions.csv"
    metadata_path = checkpoint_dir / "metadata.json"
    if not prediction_path.exists() or not metadata_path.exists():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("checkpoint_schema_version") != CHECKPOINT_SCHEMA_VERSION:
            return None
        if metadata.get("signature") != _checkpoint_signature(signature_payload):
            return None
        predictions = pd.read_csv(prediction_path, low_memory=False)
        if len(predictions) != int(expected_rows):
            return None
        if int(metadata.get("prediction_rows", -1)) != len(predictions):
            return None
        tuning_record = dict(metadata["tuning_record"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None
    return predictions, tuning_record


def _panel_dataset_config(
    dataset_cfg: dict[str, Any], available_features: Sequence[str]
) -> dict[str, Any]:
    available = set(available_features)
    configured = set(
        dataset_cfg["numeric_features"] + dataset_cfg["categorical_features"]
    )
    unknown = sorted(available - configured)
    if unknown:
        raise ValueError(f"Panel contains unknown configured features: {unknown}")
    if not available:
        raise ValueError("A panel-specific model requires at least one feature")
    panel_cfg = dict(dataset_cfg)
    panel_cfg["numeric_features"] = [
        feature for feature in dataset_cfg["numeric_features"] if feature in available
    ]
    panel_cfg["categorical_features"] = [
        feature
        for feature in dataset_cfg["categorical_features"]
        if feature in available
    ]
    return panel_cfg


def aggregate_panel_strategy_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    """Average repeated predictions to one row per strategy and participant."""

    required = {
        "dataset",
        "model",
        "scenario",
        "training_strategy",
        "row_id",
        "group_id",
        "repeat",
        "target",
        "probability_raw",
        "probability_calibrated",
    }
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Panel-training predictions lack columns: {missing}")
    frame = predictions.copy()
    frame["row_id"] = frame["row_id"].astype(str)
    frame["group_id"] = frame["group_id"].fillna("").astype(str)
    keys = ["model", "scenario", "training_strategy", "row_id", "repeat"]
    if frame.duplicated(keys).any():
        raise ValueError("Panel-training predictions are duplicated within a repeat")
    expected_repeats = int(frame["repeat"].nunique())
    stability = frame.groupby(keys[:-1], sort=False).agg(
        outcomes=("target", "nunique"),
        groups=("group_id", "nunique"),
        repeats=("repeat", "nunique"),
    )
    if stability["outcomes"].ne(1).any():
        raise ValueError("Participant outcome changed across strategy predictions")
    if stability["groups"].ne(1).any():
        raise ValueError("Participant group changed across strategy predictions")
    if stability["repeats"].ne(expected_repeats).any():
        raise ValueError("Participant is missing from one or more repeats")
    return (
        frame.groupby(keys[:-1], as_index=False, sort=True)
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


def _holm_adjust(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["holm_adjusted_p_value"] = np.nan
    for metric in result["metric"].unique():
        ordered = (
            result.loc[result["metric"] == metric, "paired_bootstrap_p_value"]
            .dropna()
            .sort_values()
        )
        running_maximum = 0.0
        for rank, (index, p_value) in enumerate(ordered.items()):
            adjusted = min(1.0, float(p_value) * (len(ordered) - rank))
            running_maximum = max(running_maximum, adjusted)
            result.loc[index, "holm_adjusted_p_value"] = running_maximum
    return result


def panel_training_contrasts(
    predictions: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare panel-specific training with masked full-panel inference."""

    aggregated = aggregate_panel_strategy_predictions(predictions)
    if set(aggregated["training_strategy"].unique()) != {
        MASKED_STRATEGY,
        PANEL_STRATEGY,
    }:
        raise ValueError("Both panel-training strategies are required")
    records: list[dict[str, Any]] = []
    grouped = aggregated.groupby(["model", "scenario"], sort=True)
    for comparison_index, ((model, scenario), frame) in enumerate(grouped):
        strategy_counts = frame.groupby("training_strategy")["row_id"].nunique()
        if len(strategy_counts) != 2 or strategy_counts.nunique() != 1:
            raise ValueError(
                f"Strategies are not participant-matched for {model}/{scenario}"
            )
        reference = (
            frame[frame["training_strategy"] == PANEL_STRATEGY]
            .sort_values("row_id")
            .reset_index(drop=True)
        )
        group_values = reference["group_id"].to_numpy(dtype=str)
        groups = group_values if np.any(np.char.str_len(group_values) > 0) else None
        comparison_input = frame[
            ["training_strategy", "row_id", "target", "probability_calibrated"]
        ].rename(columns={"training_strategy": "model"})
        comparison = paired_bootstrap_model_comparisons(
            comparison_input,
            n_bootstrap=int(n_bootstrap),
            seed=int(seed) + comparison_index,
            groups=groups,
        )
        for row in comparison.itertuples(index=False):
            # Alphabetical labels give full_panel_masked - panel_specific_trained.
            masked_minus_panel = float(row.observed_difference_a_minus_b)
            raw_lower = float(row.ci_lower_a_minus_b)
            raw_upper = float(row.ci_upper_a_minus_b)
            if row.direction == "higher":
                improvement = -masked_minus_panel
                lower = -raw_upper
                upper = -raw_lower
            else:
                improvement = masked_minus_panel
                lower = raw_lower
                upper = raw_upper
            records.append(
                {
                    "model": str(model),
                    "scenario": str(scenario),
                    "metric": str(row.metric),
                    "direction": str(row.direction),
                    "observed_improvement_panel_training_over_masked": improvement,
                    "ci_lower_improvement": lower,
                    "ci_upper_improvement": upper,
                    "positive_improvement_is_better": True,
                    "paired_bootstrap_p_value": float(row.paired_bootstrap_p_value),
                    "n_bootstrap": int(row.n_bootstrap),
                    "resampling_unit": str(row.resampling_unit),
                    "estimation_scope": "participant_mean_across_repeats",
                }
            )
    return aggregated, _holm_adjust(pd.DataFrame(records))


def _render_report(metadata: dict[str, Any], contrasts: pd.DataFrame) -> str:
    brier = contrasts[contrasts["metric"] == "brier_score"]
    lines = [
        "# Panel-Specific Training Ablation",
        "",
        f"**Dataset:** `{metadata['dataset']}`",
        "",
        f"**Profile:** `{metadata['profile']}`",
        "",
        f"**Evidence tier:** `{metadata['evidence_tier']}`",
        "",
        "Panel-specific models are tuned, calibrated, and fitted using only the "
        "panel features. Their held-out predictions are compared with the existing "
        "full-panel models evaluated on the same participants after unavailable "
        "features were masked.",
        "",
        "| Model | Panel | Brier improvement from panel training (95% CI) | Holm p |",
        "|---|---|---:|---:|",
    ]
    for _, row in brier.sort_values(["model", "scenario"]).iterrows():
        lines.append(
            f"| {row['model']} | {row['scenario']} | "
            f"{row['observed_improvement_panel_training_over_masked']:.4f} "
            f"({row['ci_lower_improvement']:.4f}, "
            f"{row['ci_upper_improvement']:.4f}) | "
            f"{row['holm_adjusted_p_value']:.4f} |"
        )
    lines.extend(
        [
            "",
            "Positive improvement favors panel-specific training. Smoke and pilot "
            "profiles remain development evidence and cannot enter final tables.",
            "",
        ]
    )
    return "\n".join(lines)


def run_panel_training_ablation(
    study_dir: Path | str,
    *,
    models: Sequence[str] = ("random_forest", "xgboost"),
    scenarios: Sequence[str] | None = None,
) -> PanelTrainingAblationResult:
    """Retrain per-panel models under an existing nested-CV split contract."""

    study_dir = Path(study_dir).resolve()
    metadata = json.loads(
        (study_dir / "experiment_metadata.json").read_text(encoding="utf-8")
    )
    profile = dict(metadata["profile"])
    if str(profile.get("name")) == "final" or bool(profile.get("locked", False)):
        raise PermissionError("Panel-training ablations are development-only")
    if str(metadata.get("runner", "nested_cv")) != "nested_cv":
        raise NotImplementedError(
            "Panel-training retraining currently supports nested-CV studies"
        )
    dataset_name = str(metadata["dataset"])
    dataset_cfg = get_dataset_config(dataset_name)
    unknown_models = sorted(set(models) - set(MODEL_NAMES))
    if unknown_models:
        raise ValueError(f"Unknown models: {unknown_models}")
    routing_cfg = _read_routing_config(dataset_name)
    scenario_definitions = dict(routing_cfg["scenarios"])
    scenario_features = {
        name: list(definition["available_features"])
        for name, definition in scenario_definitions.items()
    }
    selected_scenarios = (
        list(scenarios)
        if scenarios is not None
        else sorted(set(scenario_features) - {"full"})
    )
    unknown_scenarios = sorted(set(selected_scenarios) - set(scenario_features))
    if unknown_scenarios:
        raise ValueError(f"Unknown availability scenarios: {unknown_scenarios}")
    if not selected_scenarios:
        raise ValueError("At least one reduced availability scenario is required")

    masked_path = study_dir / "availability_routing" / "stress_predictions.csv"
    if not masked_path.exists():
        raise FileNotFoundError(
            f"Run availability routing before this ablation: {masked_path}"
        )
    masked_source = pd.read_csv(masked_path, low_memory=False)
    missing_models = sorted(set(models) - set(masked_source["model"].unique()))
    if missing_models:
        raise ValueError(
            f"Masked routing predictions do not contain models: {missing_models}"
        )
    dataset = load_dataset(dataset_name)
    manifest = pd.read_csv(metadata["split_manifest"], low_memory=False)
    selected_outer_splits = _selected_outer_splits(manifest, profile)
    if not selected_outer_splits:
        raise ValueError("The source study contains no selected outer splits")
    inner_folds = int(profile.get("inner_folds_override", dataset_cfg["inner_folds"]))
    model_n_jobs = int(profile.get("model_n_jobs", 1))
    output_dir = study_dir / "ablations" / "panel_specific_training"
    trial_dir = output_dir / "trials"
    checkpoint_root = output_dir / "checkpoints"
    output_dir.mkdir(parents=True, exist_ok=True)
    trial_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    prediction_frames: list[pd.DataFrame] = []
    tuning_records: list[dict[str, Any]] = []
    resumed_task_count = 0
    computed_task_count = 0
    analysis_source_sha256 = source_tree_sha256()

    for repeat, outer_fold in selected_outer_splits:
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
        validation_positions = validation_manifest["row_position"].to_numpy(dtype=int)
        y_training = dataset.y.iloc[training_positions].to_numpy(dtype=int)
        y_validation = dataset.y.iloc[validation_positions].to_numpy(dtype=int)
        training_groups = (
            dataset.groups.iloc[training_positions].to_numpy()
            if dataset.groups is not None
            else None
        )
        split_seed = int(profile["seed"]) + repeat * 1_000 + outer_fold
        for model_name in models:
            for scenario_name in selected_scenarios:
                features = scenario_features[scenario_name]
                panel_cfg = _panel_dataset_config(dataset_cfg, features)
                X_training = dataset.X.iloc[training_positions][features].reset_index(
                    drop=True
                )
                X_validation = dataset.X.iloc[validation_positions][features].reset_index(
                    drop=True
                )
                LOGGER.info(
                    "Panel-training ablation dataset=%s model=%s panel=%s repeat=%d fold=%d",
                    dataset_name,
                    model_name,
                    scenario_name,
                    repeat,
                    outer_fold,
                )
                signature_payload = {
                    "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
                    "source_tree_sha256": analysis_source_sha256,
                    "source_experiment_id": metadata.get("experiment_id"),
                    "source_split_manifest_sha256": metadata.get(
                        "split_manifest_sha256"
                    ),
                    "dataset_configuration_sha256": metadata.get(
                        "dataset_configuration_sha256"
                    ),
                    "dataset": dataset_name,
                    "profile": profile,
                    "model": model_name,
                    "scenario": scenario_name,
                    "features": features,
                    "repeat": int(repeat),
                    "outer_fold": int(outer_fold),
                    "inner_folds": inner_folds,
                    "seed": split_seed,
                }
                checkpoint_dir = (
                    checkpoint_root
                    / model_name
                    / scenario_name
                    / f"repeat_{repeat}_fold_{outer_fold}"
                )
                checkpoint = _load_task_checkpoint(
                    checkpoint_dir,
                    signature_payload=signature_payload,
                    expected_rows=len(validation_manifest),
                )
                if checkpoint is not None:
                    cached_predictions, cached_tuning = checkpoint
                    prediction_frames.append(cached_predictions)
                    tuning_records.append(cached_tuning)
                    resumed_task_count += 1
                    LOGGER.info(
                        "Resumed panel-training checkpoint model=%s panel=%s repeat=%d fold=%d",
                        model_name,
                        scenario_name,
                        repeat,
                        outer_fold,
                    )
                    continue
                started = time.perf_counter()
                tuning = tune_model(
                    X_training,
                    y_training,
                    panel_cfg,
                    model_name,
                    n_trials=int(profile["n_trials"]),
                    n_splits=inner_folds,
                    seed=split_seed,
                    groups=training_groups,
                    n_jobs=model_n_jobs,
                )
                tuning_seconds = time.perf_counter() - started
                tuning.trials.to_csv(
                    trial_dir
                    / f"{model_name}_{scenario_name}_repeat_{repeat}_fold_{outer_fold}.csv",
                    index=False,
                )
                inner_probability = cross_fitted_probabilities(
                    X_training,
                    y_training,
                    panel_cfg,
                    model_name,
                    tuning.best_params,
                    n_splits=inner_folds,
                    seed=split_seed,
                    groups=training_groups,
                    n_jobs=model_n_jobs,
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
                preprocessor = build_preprocessor(panel_cfg, model_name)
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
                probability_calibrated = calibration.calibrator.predict(probability_raw)
                task_predictions = pd.DataFrame(
                    {
                        "dataset": dataset_name,
                        "model": model_name,
                        "scenario": scenario_name,
                        "available_feature_count": len(features),
                        "training_strategy": PANEL_STRATEGY,
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
                tuning_record = {
                    "dataset": dataset_name,
                    "model": model_name,
                    "scenario": scenario_name,
                    "available_feature_count": len(features),
                    "repeat": repeat,
                    "outer_fold": outer_fold,
                    "n_trials": int(profile["n_trials"]),
                    "inner_folds": inner_folds,
                    "seed": split_seed,
                    "best_average_precision": tuning.best_score,
                    "best_params": json.dumps(tuning.best_params, sort_keys=True),
                    "calibration_method": calibration.method,
                    "tuning_seconds": tuning_seconds,
                }
                _write_task_checkpoint(
                    checkpoint_dir,
                    signature_payload=signature_payload,
                    predictions=task_predictions,
                    tuning_record=tuning_record,
                )
                prediction_frames.append(task_predictions)
                tuning_records.append(tuning_record)
                computed_task_count += 1

    panel_predictions = pd.concat(prediction_frames, ignore_index=True)
    masked_predictions = masked_source[
        masked_source["model"].isin(models)
        & masked_source["scenario"].isin(selected_scenarios)
    ].copy()
    masked_predictions["training_strategy"] = MASKED_STRATEGY
    aligned_columns = list(panel_predictions.columns)
    masked_predictions = masked_predictions[aligned_columns]
    predictions = pd.concat([masked_predictions, panel_predictions], ignore_index=True)
    participant_predictions, contrasts = panel_training_contrasts(
        predictions,
        n_bootstrap=int(profile["n_bootstrap"]),
        seed=int(profile["seed"]) + 1_200_000,
    )
    evidence_tier = (
        "execution_only"
        if str(profile.get("name")) == "smoke"
        else "development_only"
    )
    ablation_metadata = {
        "schema_version": "1.0",
        "dataset": dataset_name,
        "source_study": str(study_dir),
        "profile": profile["name"],
        "evidence_tier": evidence_tier,
        "models": list(models),
        "scenarios": selected_scenarios,
        "strategies": [MASKED_STRATEGY, PANEL_STRATEGY],
        "masked_prediction_source": str(masked_path),
        "selected_outer_splits": selected_outer_splits,
        "identical_outer_splits": True,
        "identical_inner_split_contract": True,
        "identical_tuning_budgets": True,
        "identical_model_families": True,
        "separate_tuning_panel_specific": True,
        "participant_paired_inference": True,
        "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION,
        "resumed_task_count": resumed_task_count,
        "computed_task_count": computed_task_count,
        "completed_task_count": resumed_task_count + computed_task_count,
        "source_tree_sha256": analysis_source_sha256,
        "ablation_study_complete": False,
        "final_outcome_access_authorized": False,
    }
    predictions_path = output_dir / "outer_predictions.csv"
    participant_path = output_dir / "participant_predictions.csv"
    contrasts_path = output_dir / "paired_contrasts.csv"
    tuning_path = output_dir / "tuning_summary.csv"
    metadata_path = output_dir / "metadata.json"
    report_path = output_dir / "Panel_Specific_Training_Ablation.md"
    predictions.to_csv(predictions_path, index=False)
    participant_predictions.to_csv(participant_path, index=False)
    contrasts.to_csv(contrasts_path, index=False)
    pd.DataFrame(tuning_records).to_csv(tuning_path, index=False)
    metadata_path.write_text(
        json.dumps(ablation_metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    report_path.write_text(
        _render_report(ablation_metadata, contrasts), encoding="utf-8"
    )
    return PanelTrainingAblationResult(
        study_dir=study_dir,
        output_dir=output_dir,
        predictions_path=predictions_path,
        contrasts_path=contrasts_path,
        report_path=report_path,
    )
