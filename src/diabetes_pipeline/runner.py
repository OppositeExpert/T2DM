"""End-to-end benchmark runner for the first nested-CV vertical slice."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import pandas as pd

from diabetes_pipeline.calibration.calibrators import select_calibrator
from diabetes_pipeline.calibration.thresholds import select_thresholds
from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.data.manifests import write_audit
from diabetes_pipeline.evaluation.bootstrap import bootstrap_metric_intervals
from diabetes_pipeline.evaluation.comparisons import paired_model_comparisons
from diabetes_pipeline.evaluation.decision_curve import decision_curve
from diabetes_pipeline.evaluation.decision_curve_inference import (
    decision_curve_bootstrap_inference,
)
from diabetes_pipeline.evaluation.metrics import binary_metrics
from diabetes_pipeline.evaluation.plots import save_evaluation_plots
from diabetes_pipeline.evaluation.repeated_cv import (
    participant_level_repeated_cv_inference,
)
from diabetes_pipeline.models.registry import MODEL_NAMES, build_estimator
from diabetes_pipeline.preprocessing.builders import build_preprocessor, transformed_feature_names
from diabetes_pipeline.settings import (
    DEFAULT_OUTPUT_ROOT,
    PROJECT_ROOT,
    configuration_sha256,
    get_dataset_config,
    load_experiment_profile,
    source_tree_sha256,
)
from diabetes_pipeline.splitting.registry import create_and_write_split_manifest
from diabetes_pipeline.splitting.concealment import (
    assert_final_execution_authorized,
    final_analysis_configuration_sha256,
)
from diabetes_pipeline.training.tuning import (
    cross_fitted_probabilities,
    positive_class_weight,
    tune_model,
)


LOGGER = logging.getLogger(__name__)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _nested_evidence_tier(profile_name: str, profile: dict[str, Any]) -> str:
    if profile_name == "smoke":
        return "execution_only_smoke"
    if profile_name in {"development_pilot", "pilot"}:
        return "development_pilot"
    if profile_name == "development":
        return "full_development"
    if profile_name == "final" and bool(profile.get("locked", False)):
        return "final_locked"
    raise ValueError("Nested studies require an explicit supported evidence profile")


def _claim_final_nested_execution(
    dataset_name: str,
    analysis_configuration_sha256: str,
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> Path:
    """Persist a one-way receipt before any authorized final nested-CV work."""

    receipt_dir = output_root / "final_execution_receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = receipt_dir / (
        f"{dataset_name}_{analysis_configuration_sha256[:12]}.json"
    )
    payload = {
        "dataset": dataset_name,
        "analysis_configuration_sha256": analysis_configuration_sha256,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "warning": "Presence of this receipt prohibits automatic final re-execution.",
    }
    try:
        with receipt.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise RuntimeError(
            "Final nested-CV execution was already started for this frozen analysis; automatic re-run is prohibited"
        ) from exc
    return receipt


@dataclass(frozen=True)
class BenchmarkResult:
    experiment_id: str
    output_dir: Path
    predictions_path: Path
    metrics_path: Path
    summary_path: Path


def _experiment_id(
    dataset_cfg: dict[str, Any],
    profile: dict[str, Any],
    models: Sequence[str],
    *,
    raw_data_sha256: str,
    split_manifest_sha256: str,
) -> str:
    payload = {
        "dataset_configuration": configuration_sha256(dataset_cfg),
        "profile": profile,
        "models": list(models),
        "raw_data_sha256": raw_data_sha256,
        "split_manifest_sha256": split_manifest_sha256,
        "source_tree_sha256": source_tree_sha256(),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:12]
    return f"{dataset_cfg['name']}_{profile['name']}_{digest}"


def _selected_outer_splits(
    manifest: pd.DataFrame, profile: dict[str, Any]
) -> list[tuple[int, int]]:
    combinations = sorted(
        {
            (int(repeat), int(fold))
            for repeat, fold in manifest[["repeat", "outer_fold"]].itertuples(index=False)
            if int(fold) >= 0
        }
    )
    max_repeats = profile.get("max_repeats")
    max_outer_folds = profile.get("max_outer_folds")
    return [
        (repeat, fold)
        for repeat, fold in combinations
        if (max_repeats is None or repeat < int(max_repeats))
        and (max_outer_folds is None or fold < int(max_outer_folds))
    ]


def _markdown_summary(summary: pd.DataFrame) -> str:
    columns = [
        "model",
        "probability_version",
        "threshold_policy",
        "auroc",
        "average_precision",
        "brier_score",
        "log_loss",
        "sensitivity",
        "specificity",
        "f1",
    ]
    frame = summary[columns].copy()
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join(["---"] * len(columns)) + "|",
    ]
    for row in frame.itertuples(index=False):
        values = []
        for value in row:
            values.append(f"{value:.4f}" if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def run_nested_benchmark(
    dataset_name: str,
    *,
    profile_name: str = "smoke",
    models: Sequence[str] = MODEL_NAMES,
) -> BenchmarkResult:
    dataset_cfg = get_dataset_config(dataset_name)
    profile = load_experiment_profile(profile_name)
    unknown_models = sorted(set(models) - set(MODEL_NAMES))
    if unknown_models:
        raise ValueError(f"Unknown models: {unknown_models}")
    evidence_tier = _nested_evidence_tier(profile_name, profile)
    if not dataset_cfg["evaluation_strategy"].startswith("repeated_nested"):
        raise NotImplementedError(
            "The first vertical-slice runner currently supports repeated nested CV datasets only"
        )

    run_started_at_utc = datetime.now(timezone.utc).isoformat()
    raw_data_sha256 = _sha256_file(Path(dataset_cfg["raw_path"]))
    analysis_configuration_sha256 = final_analysis_configuration_sha256(
        dataset_name=dataset_name,
        dataset_config=dataset_cfg,
        profile=profile,
        models=models,
    )
    final_execution_receipt = None
    if profile_name == "final":
        assert_final_execution_authorized(
            profile_name=profile_name,
            profile=profile,
            dataset_name=dataset_name,
            raw_data_sha256=raw_data_sha256,
            analysis_configuration_sha256=analysis_configuration_sha256,
            requires_concealed_holdout=False,
        )
        final_execution_receipt = _claim_final_nested_execution(
            dataset_name,
            analysis_configuration_sha256,
        )

    dataset = load_dataset(dataset_name)
    audit_path, audit_markdown_path, audit = write_audit(dataset)
    if str(audit["raw_sha256"]) != raw_data_sha256:
        raise RuntimeError("Raw data changed between authorization and dataset audit")
    split_path, split_metadata_path, manifest = create_and_write_split_manifest(
        dataset, seed=int(profile["seed"])
    )
    selected_splits = _selected_outer_splits(manifest, profile)
    if not selected_splits:
        raise RuntimeError("Experiment profile selected no outer splits")

    split_manifest_sha256 = json.loads(
        split_metadata_path.read_text(encoding="utf-8")
    )["manifest_sha256"]
    experiment_id = _experiment_id(
        dataset_cfg,
        profile,
        models,
        raw_data_sha256=raw_data_sha256,
        split_manifest_sha256=str(split_manifest_sha256),
    )
    output_dir = DEFAULT_OUTPUT_ROOT / "studies" / experiment_id
    trial_dir = output_dir / "trials"
    model_dir = output_dir / "models"
    trial_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    prediction_records: list[pd.DataFrame] = []
    threshold_prediction_records: list[pd.DataFrame] = []
    metric_records: list[dict[str, Any]] = []
    best_parameter_records: list[dict[str, Any]] = []
    calibration_records: list[dict[str, Any]] = []
    threshold_records: list[dict[str, Any]] = []
    inner_folds = int(profile.get("inner_folds_override", dataset_cfg["inner_folds"]))
    model_n_jobs = int(profile.get("model_n_jobs", 1))

    for repeat, outer_fold in selected_splits:
        fold_manifest = manifest[
            (manifest["repeat"] == repeat) & (manifest["outer_fold"] == outer_fold)
        ]
        training_positions = fold_manifest.loc[
            fold_manifest["role"] == "train", "row_position"
        ].to_numpy(dtype=int)
        validation_positions = fold_manifest.loc[
            fold_manifest["role"] == "validation", "row_position"
        ].to_numpy(dtype=int)
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
            LOGGER.info(
                "Tuning %s dataset=%s repeat=%d fold=%d trials=%d",
                model_name,
                dataset_name,
                repeat,
                outer_fold,
                profile["n_trials"],
            )
            start = time.perf_counter()
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
            )
            tuning_seconds = time.perf_counter() - start
            tuning.trials.to_csv(
                trial_dir / f"{model_name}_repeat_{repeat}_fold_{outer_fold}.csv",
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
            )
            calibration_selection = select_calibrator(
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
            calibration_method = calibration_selection.method
            calibrator = calibration_selection.calibrator
            selected_thresholds = select_thresholds(
                [str(policy) for policy in profile["threshold_policies"]],
                y_training,
                calibration_selection.cross_fitted_probability,
                sensitivity_target=profile.get("sensitivity_target"),
            )
            for score in calibration_selection.scores:
                calibration_records.append(
                    {
                        "experiment_id": experiment_id,
                        "dataset": dataset_name,
                        "model": model_name,
                        "repeat": repeat,
                        "outer_fold": outer_fold,
                        **score,
                        "selected": str(score["method"]) == calibration_method,
                        "selection_primary_metric": "brier_score",
                        "selection_tiebreak_metric": "log_loss",
                        "selection_n": len(y_training),
                        "selection_folds": inner_folds,
                    }
                )
            for selected_threshold in selected_thresholds:
                development_operating_metrics = binary_metrics(
                    y_training,
                    calibration_selection.cross_fitted_probability,
                    threshold=float(selected_threshold["threshold"]),
                )
                threshold_records.append(
                    {
                        "experiment_id": experiment_id,
                        "dataset": dataset_name,
                        "model": model_name,
                        "repeat": repeat,
                        "outer_fold": outer_fold,
                        "calibration_method": calibration_method,
                        "selection_data": "inner_cross_fitted_predictions",
                        "selection_n": len(y_training),
                        "development_sensitivity": development_operating_metrics[
                            "sensitivity"
                        ],
                        "development_specificity": development_operating_metrics[
                            "specificity"
                        ],
                        "development_ppv": development_operating_metrics["ppv"],
                        "development_npv": development_operating_metrics["npv"],
                        "development_f1": development_operating_metrics["f1"],
                        "development_mcc": development_operating_metrics["mcc"],
                        "sensitivity_target": profile.get("sensitivity_target"),
                        **selected_threshold,
                    }
                )

            preprocessor = build_preprocessor(dataset_cfg, model_name)
            transformed_training = preprocessor.fit_transform(X_training)
            transformed_validation = preprocessor.transform(X_validation)
            model = build_estimator(
                model_name,
                tuning.best_params,
                seed=split_seed + 20_000,
                n_jobs=model_n_jobs,
                positive_class_weight=positive_class_weight(y_training),
            )
            fit_start = time.perf_counter()
            model.fit(transformed_training, y_training)
            fit_seconds = time.perf_counter() - fit_start
            probability_raw = model.predict_proba(transformed_validation)
            probability_calibrated = calibrator.predict(probability_raw)

            validation_manifest = fold_manifest[fold_manifest["role"] == "validation"].copy()
            prediction_frame = pd.DataFrame(
                {
                    "experiment_id": experiment_id,
                    "dataset": dataset_name,
                    "task": dataset_cfg["task"],
                    "model": model_name,
                    "row_id": validation_manifest["row_id"].to_numpy(),
                    "group_id": validation_manifest["group_id"].to_numpy(),
                    "repeat": repeat,
                    "outer_fold": outer_fold,
                    "evaluation_role": "outer_validation",
                    "target": y_validation,
                    "probability_raw": probability_raw,
                    "probability_calibrated": probability_calibrated,
                    "calibration_method": calibration_method,
                }
            )
            prediction_records.append(prediction_frame)

            base_metric_record = {
                "experiment_id": experiment_id,
                "dataset": dataset_name,
                "task": dataset_cfg["task"],
                "endpoint": dataset_cfg["endpoint"],
                "model": model_name,
                "repeat": repeat,
                "outer_fold": outer_fold,
                "evaluation_role": "outer_validation",
                "calibration_method": calibration_method,
                "tuning_average_precision": tuning.best_score,
                "tuning_seconds": tuning_seconds,
                "fit_seconds": fit_seconds,
                "evidence_tier": evidence_tier,
            }
            raw_row = {
                **base_metric_record,
                "probability_version": "raw",
                "threshold_policy": "fixed_0_5",
            }
            raw_row.update(binary_metrics(y_validation, probability_raw, threshold=0.5))
            metric_records.append(raw_row)

            for threshold_choice in selected_thresholds:
                threshold_policy = str(threshold_choice["threshold_policy"])
                threshold = float(threshold_choice["threshold"])
                row = {
                    **base_metric_record,
                    "probability_version": "calibrated",
                    "threshold_policy": threshold_policy,
                }
                row.update(
                    binary_metrics(
                        y_validation,
                        probability_calibrated,
                        threshold=threshold,
                    )
                )
                metric_records.append(row)
                threshold_prediction_records.append(
                    prediction_frame.assign(
                        threshold_policy=threshold_policy,
                        threshold=threshold,
                        prediction=(probability_calibrated >= threshold).astype(int),
                    )
                )

            bundle = {
                "experiment_id": experiment_id,
                "dataset": dataset_name,
                "task": dataset_cfg["task"],
                "endpoint": dataset_cfg["endpoint"],
                "model_name": model_name,
                "repeat": repeat,
                "outer_fold": outer_fold,
                "dataset_configuration_sha256": configuration_sha256(dataset_cfg),
                "source_tree_sha256": source_tree_sha256(),
                "evidence_tier": evidence_tier,
                "raw_data_sha256": raw_data_sha256,
                "split_manifest_sha256": split_manifest_sha256,
                "analysis_configuration_sha256": analysis_configuration_sha256,
                "best_params": tuning.best_params,
                "preprocessor": preprocessor,
                "transformed_feature_names": transformed_feature_names(preprocessor),
                "model": model,
                "calibrator": calibrator,
                "calibration_method": calibration_method,
                "thresholds": {
                    str(choice["threshold_policy"]): float(choice["threshold"])
                    for choice in selected_thresholds
                },
                "threshold_policy": str(selected_thresholds[0]["threshold_policy"]),
                "threshold": float(selected_thresholds[0]["threshold"]),
            }
            bundle_path = model_dir / f"{model_name}_repeat_{repeat}_fold_{outer_fold}.joblib"
            joblib.dump(bundle, bundle_path)
            best_parameter_records.append(
                {
                    "model": model_name,
                    "repeat": repeat,
                    "outer_fold": outer_fold,
                    "best_score": tuning.best_score,
                    "best_params": json.dumps(tuning.best_params, sort_keys=True),
                    "bundle_path": str(bundle_path),
                }
            )

    predictions = pd.concat(prediction_records, ignore_index=True)
    threshold_predictions = pd.concat(threshold_prediction_records, ignore_index=True)
    metrics = pd.DataFrame(metric_records)
    calibration_selections = pd.DataFrame(calibration_records)
    thresholds = pd.DataFrame(threshold_records)
    scientific_columns = [
        "n",
        "positives",
        "prevalence",
        "threshold",
        "auroc",
        "average_precision",
        "brier_score",
        "scaled_brier_score",
        "log_loss",
        "calibration_intercept",
        "calibration_slope",
        "observed_expected_ratio",
        "expected_calibration_error",
        "accuracy",
        "balanced_accuracy",
        "sensitivity",
        "specificity",
        "false_positive_rate",
        "false_negative_rate",
        "ppv",
        "npv",
        "f1",
        "mcc",
        "youden_index",
        "positive_likelihood_ratio",
        "negative_likelihood_ratio",
        "diagnostic_odds_ratio",
        "tn",
        "fp",
        "fn",
        "tp",
    ]
    summary_groups = ["model", "probability_version", "threshold_policy"]
    summary = (
        metrics.groupby(summary_groups, as_index=False)[scientific_columns]
        .mean(numeric_only=True)
        .sort_values(
            ["probability_version", "threshold_policy", "average_precision"],
            ascending=[True, True, False],
        )
    )
    evaluation_counts = (
        metrics.groupby(summary_groups)
        .size()
        .rename("outer_evaluations")
        .reset_index()
    )
    summary = summary.merge(evaluation_counts, on=summary_groups, how="left")

    interval_records: list[dict[str, Any]] = []
    interval_seed_offset = 0
    for repeat in sorted(predictions["repeat"].unique()):
        for model_name in sorted(predictions["model"].unique()):
            model_predictions = predictions[
                (predictions["repeat"] == repeat)
                & (predictions["model"] == model_name)
            ]
            evaluations: list[
                tuple[str, str, np.ndarray, np.ndarray, float | np.ndarray]
            ] = [
                (
                    "raw",
                    "fixed_0_5",
                    model_predictions["target"].to_numpy(dtype=int),
                    model_predictions["probability_raw"].to_numpy(dtype=float),
                    0.5,
                )
            ]
            for threshold_policy in profile["threshold_policies"]:
                policy_predictions = threshold_predictions[
                    (threshold_predictions["repeat"] == repeat)
                    & (threshold_predictions["model"] == model_name)
                    & (threshold_predictions["threshold_policy"] == threshold_policy)
                ]
                evaluations.append(
                    (
                        "calibrated",
                        str(threshold_policy),
                        policy_predictions["target"].to_numpy(dtype=int),
                        policy_predictions["probability_calibrated"].to_numpy(dtype=float),
                        policy_predictions["threshold"].to_numpy(dtype=float),
                    )
                )
            for (
                probability_version,
                threshold_policy,
                outcome,
                probability,
                threshold,
            ) in evaluations:
                interval_seed_offset += 1
                rows = bootstrap_metric_intervals(
                    outcome,
                    probability,
                    threshold=threshold,
                    n_bootstrap=int(profile["n_bootstrap"]),
                    seed=int(profile["seed"]) + 100_000 + interval_seed_offset,
                )
                for row in rows:
                    interval_records.append(
                        {
                            "experiment_id": experiment_id,
                            "dataset": dataset_name,
                            "model": model_name,
                            "repeat": int(repeat),
                            "probability_version": probability_version,
                            "threshold_policy": threshold_policy,
                            "estimation_scope": "pooled_outer_predictions_within_repeat",
                            **row,
                        }
                    )
    confidence_intervals = pd.DataFrame(interval_records)

    decision_curve_records: list[pd.DataFrame] = []
    for (repeat, model_name), frame in predictions.groupby(["repeat", "model"], sort=True):
        curve = decision_curve(
            frame["target"].to_numpy(dtype=int),
            frame["probability_calibrated"].to_numpy(dtype=float),
        )
        curve.insert(0, "model", model_name)
        curve.insert(0, "repeat", int(repeat))
        curve.insert(0, "dataset", dataset_name)
        curve.insert(0, "experiment_id", experiment_id)
        decision_curve_records.append(curve)
    decision_curves = pd.concat(decision_curve_records, ignore_index=True)
    plotted_decision_curves = (
        decision_curves.groupby(["model", "threshold"], as_index=False)[
            [
                "model_net_benefit",
                "treat_all_net_benefit",
                "treat_none_net_benefit",
            ]
        ]
        .mean(numeric_only=True)
    )

    comparison_metrics = metrics[
        (metrics["probability_version"] == "calibrated")
        & (metrics["threshold_policy"] == "fixed_0_5")
    ]
    paired_comparisons = paired_model_comparisons(comparison_metrics)
    (
        participant_predictions,
        participant_confidence_intervals,
        participant_paired_comparisons,
    ) = participant_level_repeated_cv_inference(
        predictions,
        n_bootstrap=int(profile["n_bootstrap"]),
        seed=int(profile["seed"]) + 700_000,
    )
    participant_reference_model = sorted(participant_predictions["model"].unique())[0]
    participant_reference = (
        participant_predictions[
            participant_predictions["model"] == participant_reference_model
        ]
        .sort_values("row_id")
        .reset_index(drop=True)
    )
    participant_group_values = participant_reference["group_id"].to_numpy(dtype=str)
    participant_groups = (
        participant_group_values
        if np.any(np.char.str_len(participant_group_values) > 0)
        else None
    )
    (
        decision_curve_confidence_intervals,
        decision_curve_paired_contrasts,
    ) = decision_curve_bootstrap_inference(
        participant_predictions[
            ["model", "row_id", "target", "probability_calibrated"]
        ],
        n_bootstrap=int(profile["n_bootstrap"]),
        seed=int(profile["seed"]) + 800_000,
        groups=participant_groups,
    )
    decision_curve_confidence_intervals.insert(
        0, "estimation_scope", "participant_mean_across_repeats"
    )
    if not decision_curve_paired_contrasts.empty:
        decision_curve_paired_contrasts.insert(
            0, "estimation_scope", "participant_mean_across_repeats"
        )

    predictions_path = output_dir / "predictions.csv"
    metrics_path = output_dir / "fold_metrics.csv"
    summary_path = output_dir / "summary_metrics.csv"
    predictions.to_csv(predictions_path, index=False)
    threshold_predictions.to_csv(output_dir / "threshold_predictions.csv", index=False)
    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    (output_dir / "summary_metrics.md").write_text(_markdown_summary(summary), encoding="utf-8")
    pd.DataFrame(best_parameter_records).to_csv(output_dir / "best_parameters.csv", index=False)
    calibration_selections.to_csv(output_dir / "calibration_selection.csv", index=False)
    thresholds.to_csv(output_dir / "selected_thresholds.csv", index=False)
    confidence_intervals.to_csv(output_dir / "confidence_intervals.csv", index=False)
    decision_curves.to_csv(output_dir / "decision_curves.csv", index=False)
    paired_comparisons.to_csv(output_dir / "paired_model_comparisons.csv", index=False)
    participant_predictions.to_csv(
        output_dir / "participant_predictions.csv", index=False
    )
    participant_confidence_intervals.to_csv(
        output_dir / "participant_confidence_intervals.csv", index=False
    )
    participant_paired_comparisons.to_csv(
        output_dir / "participant_paired_model_comparisons.csv", index=False
    )
    decision_curve_confidence_intervals.to_csv(
        output_dir / "decision_curve_confidence_intervals.csv", index=False
    )
    decision_curve_paired_contrasts.to_csv(
        output_dir / "decision_curve_paired_contrasts.csv", index=False
    )

    paper_table_dir = output_dir / "paper_tables"
    paper_table_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(paper_table_dir / "primary_performance.csv", index=False)
    confidence_intervals.to_csv(
        paper_table_dir / "performance_confidence_intervals.csv", index=False
    )
    (
        calibration_selections[calibration_selections["selected"]]
        .groupby(["model", "method"], as_index=False)
        .size()
        .rename(columns={"size": "selection_count"})
        .to_csv(paper_table_dir / "calibration_method_counts.csv", index=False)
    )
    paired_comparisons.to_csv(paper_table_dir / "paired_model_comparisons.csv", index=False)
    participant_confidence_intervals.to_csv(
        paper_table_dir / "participant_confidence_intervals.csv", index=False
    )
    participant_paired_comparisons.to_csv(
        paper_table_dir / "participant_paired_model_comparisons.csv", index=False
    )
    decision_curve_confidence_intervals.to_csv(
        paper_table_dir / "decision_curve_confidence_intervals.csv", index=False
    )
    decision_curve_paired_contrasts.to_csv(
        paper_table_dir / "decision_curve_paired_contrasts.csv", index=False
    )
    save_evaluation_plots(
        predictions,
        plotted_decision_curves,
        output_dir / "figures",
    )
    (output_dir / "experiment_metadata.json").write_text(
        json.dumps(
            {
                "experiment_id": experiment_id,
                "dataset": dataset_name,
                "dataset_configuration_sha256": configuration_sha256(dataset_cfg),
                "source_tree_sha256": source_tree_sha256(),
                "raw_data_sha256": audit["raw_sha256"],
                "analysis_configuration_sha256": analysis_configuration_sha256,
                "requirements_lock_sha256": (
                    _sha256_file(PROJECT_ROOT / "requirements.lock")
                    if (PROJECT_ROOT / "requirements.lock").exists()
                    else None
                ),
                "run_started_at_utc": run_started_at_utc,
                "run_completed_at_utc": datetime.now(timezone.utc).isoformat(),
                "reproduction_command": (
                    "python -m diabetes_pipeline.cli benchmark "
                    f"--dataset {dataset_name} --profile {profile_name} --models "
                    + " ".join(models)
                ),
                "audit_json": str(audit_path),
                "audit_markdown": str(audit_markdown_path),
                "split_manifest": str(split_path),
                "split_manifest_metadata": str(split_metadata_path),
                "split_manifest_sha256": split_manifest_sha256,
                "profile": profile,
                "evidence_tier": evidence_tier,
                "final_execution_receipt": (
                    str(final_execution_receipt.relative_to(PROJECT_ROOT))
                    if final_execution_receipt is not None
                    else None
                ),
                "models": list(models),
                "outer_splits": selected_splits,
                "inner_folds": inner_folds,
                "model_n_jobs": model_n_jobs,
                "primary_repeated_cv_inference": "participant_mean_across_repeats",
                "decision_curve_inference": {
                    "estimation_scope": "participant_mean_across_repeats",
                    "paired_bootstrap": True,
                    "resampling_unit": (
                        "cluster" if participant_groups is not None else "individual"
                    ),
                },
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    return BenchmarkResult(
        experiment_id=experiment_id,
        output_dir=output_dir,
        predictions_path=predictions_path,
        metrics_path=metrics_path,
        summary_path=summary_path,
    )
