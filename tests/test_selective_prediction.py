from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.selective_prediction import (
    aggregate_routing_predictions,
    selective_prediction_analysis,
)


def _predictions(grouped: bool = False) -> pd.DataFrame:
    rows = []
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    probability = np.array([0.01, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 0.99])
    for repeat in (0, 1):
        for index, target in enumerate(y):
            rows.append(
                {
                    "dataset": "toy",
                    "system": "availability_router",
                    "scenario": "full",
                    "row_id": f"row:{index}",
                    "group_id": f"g{index // 2}" if grouped else "",
                    "repeat": repeat,
                    "target": target,
                    "probability_calibrated": probability[index],
                }
            )
    return pd.DataFrame(rows)


class SelectivePredictionTests(unittest.TestCase):
    def test_repeated_predictions_are_aggregated_per_participant(self) -> None:
        aggregated = aggregate_routing_predictions(_predictions())
        self.assertEqual(len(aggregated), 8)
        self.assertTrue(aggregated["repeat_count"].eq(2).all())

    def test_coverage_analysis_rejects_least_certain_rows(self) -> None:
        decisions, metrics, intervals = selective_prediction_analysis(
            _predictions(), coverages=[1.0, 0.75], n_bootstrap=10, seed=42
        )
        reduced = decisions[decisions["target_coverage"] == 0.75]
        rejected = reduced[~reduced["accepted"]]
        self.assertEqual(set(rejected["row_id"]), {"row:3", "row:4"})
        self.assertEqual(len(metrics), 2)
        self.assertFalse(intervals.empty)
        reduced_metrics = metrics[metrics["target_coverage"] == 0.75].iloc[0]
        self.assertEqual(int(reduced_metrics["accepted_n"]), 6)
        self.assertAlmostEqual(float(reduced_metrics["rejected_prevalence"]), 0.5)

    def test_grouped_acceptance_keeps_clusters_intact(self) -> None:
        decisions, _, _ = selective_prediction_analysis(
            _predictions(grouped=True),
            coverages=[0.75],
            n_bootstrap=5,
            seed=42,
        )
        decisions_by_group = decisions.groupby("group_id")["accepted"].nunique()
        self.assertTrue(decisions_by_group.eq(1).all())
        _, metrics, _ = selective_prediction_analysis(
            _predictions(grouped=True),
            coverages=[0.75],
            n_bootstrap=5,
            seed=42,
        )
        self.assertEqual(int(metrics.iloc[0]["accepted_group_count"]), 3)


if __name__ == "__main__":
    unittest.main()
