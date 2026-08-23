from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from diabetes_pipeline.artifacts.bundles import load_bundle, predict_bundle
from diabetes_pipeline.calibration.calibrators import fit_calibrator
from diabetes_pipeline.models.registry import build_estimator
from diabetes_pipeline.preprocessing.builders import build_preprocessor


class ArtifactReloadTests(unittest.TestCase):
    def test_round_trip_preserves_probabilities(self) -> None:
        X = pd.DataFrame({"a": [0.0, 1.0, 2.0, 3.0], "b": [1.0, np.nan, 0.0, 2.0]})
        y = np.array([0, 0, 1, 1])
        config = {"numeric_features": ["a", "b"], "categorical_features": []}
        preprocessor = build_preprocessor(config, "logistic_regression")
        transformed = preprocessor.fit_transform(X)
        model = build_estimator(
            "logistic_regression", {"C": 1.0, "l1_ratio": 0.0}, seed=42
        )
        model.fit(transformed, y)
        raw = model.predict_proba(transformed)
        calibrator = fit_calibrator("sigmoid", raw, y)
        bundle = {
            "dataset": "synthetic",
            "task": "test",
            "endpoint": "test",
            "model_name": "logistic_regression",
            "preprocessor": preprocessor,
            "model": model,
            "calibrator": calibrator,
            "threshold": 0.5,
        }
        expected = predict_bundle(bundle, X)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bundle.joblib"
            joblib.dump(bundle, path)
            reloaded = load_bundle(path)
            actual = predict_bundle(reloaded, X)
        np.testing.assert_allclose(
            expected["probability_calibrated"], actual["probability_calibrated"]
        )


if __name__ == "__main__":
    unittest.main()

