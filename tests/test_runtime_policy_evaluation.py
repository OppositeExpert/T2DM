from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.routing.policy_evaluator import (
    _optional_group_values,
    _supported_scenarios,
)


class RuntimePolicyEvaluationTests(unittest.TestCase):
    def test_object_typed_group_ids_are_normalized_for_numpy_string_operations(
        self,
    ) -> None:
        groups = _optional_group_values(pd.Series(["patient-1", None], dtype=object))
        self.assertIsNotNone(groups)
        assert groups is not None
        self.assertEqual(groups.tolist(), ["patient-1", ""])
        self.assertEqual(groups.dtype.kind, "U")
        self.assertIsNone(
            _optional_group_values(pd.Series([None, ""], dtype=object))
        )

    def test_largest_supported_panel_and_abstention_match_runtime_contract(self) -> None:
        frame = pd.DataFrame(
            {
                "a": [1.0, 1.0, np.nan, np.nan],
                "b": [2.0, np.nan, 2.0, np.nan],
                "c": [3.0, 3.0, np.nan, np.nan],
            }
        )
        scenarios = {
            "full": ["a", "b", "c"],
            "a_c": ["a", "c"],
            "a_only": ["a"],
        }
        self.assertEqual(
            _supported_scenarios(frame, scenarios).tolist(),
            ["full", "a_c", "", ""],
        )


if __name__ == "__main__":
    unittest.main()
