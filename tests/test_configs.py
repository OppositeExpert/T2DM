from __future__ import annotations

import unittest

import pytest

import yaml

from diabetes_pipeline.settings import (
    PROJECT_ROOT,
    load_dataset_registry,
    load_experiment_profile,
)


class ConfigurationTests(unittest.TestCase):
    @pytest.mark.local_research_data
    def test_all_dataset_contracts_load(self) -> None:
        registry = load_dataset_registry()
        self.assertEqual(set(registry), {"brfss", "pidd", "sylhet", "hospital130"})
        for config in registry.values():
            self.assertTrue(config["raw_path"].exists())
            self.assertTrue(config["numeric_features"] or config["categorical_features"])
        self.assertEqual(registry["brfss"]["target_encoding"]["positive_raw_values"], [1])
        self.assertIn(4, registry["brfss"]["target_encoding"]["excluded_raw_values"])

    def test_experiment_profiles_load(self) -> None:
        for name in ("smoke", "development", "final"):
            profile = load_experiment_profile(name)
            self.assertEqual(profile["name"], name)
            self.assertGreater(profile["n_trials"], 0)

    def test_draft_publication_protocol_cannot_authorize_final_execution(self) -> None:
        protocol = yaml.safe_load(
            (PROJECT_ROOT / "config" / "publication_protocol.yaml").read_text(
                encoding="utf-8"
            )
        )
        final_profile = load_experiment_profile("final")
        analysis_plan = protocol["analysis_plan"]

        self.assertEqual(analysis_plan["status"], "draft_unlocked")
        self.assertFalse(protocol["protocol_frozen"])
        self.assertFalse(analysis_plan["final_execution_authorized"])
        self.assertFalse(analysis_plan["final_split_creation_authorized"])
        self.assertIsNone(analysis_plan["final_holdout_seed"])
        self.assertIsNone(analysis_plan["final_holdout_manifest"])
        self.assertIsNone(analysis_plan["final_holdout_manifest_sha256"])
        self.assertEqual(analysis_plan["final_raw_data_sha256"], {})
        self.assertEqual(analysis_plan["final_analysis_configuration_sha256"], {})
        self.assertIsNone(analysis_plan["final_authorization_record"])
        self.assertIsNone(analysis_plan["final_authorization_record_sha256"])
        self.assertFalse(final_profile["locked"])

    def test_every_dataset_has_a_valid_availability_contract(self) -> None:
        registry = load_dataset_registry()
        payload = yaml.safe_load(
            (PROJECT_ROOT / "config" / "availability_scenarios.yaml").read_text(
                encoding="utf-8"
            )
        )
        routing = payload["datasets"]
        self.assertEqual(set(routing), set(registry))
        for name, dataset in registry.items():
            configured = set(
                dataset["numeric_features"] + dataset["categorical_features"]
            )
            scenarios = routing[name]["scenarios"]
            self.assertEqual(
                set(scenarios["full"]["available_features"]), configured
            )
            for scenario in scenarios.values():
                available = set(scenario["available_features"])
                self.assertTrue(available)
                self.assertFalse(available - configured)

    def test_development_evidence_role_cannot_imply_final_lock(self) -> None:
        schema = yaml.safe_load(
            (PROJECT_ROOT / "config/output_schemas.yaml").read_text(encoding="utf-8")
        )
        roles = schema["evaluation_roles_by_evidence_tier"]
        self.assertEqual(roles["full_development"], "development_test")
        self.assertEqual(roles["final_locked"], "locked_final_test")
        self.assertNotEqual(roles["full_development"], roles["final_locked"])


if __name__ == "__main__":
    unittest.main()
