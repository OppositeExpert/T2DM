from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.leakage_demonstrations import (
    _cross_validated_probabilities,
)


class LeakageDemonstrationTests(unittest.TestCase):
    def test_grouped_cross_validation_covers_rows_without_group_overlap(self) -> None:
        X = pd.DataFrame({"x": np.tile([0.0, 1.0], 20)})
        y = np.tile([0, 1], 20)
        groups = np.repeat(np.arange(20), 2)
        cfg = {"numeric_features": ["x"], "categorical_features": []}
        probability, diagnostics = _cross_validated_probabilities(
            X,
            y,
            cfg,
            model_name="logistic_regression",
            groups=groups,
            diagnostic_groups=groups,
            global_preprocessing=False,
            seed=42,
            n_splits=4,
        )
        self.assertFalse(np.isnan(probability).any())
        self.assertTrue(all(row["group_overlap"] == 0 for row in diagnostics))


if __name__ == "__main__":
    unittest.main()
