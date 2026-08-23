"""Decision-curve analysis for evaluating potential clinical utility."""

from __future__ import annotations

import numpy as np
import pandas as pd


def decision_curve(
    y: np.ndarray,
    probability: np.ndarray,
    *,
    thresholds: np.ndarray | None = None,
) -> pd.DataFrame:
    """Calculate model, treat-all, and treat-none net benefit."""

    y = np.asarray(y, dtype=int)
    probability = np.asarray(probability, dtype=float)
    if thresholds is None:
        thresholds = np.linspace(0.01, 0.80, 80)
    thresholds = np.asarray(thresholds, dtype=float)
    if np.any((thresholds <= 0.0) | (thresholds >= 1.0)):
        raise ValueError("Decision thresholds must lie strictly between zero and one")

    sample_count = len(y)
    prevalence = float(np.mean(y))
    records: list[dict[str, float]] = []
    for threshold in thresholds:
        prediction = probability >= threshold
        true_positive = float(np.sum(prediction & (y == 1)))
        false_positive = float(np.sum(prediction & (y == 0)))
        odds = float(threshold / (1.0 - threshold))
        records.append(
            {
                "threshold": float(threshold),
                "model_net_benefit": true_positive / sample_count
                - false_positive / sample_count * odds,
                "treat_all_net_benefit": prevalence - (1.0 - prevalence) * odds,
                "treat_none_net_benefit": 0.0,
            }
        )
    return pd.DataFrame(records)
