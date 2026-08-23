from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.routing.panel_contrasts import (
    aggregate_panel_predictions,
    matched_panel_bootstrap_contrasts,
)


def _predictions(*, grouped: bool = False) -> pd.DataFrame:
    rows = []
    targets = np.array([0, 0, 0, 1, 1, 1])
    full = np.array([0.05, 0.10, 0.20, 0.75, 0.85, 0.95])
    reduced = np.array([0.20, 0.25, 0.40, 0.55, 0.65, 0.80])
    for model in ("m1", "m2"):
        for scenario, probability, feature_count in (
            ("full", full, 6),
            ("reduced", reduced, 3),
        ):
            for repeat in (0, 1):
                for index, target in enumerate(targets):
                    rows.append(
                        {
                            "dataset": "toy",
                            "model": model,
                            "scenario": scenario,
                            "available_feature_count": feature_count,
                            "row_id": f"row:{index}",
                            "group_id": f"g{index // 2}" if grouped else "",
                            "repeat": repeat,
                            "target": target,
                            "probability_calibrated": probability[index]
                            + repeat * 0.001,
                        }
                    )
    return pd.DataFrame(rows)


class PanelContrastTests(unittest.TestCase):
    def test_aggregation_returns_one_prediction_per_panel_participant(self) -> None:
        aggregated = aggregate_panel_predictions(_predictions())
        self.assertEqual(len(aggregated), 24)
        self.assertTrue(aggregated["repeat_count"].eq(2).all())
        self.assertTrue(
            aggregated["estimation_scope"].eq(
                "participant_mean_across_repeats"
            ).all()
        )

    def test_reduced_panel_has_positive_degradation(self) -> None:
        _, contrasts = matched_panel_bootstrap_contrasts(
            _predictions(), n_bootstrap=30, seed=42
        )
        self.assertEqual(len(contrasts), 8)
        brier = contrasts[contrasts["metric"] == "brier_score"]
        average_precision = contrasts[contrasts["metric"] == "average_precision"]
        self.assertTrue((brier["observed_degradation"] > 0.0).all())
        self.assertTrue((average_precision["observed_degradation"] >= 0.0).all())
        self.assertTrue(contrasts["holm_adjusted_p_value"].between(0, 1).all())

    def test_grouped_panels_use_cluster_resampling(self) -> None:
        _, contrasts = matched_panel_bootstrap_contrasts(
            _predictions(grouped=True), n_bootstrap=10, seed=42
        )
        self.assertTrue(contrasts["resampling_unit"].eq("cluster").all())

    def test_holdout_predictions_keep_one_locked_test_row(self) -> None:
        frame = _predictions()
        frame = frame[frame["repeat"] == 0].drop(columns="repeat")
        aggregated = aggregate_panel_predictions(frame)
        self.assertEqual(len(aggregated), 24)
        self.assertTrue(aggregated["repeat_count"].eq(1).all())
        self.assertTrue(aggregated["estimation_scope"].eq("locked_test").all())

    def test_missing_full_panel_is_rejected(self) -> None:
        frame = _predictions()
        frame = frame[frame["scenario"] != "full"]
        with self.assertRaisesRegex(ValueError, "requires a 'full'"):
            matched_panel_bootstrap_contrasts(frame, n_bootstrap=5, seed=42)


if __name__ == "__main__":
    unittest.main()
