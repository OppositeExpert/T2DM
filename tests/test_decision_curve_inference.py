from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.decision_curve_inference import (
    decision_curve_bootstrap_inference,
)


def _predictions() -> pd.DataFrame:
    y = np.array([0, 0, 0, 1, 1, 1])
    rows = []
    for model, probability in (
        ("a", np.array([0.05, 0.10, 0.40, 0.60, 0.85, 0.95])),
        ("b", np.array([0.10, 0.20, 0.45, 0.55, 0.75, 0.90])),
    ):
        rows.append(
            pd.DataFrame(
                {
                    "model": model,
                    "row_id": [f"row:{index}" for index in range(len(y))],
                    "target": y,
                    "probability_calibrated": probability,
                }
            )
        )
    return pd.concat(rows, ignore_index=True)


class DecisionCurveInferenceTests(unittest.TestCase):
    def test_returns_intervals_and_paired_contrasts(self) -> None:
        intervals, contrasts = decision_curve_bootstrap_inference(
            _predictions(),
            n_bootstrap=30,
            seed=42,
            thresholds=np.array([0.2, 0.5]),
        )
        self.assertEqual(len(intervals), 4)
        self.assertEqual(len(contrasts), 2)
        self.assertTrue(intervals["resampling_unit"].eq("individual").all())
        self.assertTrue(
            contrasts["paired_bootstrap_p_value"].between(0.0, 1.0).all()
        )

    def test_identical_models_have_zero_paired_difference(self) -> None:
        predictions = _predictions()
        model_a = predictions[predictions["model"] == "a"].copy()
        model_b = model_a.copy()
        model_b["model"] = "b"
        _, contrasts = decision_curve_bootstrap_inference(
            pd.concat([model_a, model_b], ignore_index=True),
            n_bootstrap=20,
            seed=7,
            thresholds=np.array([0.25, 0.50]),
        )
        self.assertTrue(
            np.allclose(contrasts["observed_difference_a_minus_b"], 0.0)
        )
        self.assertTrue(np.allclose(contrasts["ci_lower_a_minus_b"], 0.0))
        self.assertTrue(np.allclose(contrasts["ci_upper_a_minus_b"], 0.0))
        self.assertTrue(np.allclose(contrasts["paired_bootstrap_p_value"], 1.0))

    def test_cluster_resampling_is_reported(self) -> None:
        groups = np.array(["g0", "g0", "g1", "g1", "g2", "g2"])
        intervals, contrasts = decision_curve_bootstrap_inference(
            _predictions(),
            n_bootstrap=10,
            seed=42,
            thresholds=np.array([0.3]),
            groups=groups,
        )
        self.assertTrue(intervals["resampling_unit"].eq("cluster").all())
        self.assertTrue(contrasts["resampling_unit"].eq("cluster").all())

    def test_misaligned_models_are_rejected(self) -> None:
        frame = _predictions().iloc[:-1]
        with self.assertRaisesRegex(ValueError, "identical paired rows"):
            decision_curve_bootstrap_inference(
                frame,
                n_bootstrap=5,
                seed=42,
                thresholds=np.array([0.5]),
            )


if __name__ == "__main__":
    unittest.main()
