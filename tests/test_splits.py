from __future__ import annotations

import unittest

import pytest

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.settings import get_dataset_config
from diabetes_pipeline.splitting.registry import validate_split_manifest
from diabetes_pipeline.splitting.strategies import build_split_manifest


class SplitTests(unittest.TestCase):
    @pytest.mark.local_research_data
    def test_pidd_repeated_split_is_reproducible(self) -> None:
        dataset = load_dataset("pidd")
        config = get_dataset_config("pidd")
        first = build_split_manifest(dataset, config, seed=42)
        second = build_split_manifest(dataset, config, seed=42)
        self.assertTrue(first.equals(second))
        validate_split_manifest(dataset, first, config)

    @pytest.mark.local_research_data
    def test_sylhet_profiles_do_not_cross_outer_folds(self) -> None:
        dataset = load_dataset("sylhet")
        config = get_dataset_config("sylhet")
        manifest = build_split_manifest(dataset, config, seed=42)
        validate_split_manifest(dataset, manifest, config)

    @pytest.mark.local_research_data
    def test_hospital_patients_never_cross_holdout_or_development_folds(self) -> None:
        dataset = load_dataset("hospital130")
        config = get_dataset_config("hospital130")
        manifest = build_split_manifest(dataset, config, seed=42)
        validate_split_manifest(dataset, manifest, config)
        development = manifest[manifest["role"] == "development"]
        test = manifest[manifest["role"] == "test"]
        self.assertFalse(set(development["group_id"]) & set(test["group_id"]))
        self.assertTrue(
            development.groupby("group_id")["outer_fold"].nunique().eq(1).all()
        )


if __name__ == "__main__":
    unittest.main()
