"""Validation rules for loaded modelling datasets."""

from __future__ import annotations

from typing import Any

import numpy as np

from diabetes_pipeline.contracts import LoadedDataset


class DatasetValidationError(ValueError):
    """Raised when a dataset violates a publication-pipeline contract."""


def validate_dataset(dataset: LoadedDataset, cfg: dict[str, Any]) -> None:
    if dataset.X.empty:
        raise DatasetValidationError(f"{dataset.name}: no modelling rows")
    if dataset.X.columns.duplicated().any():
        duplicated = dataset.X.columns[dataset.X.columns.duplicated()].tolist()
        raise DatasetValidationError(f"{dataset.name}: duplicate feature names: {duplicated}")
    if cfg["target_name"] in dataset.X.columns:
        raise DatasetValidationError(f"{dataset.name}: target leaked into feature matrix")
    if dataset.row_ids.isna().any() or dataset.row_ids.duplicated().any():
        raise DatasetValidationError(f"{dataset.name}: row IDs must be non-null and unique")

    target_values = set(dataset.y.dropna().unique().tolist())
    if target_values != {0, 1}:
        raise DatasetValidationError(
            f"{dataset.name}: target must contain both binary classes; found {sorted(target_values)}"
        )
    if dataset.y.isna().any():
        raise DatasetValidationError(f"{dataset.name}: target contains missing values")

    expected = cfg["numeric_features"] + cfg["categorical_features"]
    if list(dataset.X.columns) != expected:
        raise DatasetValidationError(
            f"{dataset.name}: feature order differs from contract. "
            f"Expected {expected}, found {list(dataset.X.columns)}"
        )
    non_numeric = [
        column
        for column in cfg["numeric_features"]
        if not np.issubdtype(dataset.X[column].dtype, np.number)
    ]
    if non_numeric:
        raise DatasetValidationError(f"{dataset.name}: configured numeric fields are not numeric: {non_numeric}")

    if cfg.get("group_strategy") not in {None, "none"}:
        if dataset.groups is None:
            raise DatasetValidationError(f"{dataset.name}: grouped evaluation requires group IDs")
        if dataset.groups.isna().any():
            raise DatasetValidationError(f"{dataset.name}: group IDs contain missing values")

