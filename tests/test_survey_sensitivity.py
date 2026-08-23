from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.survey_sensitivity import (
    _psu_bootstrap_weight_chunks,
    weighted_binary_metrics,
)


class SurveySensitivityTests(unittest.TestCase):
    def test_equal_weights_reproduce_standard_binary_quantities(self) -> None:
        y = np.array([0, 0, 1, 1])
        probability = np.array([0.1, 0.6, 0.4, 0.9])
        metrics = weighted_binary_metrics(
            y,
            probability,
            np.ones(4),
            threshold=0.5,
        )
        self.assertAlmostEqual(metrics["prevalence"], 0.5)
        self.assertAlmostEqual(metrics["accuracy"], 0.5)
        self.assertAlmostEqual(metrics["sensitivity"], 0.5)
        self.assertAlmostEqual(metrics["specificity"], 0.5)
        self.assertAlmostEqual(metrics["ppv"], 0.5)
        self.assertAlmostEqual(metrics["npv"], 0.5)

    def test_weights_change_population_estimand(self) -> None:
        y = np.array([0, 0, 1, 1])
        probability = np.array([0.1, 0.2, 0.8, 0.9])
        metrics = weighted_binary_metrics(
            y,
            probability,
            np.array([1.0, 1.0, 4.0, 4.0]),
            threshold=0.5,
        )
        self.assertAlmostEqual(metrics["prevalence"], 0.8)
        self.assertAlmostEqual(metrics["accuracy"], 1.0)
        self.assertGreater(metrics["kish_effective_sample_size"], 0.0)

    def test_psu_bootstrap_keeps_rows_in_one_cluster_together(self) -> None:
        design = pd.DataFrame(
            {
                "_STSTR": [1, 1, 1, 1, 2, 2],
                "_PSU": [10, 10, 11, 11, 20, 20],
                "_LLCPWT": np.ones(6),
            }
        )
        chunks = list(
            _psu_bootstrap_weight_chunks(
                design,
                n_bootstrap=8,
                seed=42,
                chunk_size=3,
            )
        )
        weights = np.vstack([chunk for _, chunk in chunks])
        self.assertEqual(weights.shape, (8, 6))
        self.assertTrue(np.array_equal(weights[:, 0], weights[:, 1]))
        self.assertTrue(np.array_equal(weights[:, 2], weights[:, 3]))
        self.assertTrue(np.all(weights[:, 4:] == 1.0))
        self.assertTrue(np.all(weights[:, :4].sum(axis=1) == 4.0))


if __name__ == "__main__":
    unittest.main()
