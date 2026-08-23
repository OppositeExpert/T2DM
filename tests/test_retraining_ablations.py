from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.retraining_ablations import (
    missing_indicator_contrasts,
)


def _predictions(grouped: bool = False) -> pd.DataFrame:
    rows = []
    y = np.array([0, 0, 0, 1, 1, 1])
    for model in ("logistic_regression", "random_forest"):
        for variant, probability in (
            ("missing_indicator_on", np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])),
            ("missing_indicator_off", np.array([0.2, 0.3, 0.4, 0.6, 0.7, 0.8])),
        ):
            for repeat in (0, 1):
                for index, target in enumerate(y):
                    rows.append(
                        {
                            "dataset": "toy",
                            "model": model,
                            "variant": variant,
                            "row_id": f"row:{index}",
                            "group_id": f"g{index // 2}" if grouped else "",
                            "repeat": repeat,
                            "target": target,
                            "probability_raw": probability[index],
                            "probability_calibrated": probability[index],
                        }
                    )
    return pd.DataFrame(rows)


class RetrainingAblationTests(unittest.TestCase):
    def test_indicator_improvement_has_consistent_orientation(self) -> None:
        aggregated, contrasts = missing_indicator_contrasts(
            _predictions(), n_bootstrap=20, seed=42
        )
        self.assertEqual(len(aggregated), 24)
        self.assertEqual(len(contrasts), 8)
        self.assertTrue(
            contrasts["observed_improvement_indicators_on_over_off"].ge(0).all()
        )
        self.assertTrue(contrasts["holm_adjusted_p_value"].between(0, 1).all())

    def test_grouped_indicator_contrast_uses_cluster_resampling(self) -> None:
        _, contrasts = missing_indicator_contrasts(
            _predictions(grouped=True), n_bootstrap=10, seed=42
        )
        self.assertTrue(contrasts["resampling_unit"].eq("cluster").all())

    def test_numerically_equivalent_predictions_are_exact_null(self) -> None:
        frame = _predictions()
        off = frame["variant"].eq("missing_indicator_off")
        frame.loc[off, "probability_calibrated"] = (
            frame.loc[off, "probability_calibrated"] + 1e-14
        )
        on_probability = {
            index: probability
            for index, probability in enumerate([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])
        }
        frame.loc[off, "probability_calibrated"] = frame.loc[off].apply(
            lambda row: on_probability[int(str(row["row_id"]).split(":")[1])]
            + 1e-14,
            axis=1,
        )
        _, contrasts = missing_indicator_contrasts(
            frame, n_bootstrap=10, seed=42
        )
        self.assertTrue(
            contrasts["numerically_equivalent_predictions_collapsed"].all()
        )
        self.assertTrue(
            contrasts["observed_improvement_indicators_on_over_off"].eq(0).all()
        )
        self.assertTrue(contrasts["holm_adjusted_p_value"].eq(1).all())

    def test_missing_variant_is_rejected(self) -> None:
        frame = _predictions()
        frame = frame[frame["variant"] == "missing_indicator_on"]
        with self.assertRaisesRegex(ValueError, "Both missing-indicator"):
            missing_indicator_contrasts(frame, n_bootstrap=5, seed=42)


if __name__ == "__main__":
    unittest.main()
