from __future__ import annotations

import unittest

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.data.validators import validate_dataset
from diabetes_pipeline.settings import get_dataset_config


class DataValidationTests(unittest.TestCase):
    def test_small_datasets_load_without_global_imputation(self) -> None:
        pidd = load_dataset("pidd")
        validate_dataset(pidd, get_dataset_config("pidd"))
        self.assertGreater(int(pidd.X.isna().sum().sum()), 0)

        sylhet = load_dataset("sylhet")
        validate_dataset(sylhet, get_dataset_config("sylhet"))
        self.assertIsNotNone(sylhet.groups)
        self.assertLess(sylhet.groups.nunique(), len(sylhet.X))

    def test_hospital_cohort_excludes_non_readmission_dispositions(self) -> None:
        hospital = load_dataset("hospital130")
        config = get_dataset_config("hospital130")
        validate_dataset(hospital, config)
        self.assertEqual(len(hospital.X), 99_343)
        self.assertIn("discharge_disposition_id", config["categorical_features"])
        self.assertNotIn("discharge_disposition_id", config["numeric_features"])
        excluded = {"11", "13", "14", "19", "20", "21"}
        self.assertFalse(
            set(hospital.X["discharge_disposition_id"].dropna()) & excluded
        )


if __name__ == "__main__":
    unittest.main()
