from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.panel_training_ablations import (
    MASKED_STRATEGY,
    PANEL_STRATEGY,
    aggregate_panel_strategy_predictions,
    panel_training_contrasts,
)


def _predictions(grouped: bool = False) -> pd.DataFrame:
    rows = []
    y = np.array([0, 0, 0, 1, 1, 1])
    for model in ("random_forest", "xgboost"):
        for strategy, probability in (
            (PANEL_STRATEGY, np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])),
            (MASKED_STRATEGY, np.array([0.2, 0.3, 0.4, 0.6, 0.7, 0.8])),
        ):
            for repeat in (0, 1):
                for index, target in enumerate(y):
                    rows.append(
                        {
                            "dataset": "toy",
                            "model": model,
                            "scenario": "reduced",
                            "training_strategy": strategy,
                            "row_id": f"row:{index}",
                            "group_id": f"g{index // 2}" if grouped else "",
                            "repeat": repeat,
                            "outer_fold": index % 2,
                            "target": target,
                            "probability_raw": probability[index],
                            "probability_calibrated": probability[index],
                        }
                    )
    return pd.DataFrame(rows)


class PanelTrainingAblationTests(unittest.TestCase):
    def test_aggregation_returns_one_row_per_strategy_participant(self) -> None:
        aggregated = aggregate_panel_strategy_predictions(_predictions())
        self.assertEqual(len(aggregated), 24)
        self.assertTrue(aggregated["repeat_count"].eq(2).all())

    def test_panel_training_improvement_orientation_is_positive(self) -> None:
        _, contrasts = panel_training_contrasts(
            _predictions(), n_bootstrap=20, seed=42
        )
        self.assertEqual(len(contrasts), 8)
        self.assertTrue(
            contrasts[
                "observed_improvement_panel_training_over_masked"
            ].ge(0).all()
        )
        self.assertTrue(contrasts["holm_adjusted_p_value"].between(0, 1).all())

    def test_grouped_predictions_use_cluster_resampling(self) -> None:
        _, contrasts = panel_training_contrasts(
            _predictions(grouped=True), n_bootstrap=10, seed=42
        )
        self.assertTrue(contrasts["resampling_unit"].eq("cluster").all())

    def test_missing_strategy_is_rejected(self) -> None:
        frame = _predictions()
        frame = frame[frame["training_strategy"] == PANEL_STRATEGY]
        with self.assertRaisesRegex(ValueError, "Both panel-training"):
            panel_training_contrasts(frame, n_bootstrap=5, seed=42)


if __name__ == "__main__":
    unittest.main()
