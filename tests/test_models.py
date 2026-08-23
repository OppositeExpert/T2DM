from __future__ import annotations

import unittest

import numpy as np

from diabetes_pipeline.models.registry import build_estimator


class ModelAdapterTests(unittest.TestCase):
    def test_all_models_fit_and_return_positive_probability(self) -> None:
        rng = np.random.default_rng(42)
        X = rng.normal(size=(80, 5))
        y = np.array([0, 1] * 40)
        parameters = {
            "logistic_regression": {"C": 1.0, "l1_ratio": 0.0, "class_weight": None},
            "random_forest": {"n_estimators": 10, "max_depth": 3},
            "xgboost": {
                "n_estimators": 10,
                "max_depth": 3,
                "learning_rate": 0.1,
                "use_class_weight": False,
            },
            "lightgbm": {"n_estimators": 10, "num_leaves": 7},
            "catboost": {"iterations": 10, "depth": 3},
        }
        for name, params in parameters.items():
            with self.subTest(model=name):
                model = build_estimator(
                    name, params, seed=42, n_jobs=1, positive_class_weight=1.0
                )
                model.fit(X, y)
                probability = model.predict_proba(X[:4])
                self.assertEqual(probability.shape, (4,))
                self.assertTrue(np.all((probability >= 0) & (probability <= 1)))


if __name__ == "__main__":
    unittest.main()
