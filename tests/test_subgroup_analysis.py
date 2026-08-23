from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.subgroup_analysis import subgroup_performance_analysis


class SubgroupAnalysisTests(unittest.TestCase):
    def test_small_cells_are_suppressed_and_supported_cells_are_estimated(self) -> None:
        rows = []
        membership = []
        for index in range(80):
            target = int(index >= 40)
            rows.append(
                {
                    "dataset": "toy",
                    "system": "availability_router",
                    "scenario": "full",
                    "row_id": f"r{index}",
                    "group_id": "",
                    "target": target,
                    "probability_calibrated": 0.2 if target == 0 else 0.8,
                    "target_coverage": 1.0,
                    "accepted": True,
                }
            )
            membership.append(
                {
                    "row_id": f"r{index}",
                    "subgroup_variable": "group",
                    "subgroup_value": "supported" if index < 70 else "small",
                }
            )
        metrics, intervals = subgroup_performance_analysis(
            pd.DataFrame(rows),
            pd.DataFrame(membership),
            n_bootstrap=5,
            seed=42,
            minimum_n=20,
            minimum_events=5,
        )
        status = metrics.set_index("subgroup_value")["status"].to_dict()
        self.assertEqual(status["supported"], "estimated")
        self.assertEqual(status["small"], "suppressed_small_cell")
        self.assertFalse(intervals.empty)


if __name__ == "__main__":
    unittest.main()
