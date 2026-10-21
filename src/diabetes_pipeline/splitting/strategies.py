"""Split strategies for large, small, grouped, and repeated evaluations."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import (
    RepeatedStratifiedKFold,
    StratifiedGroupKFold,
    StratifiedKFold,
    train_test_split,
)

from diabetes_pipeline.contracts import LoadedDataset


def _base_rows(dataset: LoadedDataset) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "dataset": dataset.name,
            "row_position": np.arange(len(dataset.X), dtype=int),
            "row_id": dataset.row_ids.to_numpy(),
            "target": dataset.y.to_numpy(dtype=int),
        }
    )
    frame["group_id"] = (
        dataset.groups.astype(str).to_numpy() if dataset.groups is not None else ""
    )
    return frame


def stratified_holdout_cv(
    dataset: LoadedDataset,
    cfg: dict[str, Any],
    seed: int,
) -> pd.DataFrame:
    positions = np.arange(len(dataset.X))
    development, test = train_test_split(
        positions,
        test_size=float(cfg["test_size"]),
        stratify=dataset.y.to_numpy(),
        random_state=seed,
    )
    role = np.full(len(dataset.X), "development", dtype=object)
    role[test] = "test"
    cv_fold = np.full(len(dataset.X), -1, dtype=int)
    splitter = StratifiedKFold(
        n_splits=int(cfg["cv_folds"]), shuffle=True, random_state=seed
    )
    y_dev = dataset.y.iloc[development].to_numpy()
    for fold, (_, validation_relative) in enumerate(splitter.split(development, y_dev)):
        cv_fold[development[validation_relative]] = fold

    manifest = _base_rows(dataset)
    manifest["role"] = role
    manifest["repeat"] = 0
    manifest["outer_fold"] = cv_fold
    manifest["inner_seed"] = seed + np.maximum(cv_fold, 0)
    return manifest


def stratified_group_holdout_cv(
    dataset: LoadedDataset,
    cfg: dict[str, Any],
    seed: int,
) -> pd.DataFrame:
    if dataset.groups is None:
        raise ValueError("Grouped holdout requires group IDs")
    positions = np.arange(len(dataset.X))
    groups = dataset.groups.to_numpy()
    y = dataset.y.to_numpy()

    holdout_splitter = StratifiedGroupKFold(
        n_splits=int(cfg["test_folds"]), shuffle=True, random_state=seed
    )
    development, test = next(holdout_splitter.split(positions, y, groups))
    role = np.full(len(dataset.X), "development", dtype=object)
    role[test] = "test"
    cv_fold = np.full(len(dataset.X), -1, dtype=int)

    cv_splitter = StratifiedGroupKFold(
        n_splits=int(cfg["cv_folds"]), shuffle=True, random_state=seed + 10_000
    )
    for fold, (_, validation_relative) in enumerate(
        cv_splitter.split(development, y[development], groups[development])
    ):
        cv_fold[development[validation_relative]] = fold

    manifest = _base_rows(dataset)
    manifest["role"] = role
    manifest["repeat"] = 0
    manifest["outer_fold"] = cv_fold
    manifest["inner_seed"] = seed + 10_000 + np.maximum(cv_fold, 0)
    return manifest


def repeated_nested_stratified_cv(
    dataset: LoadedDataset,
    cfg: dict[str, Any],
    seed: int,
) -> pd.DataFrame:
    splitter = RepeatedStratifiedKFold(
        n_splits=int(cfg["outer_folds"]),
        n_repeats=int(cfg["repeats"]),
        random_state=seed,
    )
    positions = np.arange(len(dataset.X))
    y = dataset.y.to_numpy()
    base = _base_rows(dataset)
    records: list[pd.DataFrame] = []
    n_folds = int(cfg["outer_folds"])
    for split_index, (train, validation) in enumerate(splitter.split(positions, y)):
        repeat = split_index // n_folds
        outer_fold = split_index % n_folds
        frame = base.copy()
        frame["role"] = "train"
        frame.loc[validation, "role"] = "validation"
        frame["repeat"] = repeat
        frame["outer_fold"] = outer_fold
        frame["inner_seed"] = seed + repeat * 1_000 + outer_fold
        records.append(frame)
    return pd.concat(records, ignore_index=True)


def repeated_nested_stratified_group_cv(
    dataset: LoadedDataset,
    cfg: dict[str, Any],
    seed: int,
) -> pd.DataFrame:
    if dataset.groups is None:
        raise ValueError("Repeated grouped CV requires group IDs")
    positions = np.arange(len(dataset.X))
    y = dataset.y.to_numpy()
    groups = dataset.groups.to_numpy()
    base = _base_rows(dataset)
    records: list[pd.DataFrame] = []

    for repeat in range(int(cfg["repeats"])):
        splitter = StratifiedGroupKFold(
            n_splits=int(cfg["outer_folds"]),
            shuffle=True,
            random_state=seed + repeat,
        )
        for outer_fold, (train, validation) in enumerate(splitter.split(positions, y, groups)):
            frame = base.copy()
            frame["role"] = "train"
            frame.loc[validation, "role"] = "validation"
            frame["repeat"] = repeat
            frame["outer_fold"] = outer_fold
            frame["inner_seed"] = seed + repeat * 1_000 + outer_fold
            records.append(frame)
    return pd.concat(records, ignore_index=True)


STRATEGIES = {
    "stratified_holdout_cv": stratified_holdout_cv,
    "stratified_group_holdout_cv": stratified_group_holdout_cv,
    "repeated_nested_stratified_cv": repeated_nested_stratified_cv,
    "repeated_nested_stratified_group_cv": repeated_nested_stratified_group_cv,
}


def build_split_manifest(
    dataset: LoadedDataset,
    cfg: dict[str, Any],
    seed: int = 42,
) -> pd.DataFrame:
    strategy_name = cfg["evaluation_strategy"]
    try:
        strategy = STRATEGIES[strategy_name]
    except KeyError as exc:
        raise ValueError(f"Unknown evaluation strategy '{strategy_name}'") from exc
    manifest = strategy(dataset, cfg, seed)
    manifest.insert(1, "strategy", strategy_name)
    manifest["seed"] = seed
    return manifest

