from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.calibration.calibrators import IdentityCalibrator
from diabetes_pipeline.models.registry import build_estimator
from diabetes_pipeline.preprocessing.builders import build_preprocessor
from diabetes_pipeline.routing.inference import route_patient
from diabetes_pipeline.training.tuning import (
    cross_fitted_probabilities_by_scenario,
)


DATASET_CONFIG = {
    "numeric_features": ["a", "b"],
    "categorical_features": [],
}


class RoutingTests(unittest.TestCase):
    def test_cross_fitted_scenario_probabilities_cover_every_row(self) -> None:
        rng = np.random.default_rng(42)
        X = pd.DataFrame({"a": rng.normal(size=60), "b": rng.normal(size=60)})
        y = np.array([0, 1] * 30)
        probabilities = cross_fitted_probabilities_by_scenario(
            X,
            y,
            DATASET_CONFIG,
            "logistic_regression",
            {"C": 1.0, "l1_ratio": 0.0, "class_weight": None},
            {"full": ["a", "b"], "a_only": ["a"]},
            n_splits=3,
            seed=42,
        )
        self.assertEqual(set(probabilities), {"full", "a_only"})
        for values in probabilities.values():
            self.assertEqual(values.shape, (60,))
            self.assertTrue(np.isfinite(values).all())

    def test_cross_fitted_routing_masks_integer_columns(self) -> None:
        X = pd.DataFrame(
            {"a": np.arange(60, dtype=int), "b": np.tile([0, 1], 30)}
        )
        y = np.array([0, 1] * 30)
        probabilities = cross_fitted_probabilities_by_scenario(
            X,
            y,
            DATASET_CONFIG,
            "logistic_regression",
            {"C": 1.0, "l1_ratio": 0.0, "class_weight": None},
            {"a_only": ["a"]},
            n_splits=3,
            seed=42,
        )
        self.assertTrue(np.isfinite(probabilities["a_only"]).all())

    def test_patient_router_selects_supported_panel_or_abstains(self) -> None:
        X = pd.DataFrame({"a": [-1.0, -0.5, 0.5, 1.0], "b": [0.0, 1.0, 0.0, 1.0]})
        y = np.array([0, 0, 1, 1])
        preprocessor = build_preprocessor(DATASET_CONFIG, "logistic_regression")
        transformed = preprocessor.fit_transform(X)
        model = build_estimator(
            "logistic_regression",
            {"C": 1.0, "l1_ratio": 0.0, "class_weight": None},
            seed=42,
        )
        model.fit(transformed, y)
        model_bundle = {"preprocessor": preprocessor, "model": model}
        router_bundle = {
            "configured_features": ["a", "b"],
            "scenarios": {"full": ["a", "b"], "a_only": ["a"]},
            "selected_models": {
                "full": "logistic_regression",
                "a_only": "logistic_regression",
            },
            "model_bundles": {"logistic_regression": model_bundle},
            "scenario_calibrators": {
                "logistic_regression": {
                    "full": IdentityCalibrator(),
                    "a_only": IdentityCalibrator(),
                }
            },
            "threshold": 0.5,
        }
        predicted = route_patient(
            router_bundle,
            pd.DataFrame({"a": [0.75], "b": [np.nan]}),
        )
        self.assertEqual(predicted["status"], "predicted")
        self.assertEqual(predicted["scenario"], "a_only")
        integer_input = route_patient(
            router_bundle,
            pd.DataFrame({"a": [1], "b": [2]}),
            scenario_name="a_only",
        )
        self.assertEqual(integer_input["status"], "predicted")
        abstained = route_patient(
            router_bundle,
            pd.DataFrame({"a": [np.nan], "b": [np.nan]}),
        )
        self.assertEqual(abstained["status"], "abstain")


if __name__ == "__main__":
    unittest.main()
