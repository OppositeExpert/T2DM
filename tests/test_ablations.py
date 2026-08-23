from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.ablations import (
    build_selector_predictions,
    calibration_ablation,
    model_family_ablation,
    selector_metric_ablation,
)


def _base_predictions() -> pd.DataFrame:
    rows = []
    y = np.array([0, 0, 0, 1, 1, 1])
    for model, calibrated in (
        ("logistic_regression", np.array([0.1, 0.2, 0.3, 0.7, 0.8, 0.9])),
        ("random_forest", np.array([0.05, 0.1, 0.2, 0.8, 0.9, 0.95])),
    ):
        for repeat in (0, 1):
            for index, target in enumerate(y):
                rows.append(
                    {
                        "dataset": "toy",
                        "model": model,
                        "row_id": f"row:{index}",
                        "group_id": "",
                        "repeat": repeat,
                        "target": target,
                        "probability_raw": np.clip(
                            calibrated[index] * 0.8 + 0.1, 0.001, 0.999
                        ),
                        "probability_calibrated": calibrated[index],
                    }
                )
    return pd.DataFrame(rows)


class AblationTests(unittest.TestCase):
    def test_calibration_ablation_orients_lower_losses_as_improvement(self) -> None:
        result = calibration_ablation(
            _base_predictions(), n_bootstrap=20, seed=42
        )
        self.assertEqual(len(result), 8)
        self.assertTrue(result["holm_adjusted_p_value"].between(0, 1).all())
        self.assertTrue(result["positive_improvement_is_better"].all())

    def test_model_family_ablation_uses_logistic_reference(self) -> None:
        result = model_family_ablation(
            _base_predictions(), n_bootstrap=20, seed=42
        )
        self.assertEqual(set(result["tree_model"]), {"random_forest"})
        self.assertTrue(result["reference_model"].eq("logistic_regression").all())
        self.assertTrue(
            result["observed_improvement_tree_over_logistic"].ge(0.0).all()
        )

    def test_selector_predictions_use_development_scores_only(self) -> None:
        development = pd.DataFrame(
            {
                "scenario": ["full", "full", "reduced", "reduced"],
                "model": ["a", "b", "a", "b"],
                "brier_score": [0.10, 0.12, 0.20, 0.18],
                "log_loss": [0.30, 0.28, 0.50, 0.55],
                "average_precision": [0.70, 0.75, 0.60, 0.58],
            }
        )
        stress_rows = []
        for scenario in ("full", "reduced"):
            for model in ("a", "b"):
                for index, target in enumerate((0, 1)):
                    stress_rows.append(
                        {
                            "dataset": "toy",
                            "scenario": scenario,
                            "model": model,
                            "row_id": f"row:{index}",
                            "group_id": "",
                            "target": target,
                            "probability_calibrated": 0.2 + 0.6 * target,
                        }
                    )
        selected = build_selector_predictions(
            development, pd.DataFrame(stress_rows)
        )
        chosen = selected.groupby(["scenario", "system"])["selected_model"].first()
        self.assertEqual(chosen.loc[("full", "selector_brier")], "a")
        self.assertEqual(chosen.loc[("full", "selector_average_precision")], "b")
        self.assertEqual(chosen.loc[("full", "selector_log_loss")], "b")
        self.assertEqual(chosen.loc[("reduced", "selector_brier")], "b")

        contrasts = selector_metric_ablation(
            development,
            pd.DataFrame(stress_rows),
            n_bootstrap=10,
            seed=42,
        )
        self.assertFalse(contrasts.empty)
        self.assertTrue(
            contrasts["reference_system"].eq("selector_brier").all()
        )


if __name__ == "__main__":
    unittest.main()
