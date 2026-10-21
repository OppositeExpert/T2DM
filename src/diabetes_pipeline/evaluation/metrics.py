"""First-pass discrimination, calibration, and threshold metrics."""

from __future__ import annotations

import warnings

import numpy as np
from scipy.special import logit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)


EPSILON = 1e-6


def _safe_divide(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def expected_calibration_error(
    y: np.ndarray, probability: np.ndarray, n_bins: int = 10
) -> float:
    order = np.argsort(probability)
    bins = np.array_split(order, min(n_bins, len(order)))
    error = 0.0
    for indexes in bins:
        if len(indexes):
            error += (len(indexes) / len(y)) * abs(
                float(np.mean(y[indexes])) - float(np.mean(probability[indexes]))
            )
    return float(error)


def calibration_intercept_slope(
    y: np.ndarray, probability: np.ndarray
) -> tuple[float, float]:
    clipped = np.clip(probability, EPSILON, 1.0 - EPSILON)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            model = LogisticRegression(C=np.inf, solver="lbfgs", max_iter=2_000)
            model.fit(logit(clipped).reshape(-1, 1), y)
            return float(model.intercept_[0]), float(model.coef_[0, 0])
        except Exception:
            return float("nan"), float("nan")


def binary_metrics(
    y: np.ndarray,
    probability: np.ndarray,
    *,
    threshold: float | np.ndarray = 0.5,
) -> dict[str, float | int]:
    y = np.asarray(y, dtype=int)
    probability = np.clip(np.asarray(probability, dtype=float), EPSILON, 1.0 - EPSILON)
    threshold_array = np.asarray(threshold, dtype=float)
    if threshold_array.ndim and threshold_array.shape != probability.shape:
        raise ValueError("Row-specific thresholds must match the probability shape")
    prediction = (probability >= threshold_array).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, prediction, labels=[0, 1]).ravel()
    prevalence = float(np.mean(y))
    prevalence_brier = prevalence * (1.0 - prevalence)
    brier = float(brier_score_loss(y, probability))
    calibration_intercept, calibration_slope = calibration_intercept_slope(y, probability)
    sensitivity = float(recall_score(y, prediction, zero_division=0))
    specificity = _safe_divide(tn, tn + fp)
    false_positive_rate = _safe_divide(fp, fp + tn)
    false_negative_rate = _safe_divide(fn, fn + tp)
    positive_likelihood_ratio = _safe_divide(sensitivity, false_positive_rate)
    negative_likelihood_ratio = _safe_divide(false_negative_rate, specificity)
    return {
        "n": int(len(y)),
        "positives": int(np.sum(y)),
        "prevalence": prevalence,
        "threshold": (
            float(threshold_array)
            if threshold_array.ndim == 0
            else float("nan")
        ),
        "auroc": float(roc_auc_score(y, probability)),
        "average_precision": float(average_precision_score(y, probability)),
        "brier_score": brier,
        "scaled_brier_score": float(1.0 - brier / prevalence_brier) if prevalence_brier else float("nan"),
        "log_loss": float(log_loss(y, probability, labels=[0, 1])),
        "calibration_intercept": calibration_intercept,
        "calibration_slope": calibration_slope,
        "observed_expected_ratio": _safe_divide(float(np.sum(y)), float(np.sum(probability))),
        "expected_calibration_error": expected_calibration_error(y, probability),
        "accuracy": float(accuracy_score(y, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "sensitivity": sensitivity,
        "specificity": specificity,
        "false_positive_rate": false_positive_rate,
        "false_negative_rate": false_negative_rate,
        "ppv": float(precision_score(y, prediction, zero_division=0)),
        "npv": _safe_divide(tn, tn + fn),
        "f1": float(f1_score(y, prediction, zero_division=0)),
        "mcc": float(matthews_corrcoef(y, prediction)),
        "youden_index": sensitivity + specificity - 1.0,
        "positive_likelihood_ratio": positive_likelihood_ratio,
        "negative_likelihood_ratio": negative_likelihood_ratio,
        "diagnostic_odds_ratio": _safe_divide(
            positive_likelihood_ratio, negative_likelihood_ratio
        ),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }
