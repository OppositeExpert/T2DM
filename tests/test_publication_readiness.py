from __future__ import annotations

import unittest

from diabetes_pipeline.reporting.publication_readiness import (
    audit_publication_readiness,
    render_publication_readiness_markdown,
)
from diabetes_pipeline.settings import DEFAULT_OUTPUT_ROOT


class PublicationReadinessTests(unittest.TestCase):
    def test_current_development_and_smoke_artifacts_cannot_pass_gate(self) -> None:
        studies = DEFAULT_OUTPUT_ROOT / "studies"
        result = audit_publication_readiness(
            [
                studies / "pidd_development_pilot_27b9bc88b493",
                studies / "sylhet_development_pilot_ed7c05460503",
                studies / "brfss_smoke_holdout_1f1344dceb63",
            ]
        )
        self.assertEqual(result["status"], "not_ready")
        self.assertFalse(result["ready_for_submission"])
        self.assertIn("brfss_final_profile", result["blockers"])
        self.assertIn("brfss_full_sample", result["blockers"])
        self.assertIn("protocol_frozen", result["blockers"])
        brfss_artifacts = next(
            check
            for check in result["checks"]
            if check["id"] == "brfss_required_artifacts"
        )
        self.assertIn("survey_weighted_metrics.csv", brfss_artifacts["evidence"])
        self.assertNotIn(
            "missing_indicator_retraining", brfss_artifacts["evidence"]
        )
        rendered = render_publication_readiness_markdown(result)
        self.assertIn("NOT READY", rendered)
        self.assertIn("TRIPOD", rendered)


if __name__ == "__main__":
    unittest.main()
