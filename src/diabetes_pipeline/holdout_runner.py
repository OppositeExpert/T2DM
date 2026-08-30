"""Development-locked evaluation for large and patient-grouped holdout cohorts."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from diabetes_pipeline.calibration.calibrators import select_calibrator
from diabetes_pipeline.calibration.thresholds import select_thresholds
from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.data.manifests import write_audit
from diabetes_pipeline.evaluation.bootstrap import bootstrap_metric_intervals
from diabetes_pipeline.evaluation.comparisons import (
    paired_bootstrap_model_comparisons,
)
from diabetes_pipeline.evaluation.decision_curve import decision_curve
from diabetes_pipeline.evaluation.decision_curve_inference import (
    decision_curve_bootstrap_inference,
)
from diabetes_pipeline.evaluation.metrics import binary_metrics
from diabetes_pipeline.evaluation.plots import save_evaluation_plots
from diabetes_pipeline.models.registry import MODEL_NAMES, build_estimator
from diabetes_pipeline.preprocessing.builders import (
    build_preprocessor,
    transformed_feature_names,
)
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
    load_authorized_concealed_manifest,
)
from diabetes_pipeline.training.tuning import (
    cross_fitted_probabilities,
    positive_class_weight,
    tune_model,
)


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HoldoutResult:
    experiment_id: str
    output_dir: Path
    predictions_path: Path
    metrics_path: Path
    summary_path: Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _experiment_id(
    dataset_cfg: dict[str, Any],
    profile: dict[str, Any],
    models: Sequence[str],
    *,
    raw_data_sha256: str,
    split_manifest_sha256: str,
) -> str:
    payload = {
        "runner": "development_locked_holdout",
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
    return f"{dataset_cfg['name']}_{profile['name']}_holdout_{digest}"


def _holdout_evidence_tier(profile_name: str, profile: dict[str, Any]) -> str:
    if profile_name == "smoke":
        return "execution_only_smoke"
    if profile_name == "development":
        return "full_development"
    if profile_name == "final" and bool(profile.get("locked", False)):
        return "final_locked"
    raise ValueError(
        "Holdout studies support only smoke, development, or an authorized locked final profile"
    )


def _atomic_joblib_dump(payload: Any, path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    joblib.dump(payload, temporary)
    os.replace(temporary, path)


def _claim_final_test_access(output_dir: Path, experiment_id: str) -> Path:
    """Create a one-way receipt immediately before an authorized final test access."""

    receipt = output_dir / "FINAL_TEST_ACCESS_STARTED.json"
    payload = {
        "experiment_id": experiment_id,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "warning": "Presence of this receipt prohibits automatic final-test re-execution.",
    }
    try:
        with receipt.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    except FileExistsError as exc:
        raise RuntimeError(
            "Final test access was already started for this study; automatic overwrite or re-run is prohibited"
        ) from exc
    return receipt


def _sample_partition(
    manifest: pd.DataFrame,
    *,
    maximum_rows: int | None,
    seed: int,
) -> pd.DataFrame:
    if maximum_rows is None or len(manifest) <= maximum_rows:
        return manifest.sort_values("row_position").reset_index(drop=True)
    if maximum_rows < 2:
        raise ValueError("A holdout smoke sample must contain at least two rows")
    strata = (
        manifest["target"].astype(str)
        + "|"
        + manifest["outer_fold"].astype(str)
    )
    positions = np.arange(len(manifest))
    selected, _ = train_test_split(
        positions,
        train_size=int(maximum_rows),
        stratify=strata,
        random_state=int(seed),
    )
    return (
        manifest.iloc[np.sort(selected)]
        .sort_values("row_position")
        .reset_index(drop=True)
    )


def _predefined_development_splits(
    manifest: pd.DataFrame,
) -> list[tuple[np.ndarray, np.ndarray]]:
    folds = sorted(int(fold) for fold in manifest["outer_fold"].unique())
    if len(folds) < 2 or folds[0] < 0:
        raise ValueError("Development manifest must contain at least two CV folds")
    positions = np.arange(len(manifest))
    splits: list[tuple[np.ndarray, np.ndarray]] = []
    for fold in folds:
        validation = np.flatnonzero(manifest["outer_fold"].to_numpy() == fold)
        training = np.setdiff1d(positions, validation, assume_unique=True)
        if len(np.unique(manifest.iloc[validation]["target"])) != 2:
            raise ValueError(f"Development fold {fold} does not contain both classes")
        splits.append((training, validation))
    return splits


def _choose_development_champion(scores: pd.DataFrame) -> str:
    ordered = scores.sort_values(
        ["brier_score", "log_loss", "average_precision", "model"],
        ascending=[True, True, False, True],
    )
    return str(ordered.iloc[0]["model"])


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
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join(["---"] * len(columns)) + "|",
    ]
    for row in summary[columns].itertuples(index=False):
        values = [
            f"{value:.4f}" if isinstance(value, float) else str(value)
            for value in row
        ]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def run_holdout_benchmark(
    dataset_name: str,
    *,
    profile_name: str = "smoke",
    models: Sequence[str] = MODEL_NAMES,
) -> HoldoutResult:
    """Tune on development folds, lock choices, then evaluate the held-out test."""

    dataset_cfg = get_dataset_config(dataset_name)
    profile = load_experiment_profile(profile_name)
    if dataset_cfg["evaluation_strategy"] not in {
        "stratified_holdout_cv",
        "stratified_group_holdout_cv",
    }:
        raise ValueError(
            f"{dataset_name} uses {dataset_cfg['evaluation_strategy']}, not a holdout contract"
        )
    models = tuple(dict.fromkeys(str(model) for model in models))
    unknown_models = sorted(set(models) - set(MODEL_NAMES))
    if unknown_models:
        raise ValueError(f"Unknown models: {unknown_models}")
    evidence_tier = _holdout_evidence_tier(profile_name, profile)
    evaluation_role = {
        "smoke": "smoke_test",
        "development": "development_test",
        "final": "locked_final_test",
    }[profile_name]
    run_started_at_utc = datetime.now(timezone.utc).isoformat()
    raw_data_sha256 = _sha256_file(Path(dataset_cfg["raw_path"]))
    analysis_configuration_sha256 = final_analysis_configuration_sha256(
        dataset_name=dataset_name,
        dataset_config=dataset_cfg,
        profile=profile,
        models=models,
    )
    authorized_manifest_path = None
    if profile_name == "final":
        authorized_manifest_path = assert_final_execution_authorized(
            profile_name=profile_name,
            profile=profile,
            dataset_name=dataset_name,
            raw_data_sha256=raw_data_sha256,
            analysis_configuration_sha256=analysis_configuration_sha256,
        )

    dataset = load_dataset(dataset_name)
    audit_path, audit_markdown_path, audit = write_audit(dataset)
    if str(audit["raw_sha256"]) != raw_data_sha256:
        raise RuntimeError("Raw data changed between authorization and dataset audit")
    if profile_name in {"smoke", "development"}:
        split_path, split_metadata_path, manifest = create_and_write_split_manifest(
            dataset, seed=int(profile["seed"])
        )
    else:
        assert authorized_manifest_path is not None
        split_path = authorized_manifest_path
        split_metadata_path = split_path.with_suffix(".json")
        manifest = load_authorized_concealed_manifest(split_path, dataset)
    full_development_manifest = manifest[manifest["role"] == "development"].copy()
    full_test_manifest = manifest[manifest["role"] == "test"].copy()
    sample_limit = profile.get("sample_limits", {}).get(dataset_name)
    sample_limit = int(sample_limit) if sample_limit is not None else None
    development_manifest = _sample_partition(
        full_development_manifest,
        maximum_rows=sample_limit,
        seed=int(profile["seed"]) + 1_000,
    )
    test_manifest = _sample_partition(
        full_test_manifest,
        maximum_rows=sample_limit,
        seed=int(profile["seed"]) + 2_000,
    )
    if set(development_manifest["group_id"]) & set(test_manifest["group_id"]):
        nonempty_overlap = {
            group
            for group in set(development_manifest["group_id"])
            & set(test_manifest["group_id"])
            if str(group)
        }
        if nonempty_overlap:
            raise RuntimeError("Patient groups overlap development and test samples")

    development_positions = development_manifest["row_position"].to_numpy(dtype=int)
    X_development = dataset.X.iloc[development_positions].reset_index(drop=True)
    y_development = dataset.y.iloc[development_positions].to_numpy(dtype=int)
    development_groups = (
        dataset.groups.iloc[development_positions].astype(str).to_numpy()
        if dataset.groups is not None
        else None
    )
    development_splits = _predefined_development_splits(development_manifest)
    model_n_jobs = int(profile.get("model_n_jobs", 1))

    split_manifest_sha256 = json.loads(
        split_metadata_path.read_text(encoding="utf-8")
    )["manifest_sha256"]
    experiment_id = _experiment_id(
        dataset_cfg,
        profile,
        models,
        raw_data_sha256=str(audit["raw_sha256"]),
        split_manifest_sha256=str(split_manifest_sha256),
    )
    output_dir = DEFAULT_OUTPUT_ROOT / "studies" / experiment_id
    trial_dir = output_dir / "trials"
    model_dir = output_dir / "models"
    paper_table_dir = output_dir / "paper_tables"
    checkpoint_dir = output_dir / "checkpoints" / "development_models"
    for path in (trial_dir, model_dir, paper_table_dir, checkpoint_dir):
        path.mkdir(parents=True, exist_ok=True)

    calibration_records: list[dict[str, Any]] = []
    threshold_records: list[dict[str, Any]] = []
    parameter_records: list[dict[str, Any]] = []
    development_prediction_frames: list[pd.DataFrame] = []
    development_scores: list[dict[str, Any]] = []
    locked_artifacts: dict[str, dict[str, Any]] = {}

    for model_index, model_name in enumerate(models):
        checkpoint_path = checkpoint_dir / f"{model_name}.joblib"
        if checkpoint_path.exists():
            checkpoint = joblib.load(checkpoint_path)
            if (
                checkpoint.get("experiment_id") == experiment_id
                and checkpoint.get("model_name") == model_name
            ):
                LOGGER.info("Resuming completed development model %s", model_name)
                calibration_records.extend(checkpoint["calibration_records"])
                threshold_records.extend(checkpoint["threshold_records"])
                parameter_records.append(checkpoint["parameter_record"])
                development_prediction_frames.append(
                    checkpoint["development_predictions"]
                )
                development_scores.append(checkpoint["development_score"])
                locked_artifacts[model_name] = checkpoint["locked_artifact"]
                continue
        LOGGER.info(
            "Development tuning %s dataset=%s rows=%d trials=%d",
            model_name,
            dataset_name,
            len(X_development),
            int(profile["n_trials"]),
        )
        model_seed = int(profile["seed"]) + model_index * 100_000
        start = time.perf_counter()
        tuning = tune_model(
            X_development,
            y_development,
            dataset_cfg,
            model_name,
            n_trials=int(profile["n_trials"]),
            n_splits=len(development_splits),
            seed=model_seed,
            groups=development_groups,
            predefined_splits=development_splits,
            n_jobs=model_n_jobs,
        )
        tuning_seconds = time.perf_counter() - start
        trial_path = trial_dir / f"{model_name}.csv"
        tuning.trials.to_csv(trial_path, index=False)

        inner_probability = cross_fitted_probabilities(
            X_development,
            y_development,
            dataset_cfg,
            model_name,
            tuning.best_params,
            n_splits=len(development_splits),
            seed=model_seed + 10_000,
            groups=development_groups,
            predefined_splits=development_splits,
            n_jobs=model_n_jobs,
        )
        calibration = select_calibrator(
            [str(method) for method in profile["calibration_methods"]],
            inner_probability,
            y_development,
            n_splits=len(development_splits),
            seed=model_seed + 20_000,
            groups=development_groups,
            minimum_samples_by_method={
                str(method): int(minimum)
                for method, minimum in profile.get(
                    "calibration_minimum_samples", {}
                ).items()
            },
        )
        thresholds = select_thresholds(
            [str(policy) for policy in profile["threshold_policies"]],
            y_development,
            calibration.cross_fitted_probability,
            sensitivity_target=profile.get("sensitivity_target"),
        )
        development_metric = binary_metrics(
            y_development,
            calibration.cross_fitted_probability,
            threshold=0.5,
        )
        development_score = {
            "model": model_name,
            "calibration_method": calibration.method,
            **development_metric,
        }
        development_scores.append(development_score)
        development_predictions = pd.DataFrame(
                {
                    "experiment_id": experiment_id,
                    "dataset": dataset_name,
                    "model": model_name,
                    "row_id": development_manifest["row_id"].to_numpy(),
                    "group_id": development_manifest["group_id"].to_numpy(),
                    "development_fold": development_manifest[
                        "outer_fold"
                    ].to_numpy(dtype=int),
                    "target": y_development,
                    "probability_raw_oof": inner_probability,
                    "probability_calibrated_oof": calibration.cross_fitted_probability,
                    "calibration_method": calibration.method,
                }
            )
        development_prediction_frames.append(development_predictions)
        model_calibration_records: list[dict[str, Any]] = []
        for score in calibration.scores:
            record = {
                    "experiment_id": experiment_id,
                    "dataset": dataset_name,
                    "model": model_name,
                    **score,
                    "selected": str(score["method"]) == calibration.method,
                    "selection_data": "development_oof_only",
                }
            calibration_records.append(record)
            model_calibration_records.append(record)
        model_threshold_records: list[dict[str, Any]] = []
        for threshold in thresholds:
            operating = binary_metrics(
                y_development,
                calibration.cross_fitted_probability,
                threshold=float(threshold["threshold"]),
            )
            record = {
                    "experiment_id": experiment_id,
                    "dataset": dataset_name,
                    "model": model_name,
                    "calibration_method": calibration.method,
                    "selection_data": "development_oof_only",
                    "development_sensitivity": operating["sensitivity"],
                    "development_specificity": operating["specificity"],
                    "development_ppv": operating["ppv"],
                    "development_npv": operating["npv"],
                    **threshold,
                }
            threshold_records.append(record)
            model_threshold_records.append(record)

        preprocessor = build_preprocessor(dataset_cfg, model_name)
        transformed_development = preprocessor.fit_transform(X_development)
        model = build_estimator(
            model_name,
            tuning.best_params,
            seed=model_seed + 30_000,
            n_jobs=model_n_jobs,
            positive_class_weight=positive_class_weight(y_development),
        )
        fit_start = time.perf_counter()
        model.fit(transformed_development, y_development)
        fit_seconds = time.perf_counter() - fit_start
        locked_artifact = {
            "model": model,
            "preprocessor": preprocessor,
            "calibrator": calibration.calibrator,
            "calibration_method": calibration.method,
            "thresholds": {
                str(row["threshold_policy"]): float(row["threshold"])
                for row in thresholds
            },
            "best_params": tuning.best_params,
            "tuning_average_precision": tuning.best_score,
            "tuning_seconds": tuning_seconds,
            "fit_seconds": fit_seconds,
        }
        locked_artifacts[model_name] = locked_artifact
        parameter_record = {
                "model": model_name,
                "development_cv_average_precision": tuning.best_score,
                "best_params": json.dumps(tuning.best_params, sort_keys=True),
                "tuning_seconds": tuning_seconds,
                "fit_seconds": fit_seconds,
                "trial_path": str(trial_path),
            }
        parameter_records.append(parameter_record)
        _atomic_joblib_dump(
            {
                "experiment_id": experiment_id,
                "model_name": model_name,
                "calibration_records": model_calibration_records,
                "threshold_records": model_threshold_records,
                "parameter_record": parameter_record,
                "development_predictions": development_predictions,
                "development_score": development_score,
                "locked_artifact": locked_artifact,
            },
            checkpoint_path,
        )

    development_score_frame = pd.DataFrame(development_scores)
    champion = _choose_development_champion(development_score_frame)
    development_score_frame["development_selected_champion"] = (
        development_score_frame["model"] == champion
    )

    # No test feature or label is used before all model, calibration, threshold,
    # and champion choices above have been locked from development data.
    final_access_receipt = None
    if profile_name == "final":
        final_access_receipt = _claim_final_test_access(output_dir, experiment_id)
    test_positions = test_manifest["row_position"].to_numpy(dtype=int)
    X_test = dataset.X.iloc[test_positions].reset_index(drop=True)
    y_test = dataset.y.iloc[test_positions].to_numpy(dtype=int)
    test_groups = (
        dataset.groups.iloc[test_positions].astype(str).to_numpy()
        if dataset.groups is not None
        else None
    )

    prediction_frames: list[pd.DataFrame] = []
    threshold_prediction_frames: list[pd.DataFrame] = []
    metric_records: list[dict[str, Any]] = []
    for model_name in models:
        artifact = locked_artifacts[model_name]
        transformed_test = artifact["preprocessor"].transform(X_test)
        probability_raw = artifact["model"].predict_proba(transformed_test)
        probability_calibrated = artifact["calibrator"].predict(probability_raw)
        prediction_frame = pd.DataFrame(
            {
                "experiment_id": experiment_id,
                "dataset": dataset_name,
                "task": dataset_cfg["task"],
                "endpoint": dataset_cfg["endpoint"],
                "model": model_name,
                "row_id": test_manifest["row_id"].to_numpy(),
                "group_id": test_manifest["group_id"].to_numpy(),
                "evaluation_role": evaluation_role,
                "target": y_test,
                "probability_raw": probability_raw,
                "probability_calibrated": probability_calibrated,
                "calibration_method": artifact["calibration_method"],
                "development_selected_champion": model_name == champion,
            }
        )
        prediction_frames.append(prediction_frame)
        base = {
            "experiment_id": experiment_id,
            "dataset": dataset_name,
            "task": dataset_cfg["task"],
            "endpoint": dataset_cfg["endpoint"],
            "model": model_name,
            "evaluation_role": evaluation_role,
            "calibration_method": artifact["calibration_method"],
            "development_selected_champion": model_name == champion,
            "evidence_tier": evidence_tier,
        }
        raw_metrics = {
            **base,
            "probability_version": "raw",
            "threshold_policy": "fixed_0_5",
        }
        raw_metrics.update(binary_metrics(y_test, probability_raw, threshold=0.5))
        metric_records.append(raw_metrics)
        for threshold_policy, threshold in artifact["thresholds"].items():
            calibrated_metrics = {
                **base,
                "probability_version": "calibrated",
                "threshold_policy": threshold_policy,
            }
            calibrated_metrics.update(
                binary_metrics(
                    y_test,
                    probability_calibrated,
                    threshold=float(threshold),
                )
            )
            metric_records.append(calibrated_metrics)
            threshold_prediction_frames.append(
                prediction_frame.assign(
                    threshold_policy=threshold_policy,
                    threshold=float(threshold),
                    prediction=(probability_calibrated >= float(threshold)).astype(
                        int
                    ),
                )
            )

        bundle = {
            "experiment_id": experiment_id,
            "dataset": dataset_name,
            "task": dataset_cfg["task"],
            "endpoint": dataset_cfg["endpoint"],
            "model_name": model_name,
            "evaluation_strategy": dataset_cfg["evaluation_strategy"],
            "development_rows": len(X_development),
            "test_rows": len(X_test),
            "dataset_configuration_sha256": configuration_sha256(dataset_cfg),
            "source_tree_sha256": source_tree_sha256(),
            "best_params": artifact["best_params"],
            "preprocessor": artifact["preprocessor"],
            "transformed_feature_names": transformed_feature_names(
                artifact["preprocessor"]
            ),
            "model": artifact["model"],
            "calibrator": artifact["calibrator"],
            "calibration_method": artifact["calibration_method"],
            "thresholds": artifact["thresholds"],
            "threshold_policy": "fixed_0_5",
            "threshold": float(artifact["thresholds"]["fixed_0_5"]),
            "development_selected_champion": model_name == champion,
            "evidence_tier": evidence_tier,
            "raw_data_sha256": raw_data_sha256,
            "split_manifest_sha256": split_manifest_sha256,
            "analysis_configuration_sha256": analysis_configuration_sha256,
        }
        bundle_path = model_dir / f"{model_name}.joblib"
        joblib.dump(bundle, bundle_path)

    predictions = pd.concat(prediction_frames, ignore_index=True)
    threshold_predictions = pd.concat(
        threshold_prediction_frames, ignore_index=True
    )
    metrics = pd.DataFrame(metric_records)
    summary = metrics.sort_values(
        ["probability_version", "threshold_policy", "average_precision"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    interval_records: list[dict[str, Any]] = []
    interval_index = 0
    for model_name in models:
        model_predictions = predictions[predictions["model"] == model_name]
        artifact = locked_artifacts[model_name]
        evaluations = [
            ("raw", "fixed_0_5", model_predictions["probability_raw"].to_numpy(), 0.5)
        ]
        evaluations.extend(
            (
                "calibrated",
                threshold_policy,
                model_predictions["probability_calibrated"].to_numpy(),
                float(threshold),
            )
            for threshold_policy, threshold in artifact["thresholds"].items()
        )
        for probability_version, threshold_policy, probability, threshold in evaluations:
            interval_index += 1
            intervals = bootstrap_metric_intervals(
                y_test,
                probability,
                threshold=threshold,
                n_bootstrap=int(profile["n_bootstrap"]),
                seed=int(profile["seed"]) + 500_000 + interval_index,
                groups=test_groups,
            )
            for row in intervals:
                interval_records.append(
                    {
                        "experiment_id": experiment_id,
                        "dataset": dataset_name,
                        "model": model_name,
                        "probability_version": probability_version,
                        "threshold_policy": threshold_policy,
                        "evaluation_role": evaluation_role,
                        **row,
                    }
                )
    confidence_intervals = pd.DataFrame(interval_records)

    sorted_test = test_manifest.sort_values("row_id")
    comparison_groups = (
        sorted_test["group_id"].astype(str).to_numpy()
        if dataset.groups is not None
        else None
    )
    paired_comparisons = paired_bootstrap_model_comparisons(
        predictions,
        n_bootstrap=int(profile["n_bootstrap"]),
        seed=int(profile["seed"]) + 600_000,
        groups=comparison_groups,
    )

    decision_frames: list[pd.DataFrame] = []
    for model_name, frame in predictions.groupby("model", sort=True):
        curve = decision_curve(
            frame["target"].to_numpy(dtype=int),
            frame["probability_calibrated"].to_numpy(dtype=float),
        )
        curve.insert(0, "model", model_name)
        curve.insert(0, "dataset", dataset_name)
        curve.insert(0, "experiment_id", experiment_id)
        decision_frames.append(curve)
    decision_curves = pd.concat(decision_frames, ignore_index=True)
    (
        decision_curve_confidence_intervals,
        decision_curve_paired_contrasts,
    ) = decision_curve_bootstrap_inference(
        predictions[["model", "row_id", "target", "probability_calibrated"]],
        n_bootstrap=int(profile["n_bootstrap"]),
        seed=int(profile["seed"]) + 700_000,
        groups=comparison_groups,
    )
    decision_curve_confidence_intervals.insert(0, "evaluation_role", evaluation_role)
    if not decision_curve_paired_contrasts.empty:
        decision_curve_paired_contrasts.insert(0, "evaluation_role", evaluation_role)

    paths = {
        "development_predictions": output_dir / "development_oof_predictions.csv",
        "development_scores": output_dir / "development_model_scores.csv",
        "predictions": output_dir / "test_predictions.csv",
        "threshold_predictions": output_dir / "test_threshold_predictions.csv",
        "metrics": output_dir / "test_metrics.csv",
        "summary": output_dir / "summary_metrics.csv",
        "calibration": output_dir / "calibration_selection.csv",
        "thresholds": output_dir / "selected_thresholds.csv",
        "parameters": output_dir / "best_parameters.csv",
        "intervals": output_dir / "confidence_intervals.csv",
        "comparisons": output_dir / "paired_bootstrap_model_comparisons.csv",
        "decision_curves": output_dir / "decision_curves.csv",
        "decision_curve_intervals": output_dir
        / "decision_curve_confidence_intervals.csv",
        "decision_curve_contrasts": output_dir / "decision_curve_paired_contrasts.csv",
    }
    pd.concat(development_prediction_frames, ignore_index=True).to_csv(
        paths["development_predictions"], index=False
    )
    development_score_frame.to_csv(paths["development_scores"], index=False)
    predictions.to_csv(paths["predictions"], index=False)
    threshold_predictions.to_csv(paths["threshold_predictions"], index=False)
    metrics.to_csv(paths["metrics"], index=False)
    summary.to_csv(paths["summary"], index=False)
    pd.DataFrame(calibration_records).to_csv(paths["calibration"], index=False)
    pd.DataFrame(threshold_records).to_csv(paths["thresholds"], index=False)
    pd.DataFrame(parameter_records).to_csv(paths["parameters"], index=False)
    confidence_intervals.to_csv(paths["intervals"], index=False)
    paired_comparisons.to_csv(paths["comparisons"], index=False)
    decision_curves.to_csv(paths["decision_curves"], index=False)
    decision_curve_confidence_intervals.to_csv(
        paths["decision_curve_intervals"], index=False
    )
    decision_curve_paired_contrasts.to_csv(
        paths["decision_curve_contrasts"], index=False
    )
    (output_dir / "summary_metrics.md").write_text(
        _markdown_summary(summary), encoding="utf-8"
    )
    summary.to_csv(paper_table_dir / "primary_performance.csv", index=False)
    confidence_intervals.to_csv(
        paper_table_dir / "performance_confidence_intervals.csv", index=False
    )
    paired_comparisons.to_csv(
        paper_table_dir / "paired_bootstrap_model_comparisons.csv", index=False
    )
    decision_curve_confidence_intervals.to_csv(
        paper_table_dir / "decision_curve_confidence_intervals.csv", index=False
    )
    decision_curve_paired_contrasts.to_csv(
        paper_table_dir / "decision_curve_paired_contrasts.csv", index=False
    )
    figures = save_evaluation_plots(
        predictions,
        decision_curves,
        output_dir / "figures",
    )

    metadata_path = output_dir / "experiment_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "experiment_id": experiment_id,
                "runner": "development_locked_holdout",
                "dataset": dataset_name,
                "task": dataset_cfg["task"],
                "endpoint": dataset_cfg["endpoint"],
                "evaluation_strategy": dataset_cfg["evaluation_strategy"],
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
                    "python -m diabetes_pipeline.cli benchmark-holdout "
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
                "evaluation_role": evaluation_role,
                "models": list(models),
                "development_selected_champion": champion,
                "test_access": {
                    "smoke": "smoke_path_check_not_for_scientific_inference",
                    "development": "development_test_previously_accessed_not_final_eligible",
                    "final": "single_locked_final_evaluation",
                }[profile_name],
                "final_test_access_receipt": (
                    str(final_access_receipt.relative_to(output_dir))
                    if final_access_receipt is not None
                    else None
                ),
                "all_choices_locked_before_test_prediction": True,
                "full_development_rows": len(full_development_manifest),
                "evaluated_development_rows": len(development_manifest),
                "full_test_rows": len(full_test_manifest),
                "evaluated_test_rows": len(test_manifest),
                "sample_limit_per_partition": sample_limit,
                "model_n_jobs": model_n_jobs,
                "smoke_sampling_uses_outcome_strata": profile_name == "smoke",
                "bootstrap_resampling_unit": (
                    "patient_cluster" if dataset.groups is not None else "individual"
                ),
                "decision_curve_inference": {
                    "estimation_scope": evaluation_role,
                    "paired_bootstrap": True,
                    "resampling_unit": (
                        "patient_cluster"
                        if dataset.groups is not None
                        else "individual"
                    ),
                },
                "artifacts": [
                    str(path.relative_to(output_dir))
                    for path in [*paths.values(), *figures]
                ],
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )
    return HoldoutResult(
        experiment_id=experiment_id,
        output_dir=output_dir,
        predictions_path=paths["predictions"],
        metrics_path=paths["metrics"],
        summary_path=paths["summary"],
    )
