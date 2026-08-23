from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.repeated_cv import (
    aggregate_repeated_predictions,
    participant_level_repeated_cv_inference,
)


def _predictions() -> pd.DataFrame:
    rows = []
    targets = {"a": 0, "b": 0, "c": 1, "d": 1}
    groups = {"a": "g0", "b": "g0", "c": "g1", "d": "g1"}
    for model, offset in (("m1", 0.0), ("m2", 0.02)):
        for repeat in (0, 1):
            for index, row_id in enumerate(targets):
                base = (0.1, 0.2, 0.8, 0.9)[index] + offset
                rows.append(
                    {
                        "model": model,
                        "row_id": row_id,
                        "group_id": groups[row_id],
                        "repeat": repeat,
                        "target": targets[row_id],
                        "probability_raw": base + repeat * 0.01,
                        "probability_calibrated": base + repeat * 0.005,
                    }
                )
    return pd.DataFrame(rows)


class RepeatedCvInferenceTests(unittest.TestCase):
    def test_aggregation_returns_one_row_per_model_and_participant(self) -> None:
        aggregated = aggregate_repeated_predictions(_predictions())
        self.assertEqual(len(aggregated), 8)
        self.assertTrue(aggregated["repeat_count"].eq(2).all())
        row = aggregated[(aggregated["model"] == "m1") & (aggregated["row_id"] == "a")].iloc[0]
        self.assertAlmostEqual(row["probability_calibrated"], 0.1025)
        self.assertEqual(row["group_id"], "g0")

    def test_missing_repeat_is_rejected(self) -> None:
        frame = _predictions().iloc[:-1].copy()
        with self.assertRaisesRegex(ValueError, "missing from one or more"):
            aggregate_repeated_predictions(frame)

    def test_participant_inference_uses_cluster_resampling(self) -> None:
        aggregated, intervals, comparisons = participant_level_repeated_cv_inference(
            _predictions(), n_bootstrap=10, seed=42
        )
        self.assertEqual(len(aggregated), 8)
        self.assertTrue(intervals["resampling_unit"].eq("cluster").all())
        self.assertFalse(comparisons.empty)
        self.assertTrue(comparisons["resampling_unit"].eq("cluster").all())


if __name__ == "__main__":
    unittest.main()
