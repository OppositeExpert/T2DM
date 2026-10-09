from __future__ import annotations

import json
import importlib.util
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class ReleaseGovernanceTests(unittest.TestCase):
    def test_role_migration_only_changes_exact_legacy_label(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "migrate_roles", ROOT / "scripts/migrate_development_evaluation_roles.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        payload = {
            "evaluation_role": "locked_test",
            "historical_note": "locked_test was the original label",
            "nested": ["locked_test", "locked_final_test"],
        }
        self.assertEqual(
            module._replace_json(payload),
            {
                "evaluation_role": "development_test",
                "historical_note": "locked_test was the original label",
                "nested": ["development_test", "locked_final_test"],
            },
        )

    def test_canonical_final_results_match_authoritative_ids_and_claim_boundary(self) -> None:
        declarations = yaml.safe_load(
            (ROOT / "config/authoritative_studies.yaml").read_text(encoding="utf-8")
        )["studies"]
        registry = json.loads(
            (ROOT / "evidence/study_registry.json").read_text(encoding="utf-8")
        )
        actual = {
            dataset: study["study_id"]
            for dataset, study in registry["studies"].items()
        }
        expected = {
            dataset: declaration["study_id"]
            for dataset, declaration in declarations.items()
        }
        self.assertEqual(actual, expected)
        self.assertFalse(registry["independent_holdout_claim_allowed"])
        final_path = ROOT / "results/final_publication/FINAL_RESULTS.json"
        if final_path.is_file():
            final_results = json.loads(final_path.read_text(encoding="utf-8"))
            self.assertEqual(
                {
                    dataset: study["experiment_id"]
                    for dataset, study in final_results["studies"].items()
                },
                expected,
            )
            self.assertFalse(final_results["independent_holdout_claim_allowed"])
            self.assertTrue(final_results["datasets_are_endpoint_separated"])
            self.assertFalse(final_results["cross_cohort_probability_pooling"])
            self.assertFalse(
                final_results["dynamic_model_switching"][
                    "multiplicity_corrected_superiority_established"
                ]
            )

    def test_development_table_uses_primary_estimands(self) -> None:
        import pandas as pd

        table = pd.read_csv(
            ROOT / "evidence/development_reference/development_model_performance.csv"
        )
        self.assertTrue(
            table[table["dataset"].isin(["pidd", "sylhet"])]["estimand"]
            .eq("participant_mean_across_repeats")
            .all()
        )
        self.assertTrue(table[table["dataset"].eq("pidd")]["n"].eq(768).all())
        self.assertTrue(table[table["dataset"].eq("sylhet")]["n"].eq(520).all())
        manuscript = (
            ROOT / "docs/MANUSCRIPT_REVIEW.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("mean across 25 outer evaluations", manuscript)
        self.assertIn("PIDD calibrated participant-level", manuscript)
        self.assertIn("Sylhet calibrated participant-level", manuscript)


if __name__ == "__main__":
    unittest.main()
