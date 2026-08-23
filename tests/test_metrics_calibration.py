from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.calibration.calibrators import fit_calibrator, select_calibrator
from diabetes_pipeline.calibration.thresholds import select_thresholds
from diabetes_pipeline.evaluation.bootstrap import bootstrap_metric_intervals
from diabetes_pipeline.evaluation.decision_curve import decision_curve
from diabetes_pipeline.evaluation.comparisons import paired_model_comparisons
from diabetes_pipeline.evaluation.metrics import binary_metrics


class MetricsCalibrationTests(unittest.TestCase):
    def test_metrics_reconcile_confusion_counts(self) -> None:
        y = np.array([0, 0, 1, 1])
        probability = np.array([0.1, 0.7, 0.8, 0.2])
        metrics = binary_metrics(y, probability, threshold=0.5)
        self.assertEqual(metrics["tn"], 1)
        self.assertEqual(metrics["fp"], 1)
        self.assertEqual(metrics["fn"], 1)
        self.assertEqual(metrics["tp"], 1)
        self.assertAlmostEqual(metrics["sensitivity"], 0.5)
        self.assertAlmostEqual(metrics["specificity"], 0.5)
        self.assertAlmostEqual(metrics["false_positive_rate"], 0.5)
        self.assertAlmostEqual(metrics["false_negative_rate"], 0.5)
        self.assertAlmostEqual(metrics["diagnostic_odds_ratio"], 1.0)

    def test_sigmoid_calibrator_returns_probabilities(self) -> None:
        y = np.array([0, 0, 0, 1, 1, 1])
        probability = np.array([0.05, 0.2, 0.4, 0.55, 0.75, 0.95])
        calibrator = fit_calibrator("sigmoid", probability, y)
        calibrated = calibrator.predict(probability)
        self.assertEqual(calibrated.shape, probability.shape)
        self.assertTrue(np.all((calibrated > 0) & (calibrated < 1)))

    def test_calibration_selection_is_cross_fitted_and_deterministic(self) -> None:
        y = np.array([0, 1] * 30)
        probability = np.linspace(0.05, 0.95, len(y))
        first = select_calibrator(
            ["identity", "sigmoid", "isotonic"],
            probability,
            y,
            n_splits=3,
            seed=42,
        )
        second = select_calibrator(
            ["identity", "sigmoid", "isotonic"],
            probability,
            y,
            n_splits=3,
            seed=42,
        )
        self.assertEqual(first.method, second.method)
        np.testing.assert_allclose(
            first.cross_fitted_probability,
            second.cross_fitted_probability,
        )
        self.assertEqual(len(first.scores), 3)

    def test_small_sample_isotonic_can_be_predeclared_ineligible(self) -> None:
        y = np.array([0, 1] * 30)
        probability = np.linspace(0.05, 0.95, len(y))
        selection = select_calibrator(
            ["identity", "sigmoid", "isotonic"],
            probability,
            y,
            n_splits=3,
            minimum_samples_by_method={"isotonic": 1_000},
        )
        isotonic = next(
            row for row in selection.scores if row["method"] == "isotonic"
        )
        self.assertFalse(isotonic["eligible"])
        self.assertNotEqual(selection.method, "isotonic")

    def test_threshold_policies_use_development_probabilities(self) -> None:
        y = np.array([0, 0, 0, 1, 1, 1])
        probability = np.array([0.05, 0.20, 0.55, 0.30, 0.70, 0.90])
        selected = select_thresholds(
            ["fixed_0_5", "youden_development", "sensitivity_constrained"],
            y,
            probability,
            sensitivity_target=2 / 3,
        )
        thresholds = {row["threshold_policy"]: row["threshold"] for row in selected}
        self.assertEqual(thresholds["fixed_0_5"], 0.5)
        constrained = thresholds["sensitivity_constrained"]
        self.assertGreaterEqual(np.mean(probability[y == 1] >= constrained), 2 / 3)

    def test_bootstrap_and_decision_curve_are_well_formed(self) -> None:
        y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        probability = np.array([0.05, 0.15, 0.30, 0.60, 0.40, 0.70, 0.85, 0.95])
        intervals = bootstrap_metric_intervals(
            y,
            probability,
            threshold=0.5,
            n_bootstrap=10,
            seed=42,
        )
        self.assertTrue(any(row["metric"] == "auroc" for row in intervals))
        curve = decision_curve(y, probability, thresholds=np.array([0.2, 0.5]))
        self.assertEqual(len(curve), 2)
        self.assertTrue(np.allclose(curve["treat_none_net_benefit"], 0.0))

    def test_paired_comparisons_include_holm_adjustment(self) -> None:
        rows = []
        for fold in range(5):
            for model, offset in (("a", 0.02), ("b", 0.01), ("c", 0.0)):
                rows.append(
                    {
                        "repeat": 0,
                        "outer_fold": fold,
                        "model": model,
                        "auroc": 0.75 + offset + fold / 1_000,
                        "average_precision": 0.65 + offset + fold / 1_000,
                        "brier_score": 0.20 - offset,
                        "log_loss": 0.60 - offset,
                    }
                )
        comparisons = paired_model_comparisons(pd.DataFrame(rows))
        self.assertIn("holm_adjusted_p_value", comparisons.columns)
        finite = comparisons["holm_adjusted_p_value"].dropna()
        self.assertTrue(finite.between(0.0, 1.0).all())


if __name__ == "__main__":
    unittest.main()
