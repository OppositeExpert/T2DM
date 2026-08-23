from __future__ import annotations

import unittest

import numpy as np

from diabetes_pipeline.evaluation.missingness_stress import generate_missing_mask


class MissingnessStressTests(unittest.TestCase):
    def test_mcar_masks_are_reproducible_and_retain_a_feature(self) -> None:
        first = generate_missing_mask(100, 8, severity=0.75, mechanism="mcar_independent", seed=42)
        second = generate_missing_mask(100, 8, severity=0.75, mechanism="mcar_independent", seed=42)
        self.assertTrue(np.array_equal(first, second))
        self.assertFalse(first.all(axis=1).any())

    def test_structured_block_masks_identical_columns_for_every_row(self) -> None:
        mask = generate_missing_mask(10, 8, severity=0.5, mechanism="structured_block", seed=42)
        self.assertTrue(np.array_equal(mask, np.repeat(mask[:1], 10, axis=0)))
        self.assertEqual(int(mask[0].sum()), 4)

    def test_invalid_severity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "severity"):
            generate_missing_mask(5, 3, severity=1.0, mechanism="mcar_independent", seed=42)


if __name__ == "__main__":
    unittest.main()
