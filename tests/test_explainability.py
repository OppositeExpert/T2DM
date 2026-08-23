from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.explainability.shap_analysis import (
    group_shap_by_original_feature,
    _positive_class_values,
    _raw_feature_matrix,
)
from diabetes_pipeline.explainability.stability import importance_tables
from diabetes_pipeline.explainability.plots import _filename_token


class ExplainabilityTests(unittest.TestCase):
    def test_transformed_feature_plot_filename_is_path_safe(self) -> None:
        token = _filename_token("medical_specialty_Hematology/Oncology")
        self.assertNotIn("/", token)
        self.assertEqual(token, _filename_token("medical_specialty_Hematology/Oncology"))

    def test_positive_class_shap_output_is_selected(self) -> None:
        values = np.arange(24, dtype=float).reshape(3, 4, 2)
        selected, base = _positive_class_values(values, np.array([0.4, 0.6]))
        np.testing.assert_array_equal(selected, values[:, :, 1])
        self.assertEqual(float(base), 0.6)

    def test_raw_feature_matrix_maps_missing_indicators(self) -> None:
        raw = pd.DataFrame({"Glucose": [100.0, np.nan], "Age": [30.0, 50.0]})
        matrix = _raw_feature_matrix(
            raw,
            ["Glucose", "Age", "missingindicator_Glucose"],
        )
        np.testing.assert_allclose(matrix[:, 1], [30.0, 50.0])
        np.testing.assert_allclose(matrix[:, 2], [0.0, 1.0])

    def test_stability_tables_use_only_fold_importance(self) -> None:
        rows = []
        for fold in (0, 1):
            for row_id in ("a", "b"):
                for feature, value in (("x", 0.8), ("y", 0.2), ("z", 0.1)):
                    rows.append(
                        {
                            "model": "xgboost",
                            "repeat": 0,
                            "outer_fold": fold,
                            "row_id": f"{row_id}{fold}",
                            "feature": feature,
                            "shap_value": value,
                            "absolute_shap_value": abs(value),
                            "transformed_feature_value": value + fold,
                        }
                    )
        fold, global_table, pairwise, summary = importance_tables(
            pd.DataFrame(rows), top_k=2
        )
        self.assertEqual(len(fold), 6)
        self.assertEqual(global_table.iloc[0]["feature"], "x")
        self.assertEqual(len(pairwise), 1)
        self.assertAlmostEqual(float(summary.iloc[0]["mean_top_k_jaccard"]), 1.0)

    def test_one_hot_and_missing_components_group_to_original_feature(self) -> None:
        frame = pd.DataFrame(
            {
                "model": ["xgboost"] * 4,
                "repeat": [0] * 4,
                "outer_fold": [0] * 4,
                "row_id": ["a"] * 4,
                "feature": [
                    "race_A",
                    "race_B",
                    "Glucose",
                    "missingindicator_Glucose",
                ],
                "shap_value": [0.3, -0.1, 0.5, 0.2],
                "absolute_shap_value": [0.3, 0.1, 0.5, 0.2],
                "raw_feature_value": [np.nan, np.nan, 140.0, 0.0],
                "transformed_feature_value": [1.0, 0.0, 140.0, 0.0],
            }
        )
        grouped = group_shap_by_original_feature(
            frame, ["race", "Glucose"]
        ).set_index("feature")
        self.assertAlmostEqual(float(grouped.loc["race", "shap_value"]), 0.2)
        self.assertAlmostEqual(float(grouped.loc["Glucose", "shap_value"]), 0.7)
        self.assertEqual(int(grouped.loc["race", "transformed_component_count"]), 2)


if __name__ == "__main__":
    unittest.main()
