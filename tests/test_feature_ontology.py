from __future__ import annotations

import unittest

from diabetes_pipeline.features.ontology import build_feature_dictionary
from diabetes_pipeline.settings import load_dataset_registry


class FeatureOntologyTests(unittest.TestCase):
    def test_every_configured_feature_is_covered_once(self) -> None:
        frame, ontology = build_feature_dictionary()
        registry = load_dataset_registry()
        expected = sum(
            len(cfg["numeric_features"] + cfg["categorical_features"])
            for cfg in registry.values()
        )
        self.assertEqual(len(frame), expected)
        self.assertFalse(frame[["dataset", "dataset_feature"]].duplicated().any())
        self.assertEqual(
            set(frame["dataset"]), {"pidd", "sylhet", "brfss", "hospital130"}
        )
        self.assertEqual(
            ontology["endpoint_contracts"]["hospital_readmission"][
                "probability_pooling"
            ],
            "prohibited",
        )

    def test_similarly_named_measurements_retain_distinct_semantics(self) -> None:
        frame, _ = build_feature_dictionary()
        insulin = frame[frame["canonical_feature"] == "insulin"].set_index(
            "dataset"
        )
        self.assertEqual(insulin.loc["pidd", "relation"], "direct")
        self.assertEqual(insulin.loc["hospital130", "relation"], "not_comparable")
        self.assertNotEqual(
            insulin.loc["pidd", "measurement_scale"],
            insulin.loc["hospital130", "measurement_scale"],
        )


if __name__ == "__main__":
    unittest.main()
