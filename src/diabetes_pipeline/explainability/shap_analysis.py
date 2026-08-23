"""Generate held-out SHAP explanations from a completed benchmark study."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from scipy import sparse

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.explainability.plots import save_shap_plots
from diabetes_pipeline.explainability.stability import importance_tables
from diabetes_pipeline.settings import PROJECT_ROOT, get_dataset_config, source_tree_sha256


_MPL_CONFIG = PROJECT_ROOT / "outputs" / ".matplotlib"
_MPL_CONFIG.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CONFIG))

import shap  # noqa: E402


@dataclass(frozen=True)
class ExplainabilityResult:
    study_dir: Path
    output_dir: Path
    shap_values_path: Path
    global_importance_path: Path
    stability_path: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _dense(values: Any) -> np.ndarray:
    return values.toarray() if sparse.issparse(values) else np.asarray(values)


def _positive_class_values(
    values: Any,
    expected_value: Any,
) -> tuple[np.ndarray, np.ndarray]:
    if isinstance(values, list):
        if len(values) == 2:
            values = values[1]
        elif len(values) == 1:
            values = values[0]
        else:
            raise ValueError(f"Unexpected SHAP class output count: {len(values)}")
    array = np.asarray(values, dtype=float)
    expected = np.asarray(expected_value, dtype=float)
    if array.ndim == 3:
        if array.shape[-1] != 2:
            raise ValueError(f"Unexpected SHAP output shape: {array.shape}")
        array = array[:, :, 1]
        if expected.size == 2:
            expected = expected.reshape(-1)[1]
    if array.ndim != 2:
        raise ValueError(f"SHAP values must be two-dimensional, found {array.shape}")
    return array, expected


def _model_output(model_name: str, estimator: Any, X: np.ndarray) -> np.ndarray:
    if model_name == "logistic_regression":
        return np.asarray(estimator.decision_function(X), dtype=float)
    if model_name == "random_forest":
        return np.asarray(estimator.predict_proba(X)[:, 1], dtype=float)
    if model_name == "xgboost":
        return np.asarray(estimator.predict(X, output_margin=True), dtype=float)
    if model_name == "lightgbm":
        return np.asarray(estimator.predict(X, raw_score=True), dtype=float)
    if model_name == "catboost":
        return np.asarray(
            estimator.predict(X, prediction_type="RawFormulaVal"), dtype=float
        ).reshape(-1)
    raise ValueError(f"Unsupported SHAP model: {model_name}")


def _compute_shap(
    model_name: str,
    estimator: Any,
    X: np.ndarray,
    background: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, str, np.ndarray]:
    if model_name == "logistic_regression":
        explainer = shap.LinearExplainer(estimator, background)
        explanation = explainer(X)
        values = explanation.values
        expected_value = explanation.base_values
        scale = "raw_log_odds"
    else:
        explainer = shap.TreeExplainer(estimator)
        values = explainer.shap_values(X)
        expected_value = explainer.expected_value
        scale = "raw_probability" if model_name == "random_forest" else "raw_margin"
    values, expected = _positive_class_values(values, expected_value)
    if expected.ndim == 0:
        base_values = np.full(len(X), float(expected), dtype=float)
    elif expected.size == len(X):
        base_values = expected.reshape(-1).astype(float)
    else:
        raise ValueError(f"Unexpected SHAP base-value shape: {expected.shape}")
    model_output = _model_output(model_name, estimator, X)
    return values, base_values, scale, model_output


def _sample_validation_rows(
    frame: pd.DataFrame,
    *,
    maximum: int | None,
    seed: int,
) -> pd.DataFrame:
    if maximum is None or len(frame) <= maximum:
        return frame.copy()
    rng = np.random.default_rng(seed)
    selected: list[int] = []
    for _, class_frame in frame.groupby("target"):
        class_count = max(1, round(maximum * len(class_frame) / len(frame)))
        class_count = min(class_count, len(class_frame))
        selected.extend(rng.choice(class_frame.index, size=class_count, replace=False))
    if len(selected) > maximum:
        selected = rng.choice(selected, size=maximum, replace=False).tolist()
    elif len(selected) < maximum:
        remaining = frame.index.difference(selected)
        selected.extend(
            rng.choice(remaining, size=maximum - len(selected), replace=False).tolist()
        )
    return frame.loc[sorted(selected)].copy()


def _raw_feature_matrix(
    raw_X: pd.DataFrame,
    transformed_feature_names: list[str],
) -> np.ndarray:
    raw_values = np.full(
        (len(raw_X), len(transformed_feature_names)), np.nan, dtype=float
    )
    for feature_index, feature in enumerate(transformed_feature_names):
        if feature in raw_X.columns:
            raw_values[:, feature_index] = pd.to_numeric(
                raw_X[feature], errors="coerce"
            ).to_numpy(dtype=float)
        elif feature.startswith("missingindicator_"):
            source_feature = feature.removeprefix("missingindicator_")
            if source_feature in raw_X.columns:
                raw_values[:, feature_index] = raw_X[source_feature].isna().to_numpy(
                    dtype=float
                )
    return raw_values


def _original_feature_name(
    transformed_feature: str,
    original_features: list[str],
) -> str:
    if transformed_feature.startswith("missingindicator_"):
        return transformed_feature.removeprefix("missingindicator_")
    if transformed_feature in original_features:
        return transformed_feature
    for feature in sorted(original_features, key=len, reverse=True):
        if transformed_feature.startswith(f"{feature}_"):
            return feature
    return transformed_feature


def group_shap_by_original_feature(
    shap_values: pd.DataFrame,
    original_features: list[str],
) -> pd.DataFrame:
    """Sum transformed-component SHAP values back to input-level features."""

    frame = shap_values.copy()
    frame["transformed_feature"] = frame["feature"]
    frame["feature"] = frame["feature"].map(
        lambda value: _original_feature_name(str(value), original_features)
    )
    identity_columns = [
        column
        for column in (
            "experiment_id",
            "dataset",
            "model",
            "repeat",
            "outer_fold",
            "evaluation_role",
            "row_id",
            "target",
            "probability_raw",
            "probability_calibrated",
            "calibration_method",
            "base_value",
            "explanation_scale",
            "feature",
        )
        if column in frame.columns
    ]

    def first_finite(series: pd.Series) -> float:
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        return float(numeric.iloc[0]) if len(numeric) else float("nan")

    grouped = (
        frame.groupby(identity_columns, as_index=False, dropna=False)
        .agg(
            shap_value=("shap_value", "sum"),
            raw_feature_value=("raw_feature_value", first_finite),
            transformed_feature_value=("transformed_feature_value", first_finite),
            transformed_component_count=("transformed_feature", "nunique"),
        )
    )
    grouped["absolute_shap_value"] = grouped["shap_value"].abs()
    return grouped


def _dependence_tables(
    shap_values: pd.DataFrame,
    original_numeric_features: list[str],
    *,
    bins: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    bin_records: list[dict[str, float | int | str]] = []
    transition_records: list[dict[str, float | int | str]] = []
    eligible = shap_values[shap_values["feature"].isin(original_numeric_features)]
    for (model_name, feature), frame in eligible.groupby(
        ["model", "feature"], sort=True
    ):
        frame = frame.dropna(subset=["raw_feature_value"]).copy()
        if len(frame) < 3 or frame["raw_feature_value"].nunique() < 2:
            continue
        try:
            frame["bin"] = pd.qcut(
                frame["raw_feature_value"],
                q=min(bins, frame["raw_feature_value"].nunique()),
                duplicates="drop",
            )
        except ValueError:
            continue
        summarized = (
            frame.groupby("bin", observed=True)
            .agg(
                rows=("row_id", "size"),
                value_median=("raw_feature_value", "median"),
                mean_shap=("shap_value", "mean"),
                median_shap=("shap_value", "median"),
                mean_calibrated_probability=("probability_calibrated", "mean"),
            )
            .reset_index()
        )
        for row in summarized.itertuples(index=False):
            bin_records.append(
                {
                    "model": model_name,
                    "feature": feature,
                    "bin_lower": float(row.bin.left),
                    "bin_upper": float(row.bin.right),
                    "rows": int(row.rows),
                    "value_median": float(row.value_median),
                    "mean_shap": float(row.mean_shap),
                    "median_shap": float(row.median_shap),
                    "mean_calibrated_probability": float(
                        row.mean_calibrated_probability
                    ),
                }
            )
        positive = summarized[summarized["median_shap"] > 0]
        if not positive.empty:
            first = positive.iloc[0]
            transition_records.append(
                {
                    "model": model_name,
                    "feature": feature,
                    "first_positive_bin_lower": float(first["bin"].left),
                    "first_positive_bin_upper": float(first["bin"].right),
                    "first_positive_value_median": float(first["value_median"]),
                    "interpretation": (
                        "Exploratory onset of positive contribution relative to the "
                        "model baseline; not a clinical cutoff."
                    ),
                }
            )
    return pd.DataFrame(bin_records), pd.DataFrame(transition_records)


def run_study_explainability(
    dataset_name: str,
    study_dir: Path | str,
    *,
    maximum_samples_per_fold: int | None = 1_000,
    background_size: int = 100,
    top_k: int = 5,
    seed: int = 42,
) -> ExplainabilityResult:
    """Explain only held-out predictions from a completed benchmark study."""

    study_dir = Path(study_dir).resolve()
    metadata_path = study_dir / "experiment_metadata.json"
    predictions_path = study_dir / "predictions.csv"
    model_dir = study_dir / "models"
    for required in (metadata_path, predictions_path, model_dir):
        if not required.exists():
            raise FileNotFoundError(f"Study artifact is missing: {required}")

    study_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if study_metadata["dataset"] != dataset_name:
        raise ValueError(
            f"Study dataset is {study_metadata['dataset']!r}, not {dataset_name!r}"
        )
    dataset_cfg = get_dataset_config(dataset_name)
    dataset = load_dataset(dataset_name)
    predictions = pd.read_csv(predictions_path)
    row_position = {
        str(row_id): position
        for position, row_id in enumerate(dataset.row_ids.astype(str))
    }

    output_dir = study_dir / "explanations"
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
        repeat = int(bundle["repeat"])
        outer_fold = int(bundle["outer_fold"])
        full_validation_frame = predictions[
            (predictions["model"] == model_name)
            & (predictions["repeat"] == repeat)
            & (predictions["outer_fold"] == outer_fold)
        ].copy()
        if full_validation_frame.empty:
            raise RuntimeError(f"No held-out predictions found for {bundle_path.name}")
        frame = _sample_validation_rows(
            full_validation_frame,
            maximum=maximum_samples_per_fold,
            seed=seed + bundle_index,
        )
        try:
            validation_positions = np.asarray(
                [row_position[str(row_id)] for row_id in frame["row_id"]], dtype=int
            )
        except KeyError as exc:
            raise ValueError(f"Prediction row ID is absent from the dataset: {exc}") from exc
        all_positions = np.arange(len(dataset.X))
        full_validation_positions = np.asarray(
            [
                row_position[str(row_id)]
                for row_id in full_validation_frame["row_id"]
            ],
            dtype=int,
        )
        training_positions = np.setdiff1d(all_positions, full_validation_positions)
        rng = np.random.default_rng(seed + 10_000 + bundle_index)
        background_positions = rng.choice(
            training_positions,
            size=min(background_size, len(training_positions)),
            replace=False,
        )

        raw_validation = dataset.X.iloc[validation_positions]
        transformed = _dense(bundle["preprocessor"].transform(raw_validation))
        background = _dense(
            bundle["preprocessor"].transform(dataset.X.iloc[background_positions])
        )
        estimator = bundle["model"].estimator
        values, base_values, explanation_scale, model_output = _compute_shap(
            model_name,
            estimator,
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
        reconstructed = base_values + values.sum(axis=1)
        reconstruction_error = np.abs(reconstructed - model_output)
        maximum_reconstruction_error = float(np.max(reconstruction_error))
        if maximum_reconstruction_error > 1e-4:
            raise RuntimeError(
                f"SHAP additivity check failed for {bundle_path.name}: "
                f"maximum absolute error={maximum_reconstruction_error:.6g}"
            )
        reconstruction_records.append(
            {
                "model": model_name,
                "repeat": repeat,
                "outer_fold": outer_fold,
                "explanation_scale": explanation_scale,
                "explained_rows": len(frame),
                "mean_absolute_reconstruction_error": float(
                    np.mean(reconstruction_error)
                ),
                "maximum_absolute_reconstruction_error": maximum_reconstruction_error,
            }
        )

        raw_values = _raw_feature_matrix(raw_validation, feature_names)
        sample_count, feature_count = values.shape
        shap_frames.append(
            pd.DataFrame(
                {
                    "experiment_id": study_metadata["experiment_id"],
                    "dataset": dataset_name,
                    "model": model_name,
                    "repeat": repeat,
                    "outer_fold": outer_fold,
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

    shap_values_path = output_dir / "shap_values_long.csv"
    global_importance_path = output_dir / "global_shap_importance.csv"
    stability_path = output_dir / "shap_stability_summary.csv"
    shap_values.to_csv(shap_values_path, index=False)
    fold_importance.to_csv(output_dir / "fold_shap_importance.csv", index=False)
    global_importance.to_csv(global_importance_path, index=False)
    pairwise_stability.to_csv(output_dir / "shap_stability_pairwise.csv", index=False)
    stability_summary.to_csv(stability_path, index=False)
    local_contributors.to_csv(output_dir / "local_top_contributors.csv", index=False)
    original_feature_shap.to_csv(
        output_dir / "shap_values_original_features.csv", index=False
    )
    original_fold_importance.to_csv(
        output_dir / "fold_shap_importance_original_features.csv", index=False
    )
    original_global_importance.to_csv(
        output_dir / "global_shap_importance_original_features.csv", index=False
    )
    original_pairwise_stability.to_csv(
        output_dir / "shap_stability_pairwise_original_features.csv", index=False
    )
    original_stability_summary.to_csv(
        output_dir / "shap_stability_summary_original_features.csv", index=False
    )
    local_original_contributors.to_csv(
        output_dir / "local_top_contributors_original_features.csv", index=False
    )
    dependence_bins.to_csv(output_dir / "shap_dependence_bins.csv", index=False)
    contribution_transitions.to_csv(
        output_dir / "exploratory_contribution_transitions.csv", index=False
    )
    reconstruction.to_csv(output_dir / "shap_reconstruction_checks.csv", index=False)
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

    artifact_paths = [
        shap_values_path,
        output_dir / "fold_shap_importance.csv",
        global_importance_path,
        output_dir / "shap_stability_pairwise.csv",
        stability_path,
        output_dir / "local_top_contributors.csv",
        output_dir / "shap_values_original_features.csv",
        output_dir / "fold_shap_importance_original_features.csv",
        output_dir / "global_shap_importance_original_features.csv",
        output_dir / "shap_stability_pairwise_original_features.csv",
        output_dir / "shap_stability_summary_original_features.csv",
        output_dir / "local_top_contributors_original_features.csv",
        output_dir / "shap_dependence_bins.csv",
        output_dir / "exploratory_contribution_transitions.csv",
        output_dir / "shap_reconstruction_checks.csv",
        *figures,
        *original_figures,
    ]
    (output_dir / "explainability_metadata.json").write_text(
        json.dumps(
            {
                "experiment_id": study_metadata["experiment_id"],
                "dataset": dataset_name,
                "held_out_only": True,
                "maximum_samples_per_fold": maximum_samples_per_fold,
                "background_size": background_size,
                "top_k": top_k,
                "seed": seed,
                "model_study_source_tree_sha256": study_metadata[
                    "source_tree_sha256"
                ],
                "explanation_source_tree_sha256": source_tree_sha256(),
                "shap_version": shap.__version__,
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
        shap_values_path=shap_values_path,
        global_importance_path=global_importance_path,
        stability_path=stability_path,
    )
