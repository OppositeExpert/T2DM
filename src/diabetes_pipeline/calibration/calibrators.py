"""Calibrators fitted only from development out-of-fold probabilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.special import logit
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold


EPSILON = 1e-6


def _clip(probability: np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(probability, dtype=float), EPSILON, 1.0 - EPSILON)


@dataclass
class IdentityCalibrator:
    method: str = "identity"

    def predict(self, probability: np.ndarray) -> np.ndarray:
        return _clip(probability)


@dataclass
class SigmoidCalibrator:
    model: LogisticRegression
    method: str = "sigmoid"

    def predict(self, probability: np.ndarray) -> np.ndarray:
        logits = logit(_clip(probability)).reshape(-1, 1)
        return _clip(self.model.predict_proba(logits)[:, 1])


@dataclass
class IsotonicCalibrator:
    model: IsotonicRegression
    method: str = "isotonic"

    def predict(self, probability: np.ndarray) -> np.ndarray:
        return _clip(self.model.predict(_clip(probability)))


@dataclass(frozen=True)
class CalibrationSelection:
    """A calibration choice made without using the outer validation fold."""

    method: str
    calibrator: Any
    cross_fitted_probability: np.ndarray
    scores: list[dict[str, Any]]


def fit_calibrator(method: str, probability: np.ndarray, y: np.ndarray) -> Any:
    probability = _clip(probability)
    y = np.asarray(y, dtype=int)
    if method == "identity":
        return IdentityCalibrator()
    if method == "sigmoid":
        model = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=2_000)
        model.fit(logit(probability).reshape(-1, 1), y)
        return SigmoidCalibrator(model=model)
    if method == "isotonic":
        model = IsotonicRegression(out_of_bounds="clip")
        model.fit(probability, y)
        return IsotonicCalibrator(model=model)
    raise ValueError(f"Unknown calibration method '{method}'")


def select_calibrator(
    methods: list[str],
    probability: np.ndarray,
    y: np.ndarray,
    *,
    n_splits: int = 5,
    seed: int = 42,
    groups: np.ndarray | None = None,
    minimum_samples_by_method: dict[str, int] | None = None,
) -> CalibrationSelection:
    """Select a calibrator by cross-fitted Brier score, then log loss.

    ``probability`` must itself be generated out of fold by the base model. Each
    candidate calibrator is evaluated with a second, deterministic cross-fitting
    layer so that calibration selection cannot benefit from fitting and scoring
    on the same observations.
    """

    probability = _clip(probability)
    y = np.asarray(y, dtype=int)
    methods = list(dict.fromkeys(methods))
    if not methods:
        raise ValueError("At least one calibration method is required")
    unknown = sorted(set(methods) - {"identity", "sigmoid", "isotonic"})
    if unknown:
        raise ValueError(f"Unknown calibration methods: {unknown}")
    minimum_samples_by_method = dict(minimum_samples_by_method or {})
    unknown_minimums = sorted(
        set(minimum_samples_by_method) - {"identity", "sigmoid", "isotonic"}
    )
    if unknown_minimums:
        raise ValueError(
            f"Minimum samples configured for unknown methods: {unknown_minimums}"
        )

    class_counts = np.bincount(y, minlength=2)
    effective_splits = min(int(n_splits), int(class_counts.min()))
    if effective_splits < 2:
        raise ValueError("Calibration selection requires at least two samples per class")
    splitter = (
        StratifiedGroupKFold(
            n_splits=effective_splits,
            shuffle=True,
            random_state=int(seed),
        )
        if groups is not None
        else StratifiedKFold(
            n_splits=effective_splits,
            shuffle=True,
            random_state=int(seed),
        )
    )

    candidate_probabilities: dict[str, np.ndarray] = {}
    scores: list[dict[str, Any]] = []
    for method in methods:
        minimum_samples = int(minimum_samples_by_method.get(method, 0))
        if len(y) < minimum_samples:
            scores.append(
                {
                    "method": method,
                    "eligible": False,
                    "eligibility_reason": (
                        f"requires_at_least_{minimum_samples}_calibration_samples"
                    ),
                    "minimum_samples": minimum_samples,
                    "available_samples": len(y),
                    "brier_score": float("nan"),
                    "log_loss": float("nan"),
                }
            )
            continue
        cross_fitted = np.empty(len(y), dtype=float)
        for training_index, validation_index in splitter.split(probability, y, groups):
            calibrator = fit_calibrator(
                method,
                probability[training_index],
                y[training_index],
            )
            cross_fitted[validation_index] = calibrator.predict(
                probability[validation_index]
            )
        cross_fitted = _clip(cross_fitted)
        candidate_probabilities[method] = cross_fitted
        scores.append(
            {
                "method": method,
                "eligible": True,
                "eligibility_reason": "eligible",
                "minimum_samples": minimum_samples,
                "available_samples": len(y),
                "brier_score": float(brier_score_loss(y, cross_fitted)),
                "log_loss": float(log_loss(y, cross_fitted, labels=[0, 1])),
            }
        )

    method_order = {method: position for position, method in enumerate(methods)}
    eligible_scores = [row for row in scores if bool(row["eligible"])]
    if not eligible_scores:
        raise ValueError("No calibration method meets its eligibility requirements")
    selected_score = min(
        eligible_scores,
        key=lambda row: (
            float(row["brier_score"]),
            float(row["log_loss"]),
            method_order[str(row["method"])],
        ),
    )
    selected_method = str(selected_score["method"])
    return CalibrationSelection(
        method=selected_method,
        calibrator=fit_calibrator(selected_method, probability, y),
        cross_fitted_probability=candidate_probabilities[selected_method],
        scores=scores,
    )
