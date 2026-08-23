"""Persist and validate immutable split manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.settings import (
    DEFAULT_OUTPUT_ROOT,
    configuration_sha256,
    get_dataset_config,
)
from diabetes_pipeline.splitting.strategies import build_split_manifest


def _frame_sha256(frame: pd.DataFrame) -> str:
    csv_bytes = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def _partition_summary(frame: pd.DataFrame) -> list[dict[str, Any]]:
    keys = ["repeat", "outer_fold", "role"]
    summary = (
        frame.groupby(keys, dropna=False)
        .agg(rows=("row_id", "size"), positives=("target", "sum"), groups=("group_id", "nunique"))
        .reset_index()
    )
    summary["prevalence"] = summary["positives"] / summary["rows"]
    if not frame["group_id"].astype(str).str.len().gt(0).any():
        summary["groups"] = None
    return summary.to_dict(orient="records")


def validate_split_manifest(
    dataset: LoadedDataset,
    manifest: pd.DataFrame,
    cfg: dict[str, Any],
) -> None:
    strategy = cfg["evaluation_strategy"]
    if strategy in {"stratified_holdout_cv", "stratified_group_holdout_cv"}:
        if len(manifest) != len(dataset.X):
            raise ValueError(f"{dataset.name}: holdout manifest must contain one row per record")
        if set(manifest["role"]) != {"development", "test"}:
            raise ValueError(f"{dataset.name}: holdout manifest has unexpected roles")
        if manifest.loc[manifest["role"] == "development", "outer_fold"].lt(0).any():
            raise ValueError(f"{dataset.name}: development rows are missing CV fold assignments")
        if manifest.loc[manifest["role"] == "test", "outer_fold"].ne(-1).any():
            raise ValueError(f"{dataset.name}: test rows must not have development CV assignments")
        if dataset.groups is not None:
            development_groups = set(manifest.loc[manifest["role"] == "development", "group_id"])
            test_groups = set(manifest.loc[manifest["role"] == "test", "group_id"])
            if development_groups & test_groups:
                raise ValueError(f"{dataset.name}: groups overlap between development and test")
            for fold in sorted(manifest.loc[manifest["role"] == "development", "outer_fold"].unique()):
                validation_groups = set(
                    manifest.loc[
                        (manifest["role"] == "development") & (manifest["outer_fold"] == fold),
                        "group_id",
                    ]
                )
                other_groups = set(
                    manifest.loc[
                        (manifest["role"] == "development") & (manifest["outer_fold"] != fold),
                        "group_id",
                    ]
                )
                if validation_groups & other_groups:
                    raise ValueError(f"{dataset.name}: group overlap in development fold {fold}")
        return

    repeats = int(cfg["repeats"])
    outer_folds = int(cfg["outer_folds"])
    expected_rows = len(dataset.X) * repeats * outer_folds
    if len(manifest) != expected_rows:
        raise ValueError(
            f"{dataset.name}: expected {expected_rows} repeated-CV rows, found {len(manifest)}"
        )
    for repeat in range(repeats):
        repeat_frame = manifest[manifest["repeat"] == repeat]
        validation_counts = (
            repeat_frame[repeat_frame["role"] == "validation"].groupby("row_id").size()
        )
        if len(validation_counts) != len(dataset.X) or not validation_counts.eq(1).all():
            raise ValueError(f"{dataset.name}: each row must be validation once per repeat")
        if dataset.groups is not None:
            for fold in range(outer_folds):
                fold_frame = repeat_frame[repeat_frame["outer_fold"] == fold]
                training_groups = set(fold_frame.loc[fold_frame["role"] == "train", "group_id"])
                validation_groups = set(
                    fold_frame.loc[fold_frame["role"] == "validation", "group_id"]
                )
                if training_groups & validation_groups:
                    raise ValueError(
                        f"{dataset.name}: group overlap at repeat {repeat}, fold {fold}"
                    )


def create_and_write_split_manifest(
    dataset: LoadedDataset,
    seed: int = 42,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> tuple[Path, Path, pd.DataFrame]:
    cfg = get_dataset_config(dataset.name)
    manifest = build_split_manifest(dataset, cfg, seed=seed)
    validate_split_manifest(dataset, manifest, cfg)

    config_hash = configuration_sha256(cfg)
    output_dir = output_root / "splits" / dataset.name / config_hash[:12]
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"splits_seed_{seed}.csv"
    metadata_path = output_dir / f"splits_seed_{seed}.json"
    manifest.to_csv(csv_path, index=False)

    metadata = {
        "dataset": dataset.name,
        "strategy": cfg["evaluation_strategy"],
        "seed": seed,
        "configuration_sha256": config_hash,
        "manifest_rows": len(manifest),
        "manifest_sha256": _frame_sha256(manifest),
        "partitions": _partition_summary(manifest),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    return csv_path, metadata_path, manifest
