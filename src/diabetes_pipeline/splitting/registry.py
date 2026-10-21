"""Persist and validate immutable split manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd
import numpy as np

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
    required = {"dataset", "strategy", "row_position", "row_id", "group_id",
                "target", "role", "repeat", "outer_fold"}
    if required - set(manifest):
        raise ValueError(f"{dataset.name}: incomplete split identity contract")
    if manifest.empty or not manifest["dataset"].eq(dataset.name).all():
        raise ValueError(f"{dataset.name}: split dataset identity mismatch")
    if not manifest["strategy"].eq(strategy).all():
        raise ValueError(f"{dataset.name}: split strategy mismatch")
    numeric_positions = pd.to_numeric(manifest["row_position"], errors="coerce")
    if (numeric_positions.isna().any() or
            not numeric_positions.between(0, len(dataset.X) - 1).all() or
            not numeric_positions.eq(np.floor(numeric_positions)).all()):
        raise ValueError(f"{dataset.name}: invalid row positions")
    positions = numeric_positions.to_numpy(dtype=int)
    for column, expected in (
        ("row_id", dataset.row_ids.iloc[positions].astype(str).to_numpy()),
        ("target", dataset.y.iloc[positions].to_numpy()),
        ("group_id", dataset.groups.iloc[positions].astype(str).to_numpy()
         if dataset.groups is not None else np.full(len(manifest), "")),
    ):
        actual = (manifest[column].fillna("").astype(str).to_numpy()
                  if column != "target" else manifest[column].to_numpy())
        if not np.array_equal(actual, expected):
            raise ValueError(f"{dataset.name}: {column} does not match row positions")
    if manifest.duplicated(["repeat", "outer_fold", "row_position"]).any():
        raise ValueError(f"{dataset.name}: duplicate row within a split")
    if strategy in {"stratified_holdout_cv", "stratified_group_holdout_cv"}:
        if manifest["row_position"].duplicated().any() or set(positions) != set(range(len(dataset.X))):
            raise ValueError(f"{dataset.name}: holdout positions must cover each record once")
        if set(manifest["repeat"]) != {0} or set(manifest.loc[manifest["role"] == "development", "outer_fold"]) != set(range(int(cfg["cv_folds"]))):
            raise ValueError(f"{dataset.name}: incomplete development folds")
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
    if (set(manifest["role"]) != {"train", "validation"} or
            set(manifest["repeat"]) != set(range(repeats)) or
            set(manifest["outer_fold"]) != set(range(outer_folds))):
        raise ValueError(f"{dataset.name}: invalid repeated-CV roles or folds")
    for _, frame in manifest.groupby(["repeat", "outer_fold"]):
        if (len(frame) != len(dataset.X) or
                set(frame["row_position"]) != set(range(len(dataset.X))) or
                set(frame["role"]) != {"train", "validation"}):
            raise ValueError(f"{dataset.name}: incomplete or overlapping outer split")
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
    payload = manifest.to_csv(index=False, lineterminator="\n")
    if csv_path.exists() and csv_path.read_text(encoding="utf-8") != payload:
        raise RuntimeError("Existing split manifest differs; overwrite is prohibited")

    metadata = {
        "dataset": dataset.name,
        "strategy": cfg["evaluation_strategy"],
        "seed": seed,
        "configuration_sha256": config_hash,
        "manifest_rows": len(manifest),
        "manifest_sha256": _frame_sha256(manifest),
        "partitions": _partition_summary(manifest),
    }
    if metadata_path.exists():
        if json.loads(metadata_path.read_text(encoding="utf-8")) != metadata:
            raise RuntimeError("Existing split metadata differs; overwrite is prohibited")
    if not csv_path.exists():
        with csv_path.open("x", encoding="utf-8") as handle:
            handle.write(payload)
    if not metadata_path.exists():
        with metadata_path.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(metadata, indent=2, sort_keys=True))
    return csv_path, metadata_path, manifest
