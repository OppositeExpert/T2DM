"""Clearly non-deployable demonstrations of preprocessing and split leakage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.evaluation.metrics import binary_metrics
from diabetes_pipeline.models.registry import build_estimator
from diabetes_pipeline.preprocessing.builders import build_preprocessor
from diabetes_pipeline.settings import get_dataset_config, source_tree_sha256
from diabetes_pipeline.training.tuning import inner_splits, positive_class_weight


@dataclass(frozen=True)
class LeakageDemonstrationResult:
    output_dir: Path
    predictions_path: Path
    summary_path: Path
    report_path: Path


def _cross_validated_probabilities(
    X: pd.DataFrame,
    y: np.ndarray,
    dataset_cfg: dict,
    *,
    model_name: str,
    groups: np.ndarray | None,
    diagnostic_groups: np.ndarray | None = None,
    global_preprocessing: bool,
    seed: int,
    n_splits: int,
) -> tuple[np.ndarray, list[dict[str, int]]]:
    splits = list(inner_splits(y, n_splits=n_splits, seed=seed, groups=groups))
    probabilities = np.full(len(y), np.nan)
    leakage_records = []
    globally_transformed = None
    if global_preprocessing:
        global_preprocessor = build_preprocessor(dataset_cfg, model_name)
        globally_transformed = global_preprocessor.fit_transform(X)
    for fold, (training, validation) in enumerate(splits):
        if globally_transformed is None:
            preprocessor = build_preprocessor(dataset_cfg, model_name)
            transformed_training = preprocessor.fit_transform(X.iloc[training])
            transformed_validation = preprocessor.transform(X.iloc[validation])
        else:
            transformed_training = globally_transformed[training]
            transformed_validation = globally_transformed[validation]
        model = build_estimator(
            model_name,
            {},
            seed=seed + fold,
            n_jobs=1,
            positive_class_weight=positive_class_weight(y[training]),
        )
        model.fit(transformed_training, y[training])
        probabilities[validation] = model.predict_proba(transformed_validation)
        overlap = 0
        if diagnostic_groups is not None:
            overlap = len(
                set(diagnostic_groups[training]) & set(diagnostic_groups[validation])
            )
        leakage_records.append(
            {"fold": fold, "train_n": len(training), "validation_n": len(validation),
             "group_overlap": overlap}
        )
    if np.isnan(probabilities).any():
        raise RuntimeError("Leakage demonstration did not predict every row")
    return probabilities, leakage_records


def _render_report(dataset_name: str, summary: pd.DataFrame) -> str:
    lines = [
        "# Non-Deployable Leakage Demonstrations",
        "",
        f"**Dataset:** `{dataset_name}`",
        "",
        "These variants exist only to quantify evaluation bias. Global preprocessing "
        "uses validation distributions during transformation. Naive Sylhet splitting "
        "allows identical feature profiles to cross folds. Neither variant is eligible "
        "for model selection, deployment, or final evidence.",
        "",
        "| Variant | Deployable | AUROC | AP | Brier | Group overlap |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['variant']} | {bool(row['deployable'])} | "
            f"{row['auroc']:.4f} | {row['average_precision']:.4f} | "
            f"{row['brier_score']:.4f} | {int(row['total_group_overlap'])} |"
        )
    lines.extend(["", "Only the fold-local grouped variant is scientifically valid for Sylhet.", ""])
    return "\n".join(lines)


def run_leakage_demonstrations(
    dataset_name: str,
    *,
    model_name: str = "logistic_regression",
    seed: int = 42,
    n_splits: int = 5,
) -> LeakageDemonstrationResult:
    """Run development-only invalid-versus-valid evaluation demonstrations."""

    if dataset_name not in {"pidd", "sylhet"}:
        raise ValueError("Leakage demonstrations are prespecified for pidd and sylhet")
    dataset = load_dataset(dataset_name)
    dataset_cfg = get_dataset_config(dataset_name)
    y = dataset.y.to_numpy(dtype=int)
    grouped = dataset.groups.to_numpy() if dataset.groups is not None else None
    variants = [
        ("fold_local_valid", grouped, False, True),
        ("global_preprocessing_invalid", grouped, True, False),
    ]
    if grouped is not None:
        variants.extend(
            [
                ("naive_row_split_invalid", None, False, False),
                ("global_and_naive_invalid", None, True, False),
            ]
        )
    prediction_frames = []
    summary_records = []
    split_records = []
    for variant, groups, global_preprocessing, deployable in variants:
        probability, fold_records = _cross_validated_probabilities(
            dataset.X,
            y,
            dataset_cfg,
            model_name=model_name,
            groups=groups,
            diagnostic_groups=grouped,
            global_preprocessing=global_preprocessing,
            seed=seed,
            n_splits=n_splits,
        )
        metrics = binary_metrics(y, probability, threshold=0.5)
        summary_records.append(
            {
                "dataset": dataset_name,
                "model": model_name,
                "variant": variant,
                "deployable": deployable,
                "global_preprocessing": global_preprocessing,
                "grouped_split": groups is not None,
                "total_group_overlap": sum(row["group_overlap"] for row in fold_records),
                **metrics,
            }
        )
        for row in fold_records:
            split_records.append({"variant": variant, **row})
        prediction_frames.append(
            pd.DataFrame(
                {
                    "dataset": dataset_name,
                    "model": model_name,
                    "variant": variant,
                    "row_id": dataset.row_ids.astype(str).to_numpy(),
                    "group_id": (
                        dataset.groups.astype(str).to_numpy()
                        if dataset.groups is not None
                        else ""
                    ),
                    "target": y,
                    "probability": probability,
                }
            )
        )
    summary = pd.DataFrame(summary_records)
    output_dir = Path("outputs/publication_pipeline/leakage_demonstrations") / dataset_name
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions_path = output_dir / "predictions.csv"
    summary_path = output_dir / "summary_metrics.csv"
    split_path = output_dir / "split_diagnostics.csv"
    metadata_path = output_dir / "metadata.json"
    report_path = output_dir / "Leakage_Demonstration.md"
    pd.concat(prediction_frames, ignore_index=True).to_csv(predictions_path, index=False)
    summary.to_csv(summary_path, index=False)
    pd.DataFrame(split_records).to_csv(split_path, index=False)
    metadata_path.write_text(
        json.dumps(
            {
                "dataset": dataset_name,
                "model": model_name,
                "seed": seed,
                "n_splits": n_splits,
                "non_deployable_demonstration": True,
                "final_outcome_access_authorized": False,
                "source_tree_sha256": source_tree_sha256(),
            },
            indent=2,
            sort_keys=True,
        )
    )
    report_path.write_text(_render_report(dataset_name, summary))
    return LeakageDemonstrationResult(output_dir, predictions_path, summary_path, report_path)
