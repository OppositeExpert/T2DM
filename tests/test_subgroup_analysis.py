from __future__ import annotations

import unittest

import numpy as np
import pandas as pd
from types import SimpleNamespace
from unittest.mock import patch

from diabetes_pipeline.evaluation.subgroup_analysis import (
    subgroup_membership,
    subgroup_performance_analysis,
)


class SubgroupAnalysisTests(unittest.TestCase):
    def test_hospital_membership_supports_age_gender_and_race(self) -> None:
        dataset = SimpleNamespace(
            row_ids=pd.Series(["e1", "e2", "e3", "e4"]),
            X=pd.DataFrame(
                {
                    "age": [1.0, 3.0, 5.0, 8.0],
                    "gender": ["Female", "Male", "Unknown/Invalid", "Female"],
                    "race": ["Caucasian", "AfricanAmerican", pd.NA, "Asian"],
                }
            ),
        )
        with patch(
            "diabetes_pipeline.evaluation.subgroup_analysis.load_dataset",
            return_value=dataset,
        ):
            membership = subgroup_membership("hospital130")
        self.assertEqual(
            set(membership["subgroup_variable"]), {"age_group", "sex", "race"}
        )
        age = membership[membership["subgroup_variable"] == "age_group"]
        self.assertEqual(
            age["subgroup_value"].tolist(),
            ["under_30", "30-49", "50-69", "70+"],
        )
        sex = membership[membership["subgroup_variable"] == "sex"]
        self.assertEqual(set(sex["subgroup_value"]), {"female", "male"})

    def test_membership_preserves_noncontiguous_source_index_identity(self) -> None:
        source_index = pd.Index([0, 2, 7, 11])
        dataset = SimpleNamespace(
            row_ids=pd.Series(["e1", "e2", "e3", "e4"], index=source_index),
            X=pd.DataFrame(
                {
                    "age": [1.0, 3.0, 5.0, 8.0],
                    "gender": ["Female", "Male", "Female", "Male"],
                    "race": ["Asian", "Caucasian", "Hispanic", "Other"],
                },
                index=source_index,
            ),
        )
        with patch(
            "diabetes_pipeline.evaluation.subgroup_analysis.load_dataset",
            return_value=dataset,
        ):
            membership = subgroup_membership("hospital130")
        age = membership[membership["subgroup_variable"] == "age_group"]
        self.assertEqual(
            age.set_index("row_id")["subgroup_value"].to_dict(),
            {"e1": "under_30", "e2": "30-49", "e3": "50-69", "e4": "70+"},
        )
        race = membership[membership["subgroup_variable"] == "race"]
        self.assertEqual(
            race.set_index("row_id")["subgroup_value"].to_dict()["e3"],
            "Hispanic",
        )

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
