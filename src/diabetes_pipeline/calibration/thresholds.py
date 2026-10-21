"""Threshold policies learned only from development predictions."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_curve


def _youden_threshold(y: np.ndarray, probability: np.ndarray) -> float:
    false_positive_rate, true_positive_rate, thresholds = roc_curve(y, probability)
    finite = np.isfinite(thresholds)
    thresholds = thresholds[finite]
    youden = (true_positive_rate - false_positive_rate)[finite]
    best = np.flatnonzero(np.isclose(youden, np.max(youden), rtol=0.0, atol=1e-12))
    return float(np.max(thresholds[best]))


def _sensitivity_constrained_threshold(
    y: np.ndarray,
    probability: np.ndarray,
    target: float,
) -> float:
    positive_probability = np.asarray(probability, dtype=float)[y == 1]
    if not 0.0 < target <= 1.0:
        raise ValueError("sensitivity_target must be in (0, 1]")
    if not len(positive_probability):
        raise ValueError("Sensitivity-constrained threshold requires positive samples")

    candidates = np.unique(np.concatenate(([0.0], probability, [1.0])))
    sensitivities = np.asarray(
        [np.mean(positive_probability >= threshold) for threshold in candidates]
    )
    valid = candidates[sensitivities >= target]
    if not len(valid):
        return 0.0
    return float(np.max(valid))


def select_thresholds(
    policies: list[str],
    y: np.ndarray,
    probability: np.ndarray,
    *,
    sensitivity_target: float | None = None,
) -> list[dict[str, float | str]]:
    """Return named thresholds selected from cross-fitted development data."""

    y = np.asarray(y, dtype=int)
    probability = np.asarray(probability, dtype=float)
    policies = list(dict.fromkeys(policies))
    unknown = sorted(
        set(policies)
        - {"fixed_0_5", "youden_development", "sensitivity_constrained"}
    )
    if unknown:
        raise ValueError(f"Unknown threshold policies: {unknown}")

    selected: list[dict[str, float | str]] = []
    for policy in policies:
        if policy == "fixed_0_5":
            threshold = 0.5
        elif policy == "youden_development":
            threshold = _youden_threshold(y, probability)
        else:
            if sensitivity_target is None:
                raise ValueError(
                    "sensitivity_target is required for sensitivity_constrained"
                )
            threshold = _sensitivity_constrained_threshold(
                y,
                probability,
                float(sensitivity_target),
            )
        selected.append({"threshold_policy": policy, "threshold": float(threshold)})
    return selected
