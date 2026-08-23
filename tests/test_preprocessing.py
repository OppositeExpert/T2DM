from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.preprocessing.builders import build_preprocessor, transformed_feature_names


class PreprocessingTests(unittest.TestCase):
    def test_numeric_imputer_fits_training_values_only(self) -> None:
        config = {"numeric_features": ["value"], "categorical_features": []}
        training = pd.DataFrame({"value": [1.0, 3.0, np.nan]})
        held_out = pd.DataFrame({"value": [1000.0, np.nan]})
        preprocessor = build_preprocessor(config, "random_forest")
        preprocessor.fit(training)
        statistics = (
            preprocessor.named_transformers_["numeric"]
            .named_steps["imputer"]
            .statistics_
        )
        self.assertAlmostEqual(float(statistics[0]), 2.0)
        transformed = preprocessor.transform(held_out)
        self.assertAlmostEqual(float(transformed[1, 0]), 2.0)

    def test_unknown_categories_are_ignored(self) -> None:
        config = {"numeric_features": [], "categorical_features": ["category"]}
        training = pd.DataFrame({"category": ["a", "b", None]})
        held_out = pd.DataFrame({"category": ["unseen"]})
        preprocessor = build_preprocessor(config, "catboost")
        preprocessor.fit(training)
        transformed = preprocessor.transform(held_out)
        self.assertEqual(transformed.shape[0], 1)
        self.assertGreater(len(transformed_feature_names(preprocessor)), 0)


if __name__ == "__main__":
    unittest.main()

