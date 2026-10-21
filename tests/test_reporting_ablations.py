from __future__ import annotations

import unittest

import pandas as pd

from diabetes_pipeline.evaluation.reporting_ablations import panel_size_residuals


class ReportingAblationTests(unittest.TestCase):
    def test_panel_size_fit_preserves_named_panel_residuals(self) -> None:
        frame = pd.DataFrame({
            "scenario": ["small", "medium", "large"],
            "available_feature_count": [2, 4, 8],
            "system": ["robust_single_model"] * 3,
            "brier_score": [0.3, 0.2, 0.1],
            "average_precision": [0.5, 0.6, 0.8],
        })
        panels, diagnostics = panel_size_residuals(frame)
        self.assertEqual(len(panels), 3)
        self.assertEqual(set(diagnostics["metric"]), {"brier_score", "average_precision"})
        self.assertIn("brier_score_named_panel_residual", panels)


if __name__ == "__main__":
    unittest.main()
