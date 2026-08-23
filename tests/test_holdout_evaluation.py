from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.bootstrap import bootstrap_index_samples
from diabetes_pipeline.evaluation.comparisons import (
    paired_bootstrap_model_comparisons,
)
from diabetes_pipeline.holdout_runner import _predefined_development_splits
from diabetes_pipeline.training.tuning import cross_fitted_probabilities


class HoldoutEvaluationTests(unittest.TestCase):
    def test_predefined_manifest_folds_cover_every_development_row(self) -> None:
        manifest = pd.DataFrame(
            {
                "outer_fold": [0, 0, 1, 1, 2, 2],
                "target": [0, 1, 0, 1, 0, 1],
            }
        )
        splits = _predefined_development_splits(manifest)
        validation = np.concatenate([fold for _, fold in splits])
        np.testing.assert_array_equal(np.sort(validation), np.arange(6))

        X = pd.DataFrame({"x": [-2.0, 2.0, -1.5, 1.5, -1.0, 1.0]})
        y = manifest["target"].to_numpy()
        probability = cross_fitted_probabilities(
            X,
            y,
            {"numeric_features": ["x"], "categorical_features": []},
            "logistic_regression",
            {"C": 1.0, "l1_ratio": 0.0, "class_weight": None},
            n_splits=3,
            seed=42,
            predefined_splits=splits,
        )
        self.assertTrue(np.isfinite(probability).all())

    def test_cluster_bootstrap_resamples_complete_clusters(self) -> None:
        y = np.array([0, 0, 1, 1, 0, 1])
        groups = np.array(["a", "a", "b", "b", "c", "c"])
        samples = bootstrap_index_samples(
            y, n_bootstrap=10, seed=42, groups=groups
        )
        for indexes in samples:
            counts = np.bincount(indexes, minlength=len(y))
            self.assertEqual(counts[0], counts[1])
            self.assertEqual(counts[2], counts[3])
            self.assertEqual(counts[4], counts[5])

    def test_paired_bootstrap_comparison_preserves_pairing(self) -> None:
        y = np.array([0, 1] * 20)
        probability = np.linspace(0.05, 0.95, len(y))
        rows = []
        for model in ("a", "b"):
            rows.append(
                pd.DataFrame(
                    {
                        "model": model,
                        "row_id": [f"row:{i}" for i in range(len(y))],
                        "target": y,
                        "probability_calibrated": probability,
                    }
                )
            )
        result = paired_bootstrap_model_comparisons(
            pd.concat(rows, ignore_index=True), n_bootstrap=20, seed=42
        )
        self.assertTrue(
            np.allclose(result["observed_difference_a_minus_b"], 0.0)
        )
        self.assertTrue(np.allclose(result["paired_bootstrap_p_value"], 1.0))

        one_model = paired_bootstrap_model_comparisons(
            rows[0], n_bootstrap=5, seed=42
        )
        self.assertTrue(one_model.empty)
        self.assertIn("metric", one_model.columns)


if __name__ == "__main__":
    unittest.main()
