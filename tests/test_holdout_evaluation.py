from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from diabetes_pipeline.evaluation.bootstrap import bootstrap_index_samples
from diabetes_pipeline.evaluation.comparisons import (
    paired_bootstrap_model_comparisons,
)
from diabetes_pipeline.holdout_runner import (
    _claim_final_test_access,
    _holdout_evidence_tier,
    _predefined_development_splits,
)
from diabetes_pipeline.training.tuning import cross_fitted_probabilities
from diabetes_pipeline.runner import (
    _claim_final_nested_execution,
    _nested_evidence_tier,
)


class HoldoutEvaluationTests(unittest.TestCase):
    def test_nested_evidence_tiers_are_explicit_and_fail_closed(self) -> None:
        self.assertEqual(_nested_evidence_tier("smoke", {}), "execution_only_smoke")
        self.assertEqual(
            _nested_evidence_tier("development_pilot", {}), "development_pilot"
        )
        self.assertEqual(_nested_evidence_tier("development", {}), "full_development")
        self.assertEqual(
            _nested_evidence_tier("final", {"locked": True}), "final_locked"
        )
        with self.assertRaises(ValueError):
            _nested_evidence_tier("final", {"locked": False})

    def test_final_nested_execution_receipt_is_one_time_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            receipt = _claim_final_nested_execution(
                "pidd", "a" * 64, output_root=output_root
            )
            self.assertTrue(receipt.exists())
            with self.assertRaisesRegex(RuntimeError, "already started"):
                _claim_final_nested_execution(
                    "pidd", "a" * 64, output_root=output_root
                )

    def test_holdout_evidence_tiers_are_explicit_and_fail_closed(self) -> None:
        self.assertEqual(_holdout_evidence_tier("smoke", {}), "execution_only_smoke")
        self.assertEqual(_holdout_evidence_tier("development", {}), "full_development")
        self.assertEqual(
            _holdout_evidence_tier("final", {"locked": True}), "final_locked"
        )
        with self.assertRaises(ValueError):
            _holdout_evidence_tier("development_pilot", {})
        with self.assertRaises(ValueError):
            _holdout_evidence_tier("final", {"locked": False})

    def test_final_test_access_receipt_is_one_time_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            receipt = _claim_final_test_access(output_dir, "final-study")
            self.assertTrue(receipt.exists())
            with self.assertRaisesRegex(RuntimeError, "already started"):
                _claim_final_test_access(output_dir, "final-study")
    def test_predefined_manifest_folds_cover_every_development_row(self) -> None:
        manifest = pd.DataFrame(
            {
                "outer_fold": [0, 0, 1, 1, 2, 2],
                "target": [0, 1, 0, 1, 0, 1],
            }
        )
        splits = _predefined_development_splits(manifest)
        validation = np.concatenate([fold for _, fold in splits])
        np.testing.assert_array_equal(np.sort(validation), np.arange(6))

        X = pd.DataFrame({"x": [-2.0, 2.0, -1.5, 1.5, -1.0, 1.0]})
        y = manifest["target"].to_numpy()
        probability = cross_fitted_probabilities(
            X,
            y,
            {"numeric_features": ["x"], "categorical_features": []},
            "logistic_regression",
            {"C": 1.0, "l1_ratio": 0.0, "class_weight": None},
            n_splits=3,
            seed=42,
            predefined_splits=splits,
        )
        self.assertTrue(np.isfinite(probability).all())

    def test_cluster_bootstrap_resamples_complete_clusters(self) -> None:
        y = np.array([0, 0, 1, 1, 0, 1])
        groups = np.array(["a", "a", "b", "b", "c", "c"])
        samples = bootstrap_index_samples(
            y, n_bootstrap=10, seed=42, groups=groups
        )
        for indexes in samples:
            counts = np.bincount(indexes, minlength=len(y))
            self.assertEqual(counts[0], counts[1])
            self.assertEqual(counts[2], counts[3])
            self.assertEqual(counts[4], counts[5])

    def test_paired_bootstrap_comparison_preserves_pairing(self) -> None:
        y = np.array([0, 1] * 20)
        probability = np.linspace(0.05, 0.95, len(y))
        rows = []
        for model in ("a", "b"):
            rows.append(
                pd.DataFrame(
                    {
                        "model": model,
                        "row_id": [f"row:{i}" for i in range(len(y))],
                        "target": y,
                        "probability_calibrated": probability,
                    }
                )
            )
        result = paired_bootstrap_model_comparisons(
            pd.concat(rows, ignore_index=True), n_bootstrap=20, seed=42
        )
        self.assertTrue(
            np.allclose(result["observed_difference_a_minus_b"], 0.0)
        )
        self.assertTrue(np.allclose(result["paired_bootstrap_p_value"], 1.0))

        one_model = paired_bootstrap_model_comparisons(
            rows[0], n_bootstrap=5, seed=42
        )
        self.assertTrue(one_model.empty)
        self.assertIn("metric", one_model.columns)


if __name__ == "__main__":
    unittest.main()
