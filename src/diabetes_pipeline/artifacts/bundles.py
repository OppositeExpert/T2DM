"""Safe inference contract for serialized benchmark bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


REQUIRED_BUNDLE_KEYS = {
    "dataset",
    "task",
    "endpoint",
    "model_name",
    "preprocessor",
    "model",
    "calibrator",
    "threshold",
}


def load_bundle(path: Path | str) -> dict[str, Any]:
    bundle = joblib.load(path)
    if not isinstance(bundle, dict):
        raise ValueError("Model bundle must be a dictionary")
    missing = sorted(REQUIRED_BUNDLE_KEYS - set(bundle))
    if missing:
        raise ValueError(f"Model bundle is missing required keys: {missing}")
    return bundle


def predict_bundle(bundle: dict[str, Any], X: pd.DataFrame) -> dict[str, np.ndarray]:
    missing_features = sorted(
        set(bundle["preprocessor"].feature_names_in_) - set(X.columns)
    )
    if missing_features:
        raise ValueError(f"Inference input is missing features: {missing_features}")
    ordered = X[list(bundle["preprocessor"].feature_names_in_)]
    transformed = bundle["preprocessor"].transform(ordered)
    raw = bundle["model"].predict_proba(transformed)
    calibrated = bundle["calibrator"].predict(raw)
    threshold = float(bundle["threshold"])
    return {
        "probability_raw": raw,
        "probability_calibrated": calibrated,
        "prediction": (calibrated >= threshold).astype(int),
    }

