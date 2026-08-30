"""Availability routing for development-locked holdout studies.

The ordinary routing evaluator operates on repeated outer-fold bundles. BRFSS
and Hospital130 instead have one untouched test partition and models fitted on
all development rows. This module learns panel-specific model/calibration
choices from development folds, then evaluates those locked choices once on
the test partition and saves one reloadable router bundle.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import train_test_split

from diabetes_pipeline.calibration.calibrators import select_calibrator
from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.evaluation.metrics import binary_metrics
from diabetes_pipeline.routing.evaluator import DEFAULT_ROUTING_CONFIG, _choose_model
from diabetes_pipeline.settings import get_dataset_config, source_tree_sha256
from diabetes_pipeline.training.tuning import cross_fitted_probabilities_by_scenario


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _sample_partition(
    manifest: pd.DataFrame,
    *,
    maximum_rows: int | None,
    seed: int,
) -> pd.DataFrame:
    """Reproduce the deterministic sampling used by the holdout runner."""

    if maximum_rows is None or len(manifest) <= maximum_rows:
        return manifest.sort_values("row_position").reset_index(drop=True)
    strata = manifest["target"].astype(str) + "|" + manifest["outer_fold"].astype(str)
    selected, _ = train_test_split(
        np.arange(len(manifest)),
        train_size=int(maximum_rows),
        stratify=strata,
        random_state=int(seed),
    )
    return (
        manifest.iloc[np.sort(selected)]
        .sort_values("row_position")
        .reset_index(drop=True)
    )


def _development_splits(
    manifest: pd.DataFrame,
) -> list[tuple[np.ndarray, np.ndarray]]:
    positions = np.arange(len(manifest))
    splits: list[tuple[np.ndarray, np.ndarray]] = []
    for fold in sorted(int(value) for value in manifest["outer_fold"].unique()):
        if fold < 0:
            continue
        validation = np.flatnonzero(manifest["outer_fold"].to_numpy() == fold)
        training = np.setdiff1d(positions, validation, assume_unique=True)
        splits.append((training, validation))
    if len(splits) < 2:
        raise ValueError("Holdout routing requires at least two development folds")
    return splits


def _masked(
    frame: pd.DataFrame,
    configured_features: list[str],
    available_features: list[str],
) -> pd.DataFrame:
    result = frame.copy()
    for feature in sorted(set(configured_features) - set(available_features)):
        result[feature] = np.nan
    return result


def run_holdout_availability_routing(
    dataset_name: str,
    study_dir: Path | str,
    *,
    routing_config_path: Path = DEFAULT_ROUTING_CONFIG,
):
    """Build a panel-aware router without using test labels for selection."""

    # Imported here to avoid a module-cycle while evaluator dispatches to us.
    from diabetes_pipeline.routing.evaluator import RoutingResult

    study_dir = Path(study_dir).resolve()
    metadata = json.loads(
        (study_dir / "experiment_metadata.json").read_text(encoding="utf-8")
    )
    if metadata.get("dataset") != dataset_name:
        raise ValueError(
            f"Study dataset is {metadata.get('dataset')!r}, not {dataset_name!r}"
        )
    if metadata.get("runner") != "development_locked_holdout":
        raise ValueError("The study is not a development-locked holdout study")

    routing_payload = yaml.safe_load(routing_config_path.read_text(encoding="utf-8"))
    try:
        routing_cfg = dict(routing_payload["datasets"][dataset_name])
    except KeyError as exc:
        raise ValueError(
            f"No availability-routing contract exists for '{dataset_name}'"
        ) from exc

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

    manifest = pd.read_csv(metadata["split_manifest"])
    sample_limit_value = metadata.get("sample_limit_per_partition")
    sample_limit = int(sample_limit_value) if sample_limit_value is not None else None
    seed = int(metadata["profile"]["seed"])
    development_manifest = _sample_partition(
        manifest[manifest["role"] == "development"].copy(),
        maximum_rows=sample_limit,
        seed=seed + 1_000,
    )
    test_manifest = _sample_partition(
        manifest[manifest["role"] == "test"].copy(),
        maximum_rows=sample_limit,
        seed=seed + 2_000,
    )
    development_positions = development_manifest["row_position"].to_numpy(dtype=int)
    test_positions = test_manifest["row_position"].to_numpy(dtype=int)
    X_development = dataset.X.iloc[development_positions].reset_index(drop=True)
    y_development = dataset.y.iloc[development_positions].to_numpy(dtype=int)
    X_test = dataset.X.iloc[test_positions].reset_index(drop=True)
    y_test = dataset.y.iloc[test_positions].to_numpy(dtype=int)
    development_groups = (
        dataset.groups.iloc[development_positions].astype(str).to_numpy()
        if dataset.groups is not None
        else None
    )
    predefined_splits = _development_splits(development_manifest)
    inner_folds = int(metadata["profile"].get("inner_folds_override", len(predefined_splits)))
    model_n_jobs = int(metadata["profile"].get("model_n_jobs", 1))

    configured_models = [str(value) for value in routing_cfg["router_models"]]
    model_paths = {path.stem: path for path in (study_dir / "models").glob("*.joblib")}
    missing_models = sorted(set(configured_models) - set(model_paths))
    if missing_models:
        raise FileNotFoundError(
            f"Required holdout model bundles are missing: {missing_models}"
        )

    development_records: list[dict[str, Any]] = []
    calibration_records: list[dict[str, Any]] = []
    test_prediction_frames: list[pd.DataFrame] = []
    model_bundles: dict[str, dict[str, Any]] = {}
    scenario_calibrators: dict[str, dict[str, Any]] = {}

    for model_index, model_name in enumerate(configured_models):
        model_bundle = joblib.load(model_paths[model_name])
        model_bundles[model_name] = model_bundle
        probabilities = cross_fitted_probabilities_by_scenario(
            X_development,
            y_development,
            dataset_cfg,
            model_name,
            dict(model_bundle["best_params"]),
            scenarios,
            n_splits=len(predefined_splits),
            seed=seed + 100_000 + model_index * 10_000,
            groups=development_groups,
            predefined_splits=predefined_splits,
            n_jobs=model_n_jobs,
        )
        scenario_calibrators[model_name] = {}
        for scenario_name, available_features in scenarios.items():
            calibration = select_calibrator(
                [str(value) for value in metadata["profile"]["calibration_methods"]],
                probabilities[scenario_name],
                y_development,
                n_splits=inner_folds,
                seed=seed + 200_000 + model_index * 10_000,
                groups=development_groups,
                minimum_samples_by_method={
                    str(method): int(minimum)
                    for method, minimum in metadata["profile"].get(
                        "calibration_minimum_samples", {}
                    ).items()
                },
            )
            scenario_calibrators[model_name][scenario_name] = calibration.calibrator
            development_probability = calibration.cross_fitted_probability
            development_records.append(
                {
                    "experiment_id": metadata["experiment_id"],
                    "dataset": dataset_name,
                    "task": dataset_cfg["task"],
                    "endpoint": dataset_cfg["endpoint"],
                    "evaluation_role": metadata["evaluation_role"],
                    "evidence_tier": metadata["evidence_tier"],
                    "scenario": scenario_name,
                    "available_feature_count": len(available_features),
                    "model": model_name,
                    "calibration_method": calibration.method,
                    **binary_metrics(y_development, development_probability, threshold=0.5),
                }
            )
            for score in calibration.scores:
                calibration_records.append(
                    {
                        "experiment_id": metadata["experiment_id"],
                        "dataset": dataset_name,
                        "task": dataset_cfg["task"],
                        "endpoint": dataset_cfg["endpoint"],
                        "evaluation_role": metadata["evaluation_role"],
                        "evidence_tier": metadata["evidence_tier"],
                        "scenario": scenario_name,
                        "model": model_name,
                        **score,
                        "selected": str(score["method"]) == calibration.method,
                    }
                )

            masked_test = _masked(X_test, configured_features, available_features)
            transformed = model_bundle["preprocessor"].transform(masked_test)
            probability_raw = model_bundle["model"].predict_proba(transformed)
            probability_calibrated = calibration.calibrator.predict(probability_raw)
            test_prediction_frames.append(
                pd.DataFrame(
                    {
                        "experiment_id": metadata["experiment_id"],
                        "dataset": dataset_name,
                        "task": dataset_cfg["task"],
                        "endpoint": dataset_cfg["endpoint"],
                        "evaluation_role": metadata["evaluation_role"],
                        "evidence_tier": metadata["evidence_tier"],
                        "scenario": scenario_name,
                        "available_feature_count": len(available_features),
                        "model": model_name,
                        "row_id": test_manifest["row_id"].to_numpy(),
                        "group_id": test_manifest["group_id"].to_numpy(),
                        "target": y_test,
                        "probability_raw": probability_raw,
                        "probability_calibrated": probability_calibrated,
                        "calibration_method": calibration.method,
                    }
                )
            )

    development_scores = pd.DataFrame(development_records)
    calibration_scores = pd.DataFrame(calibration_records)
    stress_predictions = pd.concat(test_prediction_frames, ignore_index=True)
    selected_models: dict[str, str] = {}
    scenario_quality: dict[str, dict[str, float | int | str]] = {}
    selection_records: list[dict[str, Any]] = []
    for scenario_name, scores in development_scores.groupby("scenario", sort=True):
        selected_model = _choose_model(scores)
        selected = scores[scores["model"] == selected_model].iloc[0]
        selected_models[scenario_name] = selected_model
        quality = {
            "selected_model": selected_model,
            "available_feature_count": int(selected["available_feature_count"]),
            "development_brier_score": float(selected["brier_score"]),
            "development_log_loss": float(selected["log_loss"]),
            "development_average_precision": float(selected["average_precision"]),
        }
        scenario_quality[scenario_name] = quality
        selection_records.append(
            {
                "experiment_id": metadata["experiment_id"],
                "dataset": dataset_name,
                "task": dataset_cfg["task"],
                "endpoint": dataset_cfg["endpoint"],
                "evaluation_role": metadata["evaluation_role"],
                "evidence_tier": metadata["evidence_tier"],
                "scenario": scenario_name,
                **quality,
                "selection_data": "development_cross_fitted_masked_predictions",
            }
        )
    selections = pd.DataFrame(selection_records)

    system_frames: list[pd.DataFrame] = []
    for model_name in configured_models:
        frame = stress_predictions[stress_predictions["model"] == model_name].copy()
        frame["system"] = model_name
        system_frames.append(frame)
    for scenario_name, selected_model in selected_models.items():
        frame = stress_predictions[
            (stress_predictions["scenario"] == scenario_name)
            & (stress_predictions["model"] == selected_model)
        ].copy()
        frame["system"] = "availability_router"
        system_frames.append(frame)
    system_predictions = pd.concat(system_frames, ignore_index=True)
    metric_records: list[dict[str, Any]] = []
    for (scenario_name, feature_count, system), frame in system_predictions.groupby(
        ["scenario", "available_feature_count", "system"], sort=True
    ):
        metric_records.append(
            {
                "experiment_id": metadata["experiment_id"],
                "dataset": dataset_name,
                "task": dataset_cfg["task"],
                "endpoint": dataset_cfg["endpoint"],
                "evaluation_role": metadata["evaluation_role"],
                "evidence_tier": metadata["evidence_tier"],
                "scenario": scenario_name,
                "available_feature_count": int(feature_count),
                "system": system,
                **binary_metrics(
                    frame["target"].to_numpy(dtype=int),
                    frame["probability_calibrated"].to_numpy(dtype=float),
                    threshold=0.5,
                ),
            }
        )
    summary = pd.DataFrame(metric_records).sort_values(
        ["available_feature_count", "scenario", "system"]
    )

    output_dir = study_dir / "availability_routing"
    bundle_dir = output_dir / "router_bundles"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "development_scores": output_dir / "development_scores.csv",
        "calibration_scores": output_dir / "calibration_selection.csv",
        "stress_predictions": output_dir / "stress_predictions.csv",
        "selections": output_dir / "router_selections.csv",
        "system_predictions": output_dir / "system_predictions.csv",
        "summary": output_dir / "summary_metrics.csv",
    }
    development_scores.to_csv(paths["development_scores"], index=False)
    calibration_scores.to_csv(paths["calibration_scores"], index=False)
    stress_predictions.to_csv(paths["stress_predictions"], index=False)
    selections.to_csv(paths["selections"], index=False)
    system_predictions.to_csv(paths["system_predictions"], index=False)
    summary.to_csv(paths["summary"], index=False)

    joblib.dump(
        {
            "experiment_id": metadata["experiment_id"],
            "dataset": dataset_name,
            "task": dataset_cfg["task"],
            "endpoint": dataset_cfg["endpoint"],
            "evaluation_role": metadata["evaluation_role"],
            "repeat": 0,
            "outer_fold": 0,
            "configured_features": configured_features,
            "scenarios": scenarios,
            "selected_models": selected_models,
            "scenario_quality": scenario_quality,
            "study_profile": str(metadata["profile"].get("name", "unknown")),
            "evidence_tier": (
                "publication_candidate"
                if str(metadata["profile"].get("name")) == "final"
                and bool(metadata["profile"].get("locked", False))
                else "execution_only"
                if str(metadata["profile"].get("name")) == "smoke"
                else "development_only"
            ),
            "publication_claim_eligible": bool(
                str(metadata["profile"].get("name")) == "final"
                and metadata["profile"].get("locked", False)
            ),
            "test_access": metadata.get("test_access"),
            "model_bundles": model_bundles,
            "scenario_calibrators": scenario_calibrators,
            "threshold": 0.5,
            "threshold_policy": "fixed_0_5",
            "source_tree_sha256": source_tree_sha256(),
        },
        bundle_dir / "router_holdout_development.joblib",
    )
    metadata_path = output_dir / "routing_metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "experiment_id": metadata["experiment_id"],
                "dataset": dataset_name,
                "task": dataset_cfg["task"],
                "endpoint": dataset_cfg["endpoint"],
                "evaluation_role": metadata["evaluation_role"],
                "evidence_tier": metadata["evidence_tier"],
                "development_only_selection": True,
                "test_used_only_after_routing_choices_locked": True,
                "router_models": configured_models,
                "scenarios": scenario_definitions,
                "routing_source_tree_sha256": source_tree_sha256(),
                "artifacts": {
                    str(path.relative_to(study_dir)): _sha256(path)
                    for path in paths.values()
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
