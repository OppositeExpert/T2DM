from __future__ import annotations

import unittest

import pandas as pd

from diabetes_pipeline.settings import load_experiment_profile
from diabetes_pipeline.splitting.concealment import (
    assert_final_execution_authorized,
    sanitize_holdout_manifest,
)


class ConcealmentTests(unittest.TestCase):
    def test_sanitized_manifest_has_no_outcome_column(self) -> None:
        manifest = pd.DataFrame(
            {
                "dataset": ["example", "example"],
                "strategy": ["stratified_holdout_cv"] * 2,
                "row_position": [0, 1],
                "row_id": ["a", "b"],
                "group_id": ["", ""],
                "target": [0, 1],
                "role": ["development", "test"],
                "repeat": [0, 0],
                "outer_fold": [0, -1],
                "inner_seed": [42, 42],
                "seed": [42, 42],
            }
        )
        safe = sanitize_holdout_manifest(manifest)
        self.assertNotIn("target", safe.columns)
        self.assertEqual(set(safe["role"]), {"development", "test"})

    def test_current_protocol_denies_final_execution(self) -> None:
        profile = load_experiment_profile("final")
        with self.assertRaisesRegex(RuntimeError, "Final holdout access denied"):
            assert_final_execution_authorized(
                profile_name="final",
                profile=profile,
            )

    def test_smoke_path_does_not_require_final_authorization(self) -> None:
        profile = load_experiment_profile("smoke")
        self.assertIsNone(
            assert_final_execution_authorized(
                profile_name="smoke",
                profile=profile,
            )
        )


if __name__ == "__main__":
    unittest.main()
