"""Held-out SHAP analysis for development-locked test studies."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.explainability.plots import save_shap_plots
from diabetes_pipeline.explainability.shap_analysis import (
    ExplainabilityResult,
    _compute_shap,
    _dense,
    _dependence_tables,
    group_shap_by_original_feature,
    _raw_feature_matrix,
    _sample_validation_rows,
    _sha256,
    shap,
)
from diabetes_pipeline.explainability.stability import importance_tables
from diabetes_pipeline.settings import get_dataset_config, source_tree_sha256


def run_holdout_explainability(
    dataset_name: str,
    study_dir: Path | str,
    *,
    maximum_samples_per_model: int | None = 1_000,
    background_size: int = 100,
    top_k: int = 5,
    seed: int = 42,
) -> ExplainabilityResult:
    """Explain only locked test predictions from a holdout benchmark."""

    study_dir = Path(study_dir).resolve()
    metadata_path = study_dir / "experiment_metadata.json"
    predictions_path = study_dir / "test_predictions.csv"
    development_path = study_dir / "development_oof_predictions.csv"
    model_dir = study_dir / "models"
    for required in (
        metadata_path,
        predictions_path,
        development_path,
        model_dir,
    ):
        if not required.exists():
            raise FileNotFoundError(f"Holdout study artifact is missing: {required}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("runner") not in {
        "development_locked_holdout",
        "locked_internal_validation_holdout",
    }:
        raise ValueError("Study was not produced by the locked holdout runner")
    if metadata["dataset"] != dataset_name:
        raise ValueError(
            f"Study dataset is {metadata['dataset']!r}, not {dataset_name!r}"
        )
    dataset_cfg = get_dataset_config(dataset_name)
    dataset = load_dataset(dataset_name)
    predictions = pd.read_csv(predictions_path)
    evaluation_roles = predictions.get(
        "evaluation_role", pd.Series(dtype=str)
    ).dropna().unique()
    evaluation_role = (
        str(evaluation_roles[0])
        if len(evaluation_roles) == 1
        else str(metadata.get("evaluation_role", "holdout_test"))
    )
    development_predictions = pd.read_csv(development_path)
    row_position = {
        str(row_id): position
        for position, row_id in enumerate(dataset.row_ids.astype(str))
    }

    output_dir = study_dir / "test_explanations"
    figure_dir = output_dir / "figures"
    output_dir.mkdir(parents=True, exist_ok=True)
    shap_frames: list[pd.DataFrame] = []
    reconstruction_records: list[dict[str, float | int | str]] = []
    bundle_paths = sorted(model_dir.glob("*.joblib"))
    if not bundle_paths:
        raise RuntimeError(f"No model bundles found in {model_dir}")

    for bundle_index, bundle_path in enumerate(bundle_paths):
        bundle = joblib.load(bundle_path)
        model_name = str(bundle["model_name"])
        full_test_frame = predictions[predictions["model"] == model_name].copy()
        if full_test_frame.empty:
            raise RuntimeError(f"No held-out test predictions found for {model_name}")
        frame = _sample_validation_rows(
            full_test_frame,
            maximum=maximum_samples_per_model,
            seed=seed + bundle_index,
        )
        test_positions = np.asarray(
            [row_position[str(row_id)] for row_id in frame["row_id"]], dtype=int
        )
        development_rows = development_predictions[
            development_predictions["model"] == model_name
        ]["row_id"].astype(str).drop_duplicates()
        development_positions = np.asarray(
            [row_position[row_id] for row_id in development_rows], dtype=int
        )
        rng = np.random.default_rng(seed + 10_000 + bundle_index)
        background_positions = rng.choice(
            development_positions,
            size=min(background_size, len(development_positions)),
            replace=False,
        )

        raw_test = dataset.X.iloc[test_positions]
        transformed = _dense(bundle["preprocessor"].transform(raw_test))
        background = _dense(
            bundle["preprocessor"].transform(
                dataset.X.iloc[background_positions]
            )
        )
        values, base_values, explanation_scale, model_output = _compute_shap(
            model_name,
            bundle["model"].estimator,
            transformed,
            background,
        )
        feature_names = list(bundle["transformed_feature_names"])
        if values.shape != transformed.shape or values.shape[1] != len(feature_names):
            raise ValueError(
                f"SHAP/feature shape mismatch for {bundle_path.name}: "
                f"SHAP={values.shape}, transformed={transformed.shape}, "
                f"features={len(feature_names)}"
            )
        reconstruction_error = np.abs(
            base_values + values.sum(axis=1) - model_output
        )
        maximum_error = float(np.max(reconstruction_error))
        if maximum_error > 1e-4:
            raise RuntimeError(
                f"SHAP additivity check failed for {bundle_path.name}: "
                f"maximum absolute error={maximum_error:.6g}"
            )
        reconstruction_records.append(
            {
                "model": model_name,
                "repeat": 0,
                "outer_fold": -1,
                "explanation_scale": explanation_scale,
                "explained_rows": len(frame),
                "mean_absolute_reconstruction_error": float(
                    np.mean(reconstruction_error)
                ),
                "maximum_absolute_reconstruction_error": maximum_error,
            }
        )

        raw_values = _raw_feature_matrix(raw_test, feature_names)
        sample_count, feature_count = values.shape
        shap_frames.append(
            pd.DataFrame(
                {
                    "experiment_id": metadata["experiment_id"],
                    "dataset": dataset_name,
                    "model": model_name,
                    "repeat": 0,
                    "outer_fold": -1,
                    "evaluation_role": evaluation_role,
                    "row_id": np.repeat(frame["row_id"].to_numpy(), feature_count),
                    "target": np.repeat(frame["target"].to_numpy(), feature_count),
                    "probability_raw": np.repeat(
                        frame["probability_raw"].to_numpy(), feature_count
                    ),
                    "probability_calibrated": np.repeat(
                        frame["probability_calibrated"].to_numpy(), feature_count
                    ),
                    "calibration_method": np.repeat(
                        frame["calibration_method"].to_numpy(), feature_count
                    ),
                    "feature": np.tile(feature_names, sample_count),
                    "raw_feature_value": raw_values.reshape(-1),
                    "transformed_feature_value": transformed.reshape(-1),
                    "shap_value": values.reshape(-1),
                    "absolute_shap_value": np.abs(values).reshape(-1),
                    "base_value": np.repeat(base_values, feature_count),
                    "explanation_scale": explanation_scale,
                }
            )
        )

    shap_values = pd.concat(shap_frames, ignore_index=True)
    original_features = list(
        dataset_cfg["numeric_features"] + dataset_cfg["categorical_features"]
    )
    original_feature_shap = group_shap_by_original_feature(
        shap_values, original_features
    )
    fold_importance, global_importance, pairwise_stability, stability_summary = (
        importance_tables(shap_values, top_k=top_k)
    )
    (
        original_fold_importance,
        original_global_importance,
        original_pairwise_stability,
        original_stability_summary,
    ) = importance_tables(original_feature_shap, top_k=top_k)
    local_contributors = (
        shap_values.sort_values("absolute_shap_value", ascending=False)
        .groupby(["model", "row_id"], sort=False)
        .head(top_k)
        .copy()
    )
    local_contributors["contribution_direction"] = np.where(
        local_contributors["shap_value"] >= 0,
        "raises_model_output",
        "lowers_model_output",
    )
    local_original_contributors = (
        original_feature_shap.sort_values("absolute_shap_value", ascending=False)
        .groupby(["model", "row_id"], sort=False)
        .head(top_k)
        .copy()
    )
    local_original_contributors["contribution_direction"] = np.where(
        local_original_contributors["shap_value"] >= 0,
        "raises_model_output",
        "lowers_model_output",
    )
    dependence_bins, contribution_transitions = _dependence_tables(
        shap_values,
        list(dataset_cfg["numeric_features"]),
    )
    reconstruction = pd.DataFrame(reconstruction_records)

    paths = {
        "shap_values": output_dir / "shap_values_long.csv",
        "fold_importance": output_dir / "test_shap_importance.csv",
        "global_importance": output_dir / "global_shap_importance.csv",
        "pairwise_stability": output_dir / "shap_stability_pairwise.csv",
        "stability": output_dir / "shap_stability_summary.csv",
        "local": output_dir / "local_top_contributors.csv",
        "dependence": output_dir / "shap_dependence_bins.csv",
        "transitions": output_dir / "exploratory_contribution_transitions.csv",
        "reconstruction": output_dir / "shap_reconstruction_checks.csv",
        "original_values": output_dir / "shap_values_original_features.csv",
        "original_fold_importance": output_dir
        / "test_shap_importance_original_features.csv",
        "original_global_importance": output_dir
        / "global_shap_importance_original_features.csv",
        "original_pairwise_stability": output_dir
        / "shap_stability_pairwise_original_features.csv",
        "original_stability": output_dir
        / "shap_stability_summary_original_features.csv",
        "original_local": output_dir
        / "local_top_contributors_original_features.csv",
    }
    shap_values.to_csv(paths["shap_values"], index=False)
    fold_importance.to_csv(paths["fold_importance"], index=False)
    global_importance.to_csv(paths["global_importance"], index=False)
    pairwise_stability.to_csv(paths["pairwise_stability"], index=False)
    stability_summary.to_csv(paths["stability"], index=False)
    local_contributors.to_csv(paths["local"], index=False)
    dependence_bins.to_csv(paths["dependence"], index=False)
    contribution_transitions.to_csv(paths["transitions"], index=False)
    reconstruction.to_csv(paths["reconstruction"], index=False)
    original_feature_shap.to_csv(paths["original_values"], index=False)
    original_fold_importance.to_csv(
        paths["original_fold_importance"], index=False
    )
    original_global_importance.to_csv(
        paths["original_global_importance"], index=False
    )
    original_pairwise_stability.to_csv(
        paths["original_pairwise_stability"], index=False
    )
    original_stability_summary.to_csv(paths["original_stability"], index=False)
    local_original_contributors.to_csv(paths["original_local"], index=False)
    figures = save_shap_plots(
        shap_values,
        global_importance,
        stability_summary,
        figure_dir,
        top_n=10,
        dependence_features=3,
    )
    original_figures = save_shap_plots(
        original_feature_shap,
        original_global_importance,
        original_stability_summary,
        figure_dir / "original_features",
        top_n=10,
        dependence_features=3,
    )

    artifact_paths = [*paths.values(), *figures, *original_figures]
    (output_dir / "explainability_metadata.json").write_text(
        json.dumps(
            {
                "experiment_id": metadata["experiment_id"],
                "dataset": dataset_name,
                "evaluation_role": evaluation_role,
                "held_out_test_only": True,
                "study_test_access": metadata["test_access"],
                "maximum_samples_per_model": maximum_samples_per_model,
                "background_source": "development_rows_only",
                "background_size": background_size,
                "top_k": top_k,
                "seed": seed,
                "model_study_source_tree_sha256": metadata[
                    "source_tree_sha256"
                ],
                "explanation_source_tree_sha256": source_tree_sha256(),
                "shap_version": shap.__version__,
                "fold_stability_available": False,
                "fold_stability_reason": f"one_{evaluation_role}_evaluation_per_model",
                "artifacts": {
                    str(path.relative_to(study_dir)): _sha256(path)
                    for path in artifact_paths
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return ExplainabilityResult(
        study_dir=study_dir,
        output_dir=output_dir,
        shap_values_path=paths["shap_values"],
        global_importance_path=paths["global_importance"],
        stability_path=paths["stability"],
    )
