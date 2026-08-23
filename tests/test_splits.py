from __future__ import annotations

import unittest

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.settings import get_dataset_config
from diabetes_pipeline.splitting.registry import validate_split_manifest
from diabetes_pipeline.splitting.strategies import build_split_manifest


class SplitTests(unittest.TestCase):
    def test_pidd_repeated_split_is_reproducible(self) -> None:
        dataset = load_dataset("pidd")
        config = get_dataset_config("pidd")
        first = build_split_manifest(dataset, config, seed=42)
        second = build_split_manifest(dataset, config, seed=42)
        self.assertTrue(first.equals(second))
        validate_split_manifest(dataset, first, config)

    def test_sylhet_profiles_do_not_cross_outer_folds(self) -> None:
        dataset = load_dataset("sylhet")
        config = get_dataset_config("sylhet")
        manifest = build_split_manifest(dataset, config, seed=42)
        validate_split_manifest(dataset, manifest, config)


if __name__ == "__main__":
    unittest.main()

