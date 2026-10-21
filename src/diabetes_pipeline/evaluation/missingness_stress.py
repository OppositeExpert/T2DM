"""Development-only random and structured feature-missingness stress tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import joblib
import numpy as np
import pandas as pd
from scipy.stats import t

from diabetes_pipeline.artifacts.bundles import predict_bundle
from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.evaluation.metrics import binary_metrics
from diabetes_pipeline.routing.evaluator import _read_routing_config
from diabetes_pipeline.runner import _selected_outer_splits
from diabetes_pipeline.settings import source_tree_sha256


MECHANISMS = ("mcar_independent", "structured_block")
STRESS_METRICS = ("auroc", "average_precision", "brier_score", "log_loss")


@dataclass(frozen=True)
class MissingnessStressResult:
    study_dir: Path
    output_dir: Path
    metrics_path: Path
    summary_path: Path
    report_path: Path


def applicability_guard_ablation(predictions: pd.DataFrame) -> pd.DataFrame:
    """Compare always-predict behavior with named-panel applicability abstention."""

    required = {
        "model", "mechanism", "severity", "mask_replicate", "repeat",
        "outer_fold", "target", "probability_calibrated", "supported_named_panel",
    }
    missing = sorted(required - set(predictions.columns))
    if missing:
        raise ValueError(f"Stress predictions lack guard columns: {missing}")
    records = []
    keys = ["model", "mechanism", "severity", "mask_replicate", "repeat", "outer_fold"]
    for values, frame in predictions.groupby(keys, sort=True):
        model, mechanism, severity, replicate, repeat, fold = values
        total_events = int(frame["target"].sum())
        for policy, accepted in (
            ("always_predict", np.ones(len(frame), dtype=bool)),
            ("named_panel_guard", frame["supported_named_panel"].astype(bool).to_numpy()),
        ):
            retained = frame.loc[accepted]
            retained_events = int(retained["target"].sum())
            base = {
                "model": model, "mechanism": mechanism, "severity": float(severity),
                "mask_replicate": int(replicate), "repeat": int(repeat),
                "outer_fold": int(fold), "policy": policy,
                "coverage": float(len(retained) / len(frame)),
                "positive_event_coverage": (
                    float(retained_events / total_events) if total_events else np.nan
                ),
                "accepted_n": int(len(retained)), "positive_events": retained_events,
            }
            if retained["target"].nunique() < 2:
                records.append({**base, "status": "suppressed_single_class"})
            else:
                records.append({
                    **base, "status": "estimated",
                    **binary_metrics(
                        retained["target"].to_numpy(dtype=int),
                        retained["probability_calibrated"].to_numpy(dtype=float),
                        threshold=0.5,
                    ),
                })
    return pd.DataFrame(records)


def generate_missing_mask(
    n_rows: int,
    n_features: int,
    *,
    severity: float,
    mechanism: str,
    seed: int,
) -> np.ndarray:
    """Create a deterministic mask while retaining at least one feature per row."""

    if mechanism not in MECHANISMS:
        raise ValueError(f"Unknown missingness mechanism: {mechanism}")
    if not 0.0 <= severity < 1.0:
        raise ValueError("Missingness severity must be in [0, 1)")
    rng = np.random.default_rng(int(seed))
    if severity == 0.0:
        return np.zeros((n_rows, n_features), dtype=bool)
    if mechanism == "mcar_independent":
        mask = rng.random((n_rows, n_features)) < severity
        fully_masked = np.flatnonzero(mask.all(axis=1))
        if len(fully_masked):
            retained = rng.integers(0, n_features, size=len(fully_masked))
            mask[fully_masked, retained] = False
        return mask
    masked_features = min(n_features - 1, max(1, int(round(severity * n_features))))
    columns = rng.choice(n_features, size=masked_features, replace=False)
    mask = np.zeros((n_rows, n_features), dtype=bool)
    mask[:, columns] = True
    return mask


def _supported_panel(frame: pd.DataFrame, scenarios: dict[str, list[str]]) -> np.ndarray:
    supported = np.zeros(len(frame), dtype=bool)
    for features in scenarios.values():
        supported |= frame[features].notna().all(axis=1).to_numpy()
    return supported


def _summarize(metrics: pd.DataFrame) -> pd.DataFrame:
    records = []
    keys = ["model", "mechanism", "severity"]
    for values, frame in metrics.groupby(keys, sort=True):
        model, mechanism, severity = values
        row = {
            "model": model,
            "mechanism": mechanism,
            "severity": float(severity),
            "evaluation_units": len(frame),
            "mean_actual_missing_fraction": float(frame["actual_missing_fraction"].mean()),
            "mean_supported_panel_coverage": float(frame["supported_panel_coverage"].mean()),
        }
        for metric in STRESS_METRICS:
            values_array = frame[metric].dropna().to_numpy(dtype=float)
            mean = float(np.mean(values_array))
            if len(values_array) > 1:
                sem = float(np.std(values_array, ddof=1) / np.sqrt(len(values_array)))
                margin = float(t.ppf(0.975, len(values_array) - 1) * sem)
            else:
                margin = float("nan")
            row[f"{metric}_mean"] = mean
            row[f"{metric}_ci_lower"] = mean - margin
            row[f"{metric}_ci_upper"] = mean + margin
        records.append(row)
    return pd.DataFrame(records)


def _render_report(metadata: dict, summary: pd.DataFrame) -> str:
    lines = [
        "# Missingness Stress Development Analysis",
        "",
        f"**Dataset:** `{metadata['dataset']}`",
        "",
        f"**Profile:** `{metadata['profile']}`",
        "",
        "MCAR-like masks remove features independently. Structured-block masks "
        "remove the same correlated feature subset for every participant in a "
        "replicate. Neither mechanism is presented as real-world MNAR validation.",
        "",
        "| Model | Mechanism | Severity | Brier mean | AP mean | Supported-panel coverage |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, row in summary.sort_values(["model", "mechanism", "severity"]).iterrows():
        lines.append(
            f"| {row['model']} | {row['mechanism']} | {row['severity']:.2f} | "
            f"{row['brier_score_mean']:.4f} | {row['average_precision_mean']:.4f} | "
            f"{row['mean_supported_panel_coverage']:.3f} |"
        )
    lines.extend(["", "Development evidence only; final outcomes were not accessed.", ""])
    return "\n".join(lines)


def run_missingness_stress(
    study_dir: Path | str,
    *,
    models: Sequence[str] = ("random_forest", "xgboost"),
    severities: Sequence[float] = (0.0, 0.25, 0.50, 0.75),
    replicates: int = 5,
) -> MissingnessStressResult:
    """Apply shared masks to held-out outer-fold participants and saved bundles."""

    study_dir = Path(study_dir).resolve()
    study_metadata = json.loads((study_dir / "experiment_metadata.json").read_text())
    profile = dict(study_metadata["profile"])
    if str(profile.get("name")) == "final" or bool(profile.get("locked", False)):
        raise PermissionError("Missingness stress experiments are development-only")
    if str(study_metadata.get("runner", "nested_cv")) != "nested_cv":
        raise NotImplementedError("Missingness stress currently supports nested-CV studies")
    if replicates < 1:
        raise ValueError("replicates must be positive")
    dataset_name = str(study_metadata["dataset"])
    dataset = load_dataset(dataset_name)
    features = list(dataset.X.columns)
    routing_cfg = _read_routing_config(dataset_name)
    scenarios = {
        name: list(definition["available_features"])
        for name, definition in routing_cfg["scenarios"].items()
    }
    manifest = pd.read_csv(study_metadata["split_manifest"], low_memory=False)
    outer_splits = _selected_outer_splits(manifest, profile)
    records = []
    prediction_frames = []
    for repeat, outer_fold in outer_splits:
        validation_manifest = manifest[
            (manifest["repeat"] == repeat)
            & (manifest["outer_fold"] == outer_fold)
            & (manifest["role"] == "validation")
        ].copy()
        positions = validation_manifest["row_position"].to_numpy(dtype=int)
        X_validation = dataset.X.iloc[positions].reset_index(drop=True)
        y_validation = dataset.y.iloc[positions].to_numpy(dtype=int)
        for mechanism_index, mechanism in enumerate(MECHANISMS):
            for severity_index, severity in enumerate(severities):
                replicate_count = 1 if float(severity) == 0.0 else int(replicates)
                for replicate in range(replicate_count):
                    mask_seed = (
                        int(profile["seed"]) + repeat * 100_000 + outer_fold * 10_000
                        + mechanism_index * 1_000 + severity_index * 100 + replicate
                    )
                    mask = generate_missing_mask(
                        len(X_validation), len(features), severity=float(severity),
                        mechanism=mechanism, seed=mask_seed,
                    )
                    masked = X_validation.mask(mask)
                    supported = _supported_panel(masked, scenarios)
                    actual_missing = float(masked.isna().to_numpy().mean())
                    for model_name in models:
                        bundle_path = study_dir / "models" / f"{model_name}_repeat_{repeat}_fold_{outer_fold}.joblib"
                        if not bundle_path.exists():
                            raise FileNotFoundError(f"Required model bundle is missing: {bundle_path}")
                        predicted = predict_bundle(joblib.load(bundle_path), masked)
                        metric = binary_metrics(y_validation, predicted["probability_calibrated"], threshold=0.5)
                        records.append({
                            "dataset": dataset_name, "model": model_name,
                            "repeat": repeat, "outer_fold": outer_fold,
                            "mechanism": mechanism, "severity": float(severity),
                            "mask_replicate": replicate, "mask_seed": mask_seed,
                            "actual_missing_fraction": actual_missing,
                            "supported_panel_coverage": float(np.mean(supported)), **metric,
                        })
                        prediction_frames.append(pd.DataFrame({
                            "dataset": dataset_name, "model": model_name,
                            "repeat": repeat, "outer_fold": outer_fold,
                            "mechanism": mechanism, "severity": float(severity),
                            "mask_replicate": replicate,
                            "row_id": validation_manifest["row_id"].to_numpy(),
                            "group_id": validation_manifest["group_id"].to_numpy(),
                            "target": y_validation, "supported_named_panel": supported,
                            "probability_raw": predicted["probability_raw"],
                            "probability_calibrated": predicted["probability_calibrated"],
                        }))
    metrics = pd.DataFrame(records)
    stress_predictions = pd.concat(prediction_frames, ignore_index=True)
    summary = _summarize(metrics)
    guard_ablation = applicability_guard_ablation(stress_predictions)
    output_dir = study_dir / "missingness_stress"
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": "1.0", "dataset": dataset_name,
        "source_study": str(study_dir), "profile": str(profile["name"]),
        "models": list(models), "mechanisms": list(MECHANISMS),
        "severities": [float(value) for value in severities], "replicates": int(replicates),
        "shared_masks_across_models": True, "fold_local_saved_preprocessors": True,
        "real_world_mnar_claim": False, "source_tree_sha256": source_tree_sha256(),
        "final_outcome_access_authorized": False,
    }
    metrics_path = output_dir / "fold_replicate_metrics.csv"
    summary_path = output_dir / "summary_metrics.csv"
    predictions_path = output_dir / "stress_predictions.csv"
    guard_path = output_dir / "applicability_guard_ablation.csv"
    metadata_path = output_dir / "metadata.json"
    report_path = output_dir / "Missingness_Stress_Analysis.md"
    metrics.to_csv(metrics_path, index=False)
    summary.to_csv(summary_path, index=False)
    stress_predictions.to_csv(predictions_path, index=False)
    guard_ablation.to_csv(guard_path, index=False)
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True))
    report_path.write_text(_render_report(metadata, summary))
    return MissingnessStressResult(study_dir, output_dir, metrics_path, summary_path, report_path)
