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

    def test_canonical_readiness_audit_matches_authoritative_primary_ids(self) -> None:
        declarations = yaml.safe_load(
            (ROOT / "config/authoritative_studies.yaml").read_text(encoding="utf-8")
        )["studies"]
        primary = yaml.safe_load(
            (ROOT / "config/publication_protocol.yaml").read_text(encoding="utf-8")
        )["primary_datasets"]
        audit = json.loads(
            (ROOT / "conference_package/qa/publication_readiness.json").read_text(
                encoding="utf-8"
            )
        )
        actual = {Path(path).name for path in audit["study_directories"]}
        expected = {declarations[name]["study_id"] for name in primary}
        self.assertEqual(actual, expected)
        markdown = (
            ROOT / "conference_package/qa/Publication_Readiness_Audit.md"
        ).read_text(encoding="utf-8")
        self.assertIn(f"**Blocking checks:** {audit['blocker_count']}", markdown)
        self.assertIn(f"**Warnings:** {audit['warning_count']}", markdown)

    def test_development_table_uses_primary_estimands(self) -> None:
        import pandas as pd

        table = pd.read_csv(
            ROOT / "conference_package/generated/development_model_performance.csv"
        )
        self.assertTrue(
            table[table["dataset"].isin(["pidd", "sylhet"])]["estimand"]
            .eq("participant_mean_across_repeats")
            .all()
        )
        self.assertTrue(table[table["dataset"].eq("pidd")]["n"].eq(768).all())
        self.assertTrue(table[table["dataset"].eq("sylhet")]["n"].eq(520).all())
        manuscript = (
            ROOT / "conference_package/Conference_Manuscript_Development_Draft.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("mean across 25 outer evaluations", manuscript)
        self.assertIn("PIDD calibrated participant-level", manuscript)
        self.assertIn("Sylhet calibrated participant-level", manuscript)


if __name__ == "__main__":
    unittest.main()
