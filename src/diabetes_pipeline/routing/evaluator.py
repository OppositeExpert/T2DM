"""Nested, development-only evaluation of feature-availability model routing."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml

from diabetes_pipeline.calibration.calibrators import select_calibrator
from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.evaluation.bootstrap import bootstrap_metric_intervals
from diabetes_pipeline.evaluation.comparisons import paired_model_comparisons
from diabetes_pipeline.evaluation.metrics import binary_metrics
from diabetes_pipeline.routing.plots import save_routing_plots
from diabetes_pipeline.settings import PROJECT_ROOT, get_dataset_config, source_tree_sha256
from diabetes_pipeline.training.tuning import cross_fitted_probabilities_by_scenario


DEFAULT_ROUTING_CONFIG = PROJECT_ROOT / "config" / "availability_scenarios.yaml"
ROUTING_INTERVAL_METRICS = (
    "auroc",
    "average_precision",
    "brier_score",
    "log_loss",
    "calibration_intercept",
    "calibration_slope",
    "sensitivity",
    "specificity",
    "ppv",
    "npv",
    "f1",
    "mcc",
)


@dataclass(frozen=True)
class RoutingResult:
    study_dir: Path
    output_dir: Path
    selections_path: Path
    summary_path: Path


def _read_routing_config(
    dataset_name: str,
    path: Path = DEFAULT_ROUTING_CONFIG,
) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    try:
        return dict(payload["datasets"][dataset_name])
    except KeyError as exc:
        raise ValueError(
            f"No availability-routing contract exists for '{dataset_name}'"
        ) from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _mask_to_scenario(
    frame: pd.DataFrame,
    configured_features: list[str],
    available_features: list[str],
) -> pd.DataFrame:
    masked = frame.copy()
    unavailable = sorted(set(configured_features) - set(available_features))
    for feature in unavailable:
        masked[feature] = np.nan
    return masked


def _choose_model(scores: pd.DataFrame) -> str:
    ordered = scores.sort_values(
        ["brier_score", "log_loss", "average_precision", "model"],
        ascending=[True, True, False, True],
    )
    return str(ordered.iloc[0]["model"])


def run_availability_routing(
    dataset_name: str,
    study_dir: Path | str,
    *,
    routing_config_path: Path = DEFAULT_ROUTING_CONFIG,
) -> RoutingResult:
    """Evaluate whether feature-panel-aware routing beats fixed model choices."""

    study_dir = Path(study_dir).resolve()
    metadata = json.loads(
        (study_dir / "experiment_metadata.json").read_text(encoding="utf-8")
    )
    if metadata["dataset"] != dataset_name:
        raise ValueError(
            f"Study dataset is {metadata['dataset']!r}, not {dataset_name!r}"
        )
    if metadata.get("runner") in {
        "development_locked_holdout",
        "locked_internal_validation_holdout",
    }:
        from diabetes_pipeline.routing.holdout_evaluator import (
            run_holdout_availability_routing,
        )

        return run_holdout_availability_routing(
            dataset_name,
            study_dir,
            routing_config_path=routing_config_path,
        )
    profile = dict(metadata["profile"])
    routing_cfg = _read_routing_config(dataset_name, routing_config_path)
    dataset_cfg = get_dataset_config(dataset_name)
    dataset = load_dataset(dataset_name)
    configured_features = list(
        dataset_cfg["numeric_features"] + dataset_cfg["categorical_features"]
    )
    scenario_definitions = dict(routing_cfg["scenarios"])
    scenarios = {
        name: list(definition["available_features"])
        for name, definition in scenario_definitions.items()
    }
    if "full" not in scenarios or set(scenarios["full"]) != set(configured_features):
        raise ValueError("Routing contract requires a 'full' scenario with every feature")
    router_models = [str(model) for model in routing_cfg["router_models"]]

    split_manifest = pd.read_csv(metadata["split_manifest"])
    prediction_manifest = pd.read_csv(study_dir / "predictions.csv")
    outer_splits = sorted(
        {
            (int(repeat), int(fold))
            for repeat, fold in prediction_manifest[
                ["repeat", "outer_fold"]
            ].itertuples(index=False)
        }
    )
    model_n_jobs = int(profile.get("model_n_jobs", 1))
    output_dir = study_dir / "availability_routing"
    router_bundle_dir = output_dir / "router_bundles"
    figure_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    router_bundle_dir.mkdir(parents=True, exist_ok=True)

    development_records: list[dict[str, Any]] = []
    calibration_records: list[dict[str, Any]] = []
    stress_prediction_frames: list[pd.DataFrame] = []
    selection_records: list[dict[str, Any]] = []

    for repeat, outer_fold in outer_splits:
        fold_manifest = split_manifest[
            (split_manifest["repeat"] == repeat)
            & (split_manifest["outer_fold"] == outer_fold)
        ]
        training_positions = fold_manifest.loc[
            fold_manifest["role"] == "train", "row_position"
        ].to_numpy(dtype=int)
        validation_manifest = fold_manifest[
            fold_manifest["role"] == "validation"
        ].copy()
        validation_positions = validation_manifest["row_position"].to_numpy(dtype=int)
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
        inner_folds = int(
            profile.get("inner_folds_override") or dataset_cfg["inner_folds"]
        )
        fold_development_records: list[dict[str, Any]] = []
        model_bundles: dict[str, dict[str, Any]] = {}
        scenario_calibrators: dict[str, dict[str, Any]] = {}

        for model_name in router_models:
            bundle_path = (
                study_dir
                / "models"
                / f"{model_name}_repeat_{repeat}_fold_{outer_fold}.joblib"
            )
            if not bundle_path.exists():
                raise FileNotFoundError(f"Required model bundle is missing: {bundle_path}")
            bundle = joblib.load(bundle_path)
            model_bundles[model_name] = bundle
            scenario_calibrators[model_name] = {}
            inner_probabilities = cross_fitted_probabilities_by_scenario(
                X_training,
                y_training,
                dataset_cfg,
                model_name,
                dict(bundle["best_params"]),
                scenarios,
                n_splits=inner_folds,
                seed=split_seed + 40_000,
                groups=training_groups,
                n_jobs=model_n_jobs,
            )

            for scenario_name, available_features in scenarios.items():
                calibration = select_calibrator(
                    [str(method) for method in profile["calibration_methods"]],
                    inner_probabilities[scenario_name],
                    y_training,
                    n_splits=inner_folds,
                    seed=split_seed + 50_000,
                    groups=training_groups,
                    minimum_samples_by_method={
                        str(method): int(minimum)
                        for method, minimum in profile.get(
                            "calibration_minimum_samples", {}
                        ).items()
                    },
                )
                scenario_calibrators[model_name][scenario_name] = calibration.calibrator
                development_probability = calibration.cross_fitted_probability
                development_metric = binary_metrics(
                    y_training, development_probability, threshold=0.5
                )
                development_row = {
                    "experiment_id": metadata["experiment_id"],
                    "dataset": dataset_name,
                    "repeat": repeat,
                    "outer_fold": outer_fold,
                    "scenario": scenario_name,
                    "available_feature_count": len(available_features),
                    "model": model_name,
                    "calibration_method": calibration.method,
                    **development_metric,
                }
                development_records.append(development_row)
                fold_development_records.append(development_row)
                for score in calibration.scores:
                    calibration_records.append(
                        {
                            "experiment_id": metadata["experiment_id"],
                            "dataset": dataset_name,
                            "repeat": repeat,
                            "outer_fold": outer_fold,
                            "scenario": scenario_name,
                            "model": model_name,
                            **score,
                            "selected": str(score["method"]) == calibration.method,
                        }
                    )

                masked_validation = _mask_to_scenario(
                    X_validation,
                    configured_features,
                    available_features,
                )
                transformed_validation = bundle["preprocessor"].transform(
                    masked_validation
                )
                probability_raw = bundle["model"].predict_proba(
                    transformed_validation
                )
                probability_calibrated = calibration.calibrator.predict(
                    probability_raw
                )
                stress_prediction_frames.append(
                    pd.DataFrame(
                        {
                            "experiment_id": metadata["experiment_id"],
                            "dataset": dataset_name,
                            "repeat": repeat,
                            "outer_fold": outer_fold,
                            "scenario": scenario_name,
                            "available_feature_count": len(available_features),
                            "model": model_name,
                            "row_id": validation_manifest["row_id"].to_numpy(),
                            "group_id": validation_manifest["group_id"].to_numpy(),
                            "target": y_validation,
                            "probability_raw": probability_raw,
                            "probability_calibrated": probability_calibrated,
                            "calibration_method": calibration.method,
                        }
                    )
                )

        fold_scores = pd.DataFrame(fold_development_records)
        full_panel_champion = _choose_model(
            fold_scores[fold_scores["scenario"] == "full"]
        )
        robust_scores = (
            fold_scores.groupby("model", as_index=False)
            .agg(
                brier_score=("brier_score", "mean"),
                log_loss=("log_loss", "mean"),
                average_precision=("average_precision", "mean"),
            )
        )
        robust_single_model = _choose_model(robust_scores)
        selected_models: dict[str, str] = {}
        scenario_quality: dict[str, dict[str, float | int | str]] = {}
        for scenario_name, scenario_scores in fold_scores.groupby(
            "scenario", sort=True
        ):
            selected_model = _choose_model(scenario_scores)
            selected_models[scenario_name] = selected_model
            selected_score = scenario_scores[
                scenario_scores["model"] == selected_model
            ].iloc[0]
            scenario_quality[scenario_name] = {
                "selected_model": selected_model,
                "available_feature_count": int(
                    selected_score["available_feature_count"]
                ),
                "development_brier_score": float(selected_score["brier_score"]),
                "development_log_loss": float(selected_score["log_loss"]),
                "development_average_precision": float(
                    selected_score["average_precision"]
                ),
            }
            selection_records.append(
                {
                    "experiment_id": metadata["experiment_id"],
                    "dataset": dataset_name,
                    "repeat": repeat,
                    "outer_fold": outer_fold,
                    "scenario": scenario_name,
                    "available_feature_count": int(
                        selected_score["available_feature_count"]
                    ),
                    "selected_model": selected_model,
                    "development_brier_score": float(selected_score["brier_score"]),
                    "development_log_loss": float(selected_score["log_loss"]),
                    "development_average_precision": float(
                        selected_score["average_precision"]
                    ),
                    "full_panel_champion": full_panel_champion,
                    "robust_single_model": robust_single_model,
                    "selection_data": "inner_cross_fitted_masked_predictions",
                }
            )

        joblib.dump(
            {
                "experiment_id": metadata["experiment_id"],
                "dataset": dataset_name,
                "task": dataset_cfg["task"],
                "endpoint": dataset_cfg["endpoint"],
                "repeat": repeat,
                "outer_fold": outer_fold,
                "raw_data_sha256": metadata.get("raw_data_sha256"),
                "split_manifest_sha256": metadata.get("split_manifest_sha256"),
                "analysis_configuration_sha256": metadata.get(
                    "analysis_configuration_sha256"
                ),
                "protocol_id": metadata.get("protocol_id"),
                "configured_features": configured_features,
                "scenarios": scenarios,
                "selected_models": selected_models,
                "scenario_quality": scenario_quality,
                "study_profile": str(profile.get("name", "unknown")),
                "evidence_tier": metadata.get("evidence_tier", "unknown"),
                "publication_claim_eligible": bool(
                    str(profile.get("name"))
                    in {"final", "final_internal_validation"}
                    and profile.get("locked", False)
                ),
                "full_panel_champion": full_panel_champion,
                "robust_single_model": robust_single_model,
                "model_bundles": model_bundles,
                "scenario_calibrators": scenario_calibrators,
                "threshold": 0.5,
                "threshold_policy": "fixed_0_5",
                "source_tree_sha256": source_tree_sha256(),
            },
            router_bundle_dir / f"router_repeat_{repeat}_fold_{outer_fold}.joblib",
        )

    development_scores = pd.DataFrame(development_records)
    calibration_scores = pd.DataFrame(calibration_records)
    stress_predictions = pd.concat(stress_prediction_frames, ignore_index=True)
    selections = pd.DataFrame(selection_records)

    system_prediction_frames: list[pd.DataFrame] = []
    for model_name in router_models:
        frame = stress_predictions[stress_predictions["model"] == model_name].copy()
        frame["system"] = model_name
        frame["selected_model"] = model_name
        system_prediction_frames.append(frame)
    for selection in selections.itertuples(index=False):
        candidates = stress_predictions[
            (stress_predictions["repeat"] == selection.repeat)
            & (stress_predictions["outer_fold"] == selection.outer_fold)
            & (stress_predictions["scenario"] == selection.scenario)
        ]
        for system, model_name in (
            ("availability_router", selection.selected_model),
            ("full_panel_champion", selection.full_panel_champion),
            ("robust_single_model", selection.robust_single_model),
        ):
            frame = candidates[candidates["model"] == model_name].copy()
            frame["system"] = system
            frame["selected_model"] = model_name
            system_prediction_frames.append(frame)
    system_predictions = pd.concat(system_prediction_frames, ignore_index=True)

    metric_records: list[dict[str, Any]] = []
    for keys, frame in system_predictions.groupby(
        ["repeat", "outer_fold", "scenario", "available_feature_count", "system"],
        sort=True,
    ):
        repeat, outer_fold, scenario_name, feature_count, system = keys
        row = {
            "experiment_id": metadata["experiment_id"],
            "dataset": dataset_name,
            "repeat": int(repeat),
            "outer_fold": int(outer_fold),
            "scenario": scenario_name,
            "available_feature_count": int(feature_count),
            "system": system,
            "selected_model": "|".join(sorted(frame["selected_model"].unique())),
        }
        row.update(
            binary_metrics(
                frame["target"].to_numpy(dtype=int),
                frame["probability_calibrated"].to_numpy(dtype=float),
                threshold=0.5,
            )
        )
        metric_records.append(row)
    fold_metrics = pd.DataFrame(metric_records)
    summary_columns = [
        "auroc",
        "average_precision",
        "brier_score",
        "log_loss",
        "calibration_intercept",
        "calibration_slope",
        "sensitivity",
        "specificity",
        "ppv",
        "npv",
        "f1",
        "mcc",
    ]
    summary = (
        fold_metrics.groupby(
            ["scenario", "available_feature_count", "system"], as_index=False
        )[summary_columns]
        .mean(numeric_only=True)
        .sort_values(["available_feature_count", "scenario", "brier_score"])
    )

    interval_records: list[dict[str, Any]] = []
    interval_seed = int(profile["seed"]) + 700_000
    comparison_systems = {
        "availability_router",
        "full_panel_champion",
        "robust_single_model",
    }
    pooled_system_predictions = system_predictions[
        system_predictions["system"].isin(comparison_systems)
    ]
    for index, (keys, frame) in enumerate(
        pooled_system_predictions.groupby(
            ["repeat", "scenario", "available_feature_count", "system"], sort=True
        )
    ):
        repeat, scenario_name, feature_count, system = keys
        rows = bootstrap_metric_intervals(
            frame["target"].to_numpy(dtype=int),
            frame["probability_calibrated"].to_numpy(dtype=float),
            threshold=0.5,
            n_bootstrap=int(profile["n_bootstrap"]),
            seed=interval_seed + index,
            metric_names=ROUTING_INTERVAL_METRICS,
        )
        for row in rows:
            interval_records.append(
                {
                    "experiment_id": metadata["experiment_id"],
                    "dataset": dataset_name,
                    "repeat": int(repeat),
                    "scenario": scenario_name,
                    "available_feature_count": int(feature_count),
                    "system": system,
                    **row,
                }
            )
    confidence_intervals = pd.DataFrame(interval_records)

    comparison_records: list[pd.DataFrame] = []
    for scenario_name, frame in fold_metrics[
        fold_metrics["system"].isin(comparison_systems)
    ].groupby("scenario", sort=True):
        comparison_input = frame.rename(columns={"system": "model"})
        comparisons = paired_model_comparisons(comparison_input)
        comparisons.insert(0, "scenario", scenario_name)
        comparison_records.append(comparisons)
    paired_comparisons = pd.concat(comparison_records, ignore_index=True)

    gain_records: list[dict[str, Any]] = []
    for scenario_name, frame in summary.groupby("scenario", sort=True):
        indexed = frame.set_index("system")
        router = indexed.loc["availability_router"]
        for baseline in ("full_panel_champion", "robust_single_model"):
            comparison = indexed.loc[baseline]
            gain_records.append(
                {
                    "scenario": scenario_name,
                    "available_feature_count": int(
                        router["available_feature_count"]
                    ),
                    "baseline": baseline,
                    "average_precision_gain": float(
                        router["average_precision"]
                        - comparison["average_precision"]
                    ),
                    "brier_score_reduction": float(
                        comparison["brier_score"] - router["brier_score"]
                    ),
                    "log_loss_reduction": float(
                        comparison["log_loss"] - router["log_loss"]
                    ),
                }
            )
    router_gains = pd.DataFrame(gain_records)

    paths = {
        "development_scores": output_dir / "development_scores.csv",
        "calibration_scores": output_dir / "calibration_selection.csv",
        "stress_predictions": output_dir / "stress_predictions.csv",
        "selections": output_dir / "router_selections.csv",
        "system_predictions": output_dir / "system_predictions.csv",
        "fold_metrics": output_dir / "fold_metrics.csv",
        "summary": output_dir / "summary_metrics.csv",
        "confidence_intervals": output_dir / "confidence_intervals.csv",
        "paired_comparisons": output_dir / "paired_system_comparisons.csv",
        "router_gains": output_dir / "router_gains.csv",
    }
    development_scores.to_csv(paths["development_scores"], index=False)
    calibration_scores.to_csv(paths["calibration_scores"], index=False)
    stress_predictions.to_csv(paths["stress_predictions"], index=False)
    selections.to_csv(paths["selections"], index=False)
    system_predictions.to_csv(paths["system_predictions"], index=False)
    fold_metrics.to_csv(paths["fold_metrics"], index=False)
    summary.to_csv(paths["summary"], index=False)
    confidence_intervals.to_csv(paths["confidence_intervals"], index=False)
    paired_comparisons.to_csv(paths["paired_comparisons"], index=False)
    router_gains.to_csv(paths["router_gains"], index=False)
    figures = save_routing_plots(summary, selections, figure_dir)

    metadata_path = output_dir / "routing_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "experiment_id": metadata["experiment_id"],
                "dataset": dataset_name,
                "development_only_selection": True,
                "selection_order": [
                    "minimum_brier_score",
                    "minimum_log_loss",
                    "maximum_average_precision",
                ],
                "router_models": router_models,
                "scenarios": scenario_definitions,
                "model_study_source_tree_sha256": metadata[
                    "source_tree_sha256"
                ],
                "routing_source_tree_sha256": source_tree_sha256(),
                "artifacts": {
                    str(path.relative_to(study_dir)): _sha256(path)
                    for path in [*paths.values(), *figures]
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return RoutingResult(
        study_dir=study_dir,
        output_dir=output_dir,
        selections_path=paths["selections"],
        summary_path=paths["summary"],
    )
