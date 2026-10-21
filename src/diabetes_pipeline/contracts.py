"""Shared typed contracts for datasets and transformed artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class LoadedDataset:
    """A validated modelling dataset with stable identity and grouping metadata."""

    name: str
    X: pd.DataFrame
    y: pd.Series
    row_ids: pd.Series
    groups: pd.Series | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        lengths = {len(self.X), len(self.y), len(self.row_ids)}
        if self.groups is not None:
            lengths.add(len(self.groups))
        if len(lengths) != 1:
            raise ValueError("X, y, row_ids, and groups must have identical lengths")
        if not self.X.index.equals(self.y.index) or not self.X.index.equals(self.row_ids.index):
            raise ValueError("X, y, and row_ids must use aligned indexes")
        if self.groups is not None and not self.X.index.equals(self.groups.index):
            raise ValueError("groups must use the same index as X")

