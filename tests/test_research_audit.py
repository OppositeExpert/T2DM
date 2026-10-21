from __future__ import annotations

import unittest

import numpy as np

from diabetes_pipeline.data.research_audit import _safe_weighted_prevalence


class ResearchAuditTests(unittest.TestCase):
    def test_weighted_prevalence_uses_only_positive_finite_weights(self) -> None:
        y = np.asarray([0, 1, 1, 0], dtype=float)
        weights = np.asarray([1.0, 3.0, 0.0, np.nan], dtype=float)
        self.assertAlmostEqual(_safe_weighted_prevalence(y, weights), 0.75)

    def test_weighted_prevalence_is_nan_without_eligible_rows(self) -> None:
        result = _safe_weighted_prevalence(
            np.asarray([0, 1]), np.asarray([0.0, np.nan])
        )
        self.assertTrue(np.isnan(result))


if __name__ == "__main__":
    unittest.main()
