"""A small common interface around sklearn-compatible binary classifiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class ModelAdapter:
    name: str
    estimator: Any

    def fit(self, X: Any, y: Any) -> "ModelAdapter":
        self.estimator.fit(X, y)
        return self

    def predict_proba(self, X: Any) -> np.ndarray:
        probabilities = np.asarray(self.estimator.predict_proba(X), dtype=float)
        if probabilities.ndim != 2 or probabilities.shape[1] != 2:
            raise ValueError(
                f"{self.name} returned probability shape {probabilities.shape}; expected (n, 2)"
            )
        classes = np.asarray(self.estimator.classes_)
        positive_locations = np.flatnonzero(classes == 1)
        if len(positive_locations) != 1:
            raise ValueError(f"{self.name} classes do not contain exactly one positive class: {classes}")
        return probabilities[:, int(positive_locations[0])]

    def get_params(self) -> dict[str, Any]:
        return self.estimator.get_params(deep=False)

