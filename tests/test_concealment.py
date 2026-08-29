from __future__ import annotations

import unittest
import hashlib
import json
import tempfile
from pathlib import Path

import pandas as pd
import yaml

from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.settings import get_dataset_config, load_experiment_profile
from diabetes_pipeline.splitting.concealment import (
    assert_final_execution_authorized,
    final_analysis_configuration_sha256,
    sanitize_holdout_manifest,
    write_final_concealed_manifest,
)


class ConcealmentTests(unittest.TestCase):
    def _authorized_fixture(self, root: Path) -> tuple[Path, dict[str, object], Path]:
        manifest_path = root / "final.csv"
        manifest = pd.DataFrame(
            {
                "dataset": ["example", "example"],
                "strategy": ["stratified_holdout_cv"] * 2,
                "row_position": [0, 1],
                "row_id": ["a", "b"],
                "group_id": ["", ""],
                "role": ["development", "test"],
                "repeat": [0, 0],
                "outer_fold": [0, -1],
                "inner_seed": [901, 901],
                "seed": [901, 901],
            }
        )
        manifest.to_csv(manifest_path, index=False)
        manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        metadata = {
            "schema_version": "1.0",
            "dataset": "example",
            "strategy": "stratified_holdout_cv",
            "seed": 901,
            "purpose": "final_locked_holdout",
            "outcome_blind": True,
            "rows": 2,
            "role_rows": {"development": 1, "test": 1},
            "role_groups": {"development": None, "test": None},
            "manifest_sha256": manifest_sha,
        }
        manifest_path.with_suffix(".json").write_text(json.dumps(metadata))
        authorization = root / "authorization.txt"
        authorization.write_text("approved by accountable investigators\n")
        authorization_sha = hashlib.sha256(authorization.read_bytes()).hexdigest()
        protocol = {
            "protocol_frozen": True,
            "novelty_review_complete": True,
            "ablation_study_complete": True,
            "selective_prediction_evaluation_complete": True,
            "subgroup_analysis_complete": True,
            "analysis_plan": {
                "status": "frozen",
                "final_execution_authorized": True,
                "final_holdout_seed": 901,
                "final_holdout_manifest": str(manifest_path),
                "final_holdout_manifest_sha256": manifest_sha,
                "final_raw_data_sha256": {"example": "raw-sha"},
                "final_analysis_configuration_sha256": {"example": "analysis-sha"},
                "final_authorization_record": str(authorization),
                "final_authorization_record_sha256": authorization_sha,
            },
        }
        protocol_path = root / "protocol.yaml"
        protocol_path.write_text(yaml.safe_dump(protocol))
        return protocol_path, {"name": "final", "seed": 901, "locked": True}, manifest_path

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
        with self.assertRaisesRegex(RuntimeError, "Final study execution denied"):
            assert_final_execution_authorized(
                profile_name="final",
                profile=profile,
            )

    def test_current_protocol_denies_final_manifest_creation(self) -> None:
        profile = load_experiment_profile("final")
        with self.assertRaisesRegex(RuntimeError, "Final manifest creation denied"):
            write_final_concealed_manifest(None, profile=profile)  # type: ignore[arg-type]

    def test_analysis_fingerprint_binds_model_bank_and_profile(self) -> None:
        config = get_dataset_config("brfss")
        profile = load_experiment_profile("final")
        five_models = final_analysis_configuration_sha256(
            dataset_name="brfss",
            dataset_config=config,
            profile=profile,
            models=[
                "logistic_regression",
                "random_forest",
                "xgboost",
                "lightgbm",
                "catboost",
            ],
        )
        four_models = final_analysis_configuration_sha256(
            dataset_name="brfss",
            dataset_config=config,
            profile=profile,
            models=["random_forest", "xgboost", "lightgbm", "catboost"],
        )
        changed_profile = final_analysis_configuration_sha256(
            dataset_name="brfss",
            dataset_config=config,
            profile={**profile, "n_trials": int(profile["n_trials"]) + 1},
            models=[
                "logistic_regression",
                "random_forest",
                "xgboost",
                "lightgbm",
                "catboost",
            ],
        )
        self.assertNotEqual(five_models, four_models)
        self.assertNotEqual(five_models, changed_profile)

    def test_smoke_path_does_not_require_final_authorization(self) -> None:
        profile = load_experiment_profile("smoke")
        self.assertIsNone(
            assert_final_execution_authorized(
                profile_name="smoke",
                profile=profile,
            )
        )

    def test_fully_bound_final_authorization_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            protocol, profile, manifest = self._authorized_fixture(Path(temporary))
            self.assertEqual(
                assert_final_execution_authorized(
                    profile_name="final",
                    profile=profile,
                    dataset_name="example",
                    raw_data_sha256="raw-sha",
                    analysis_configuration_sha256="analysis-sha",
                    protocol_path=protocol,
                ),
                manifest.resolve(),
            )

    def test_authorized_nested_final_does_not_require_holdout_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            protocol, profile, _ = self._authorized_fixture(Path(temporary))
            self.assertIsNone(
                assert_final_execution_authorized(
                    profile_name="final",
                    profile=profile,
                    dataset_name="example",
                    raw_data_sha256="raw-sha",
                    analysis_configuration_sha256="analysis-sha",
                    requires_concealed_holdout=False,
                    protocol_path=protocol,
                )
            )

    def test_final_manifest_creation_is_outcome_blind_and_non_overwritable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol_path = root / "protocol.yaml"
            protocol_path.write_text(
                yaml.safe_dump(
                    {
                        "protocol_frozen": True,
                        "analysis_plan": {
                            "status": "frozen",
                            "final_split_creation_authorized": True,
                            "final_execution_authorized": False,
                            "final_holdout_seed": 901,
                            "final_holdout_manifest": None,
                            "final_holdout_manifest_sha256": None,
                        },
                    }
                )
            )
            n = 100
            dataset = LoadedDataset(
                name="brfss",
                X=pd.DataFrame({"placeholder": range(n)}),
                y=pd.Series([0, 1] * (n // 2)),
                row_ids=pd.Series([f"row-{index}" for index in range(n)]),
            )
            profile = {"name": "final", "seed": 901, "locked": True}
            manifest, metadata_path, metadata = write_final_concealed_manifest(
                dataset,
                profile=profile,
                protocol_path=protocol_path,
                output_root=root / "outputs",
            )
            self.assertNotIn("target", pd.read_csv(manifest, nrows=0).columns)
            self.assertEqual(metadata["purpose"], "final_locked_holdout")
            self.assertTrue(metadata_path.exists())
            with self.assertRaisesRegex(RuntimeError, "overwrite is prohibited"):
                write_final_concealed_manifest(
                    dataset,
                    profile=profile,
                    protocol_path=protocol_path,
                    output_root=root / "outputs",
                )

    def test_final_authorization_rejects_changed_data_or_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            protocol, profile, _ = self._authorized_fixture(Path(temporary))
            for raw_sha, analysis_sha, message in (
                ("changed", "analysis-sha", "raw-data SHA-256"),
                ("raw-sha", "changed", "analysis-configuration SHA-256"),
            ):
                with self.subTest(message=message), self.assertRaisesRegex(RuntimeError, message):
                    assert_final_execution_authorized(
                        profile_name="final",
                        profile=profile,
                        dataset_name="example",
                        raw_data_sha256=raw_sha,
                        analysis_configuration_sha256=analysis_sha,
                        protocol_path=protocol,
                    )

    def test_final_authorization_rejects_development_profile_disguised_as_final(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            protocol, profile, _ = self._authorized_fixture(Path(temporary))
            profile["name"] = "development"
            with self.assertRaisesRegex(RuntimeError, "not named final"):
                assert_final_execution_authorized(
                    profile_name="final",
                    profile=profile,
                    dataset_name="example",
                    raw_data_sha256="raw-sha",
                    analysis_configuration_sha256="analysis-sha",
                    protocol_path=protocol,
                )

    def test_final_authorization_rejects_wrong_seed_and_manifest_purpose(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol_path, profile, manifest_path = self._authorized_fixture(root)
            wrong_seed = dict(profile, seed=42)
            with self.assertRaisesRegex(RuntimeError, "profile seed"):
                assert_final_execution_authorized(
                    profile_name="final",
                    profile=wrong_seed,
                    dataset_name="example",
                    raw_data_sha256="raw-sha",
                    analysis_configuration_sha256="analysis-sha",
                    protocol_path=protocol_path,
                )
            metadata_path = manifest_path.with_suffix(".json")
            metadata = json.loads(metadata_path.read_text())
            metadata["purpose"] = "development_control_test_only"
            metadata_path.write_text(json.dumps(metadata))
            with self.assertRaisesRegex(RuntimeError, "purpose"):
                assert_final_execution_authorized(
                    profile_name="final",
                    profile=profile,
                    dataset_name="example",
                    raw_data_sha256="raw-sha",
                    analysis_configuration_sha256="analysis-sha",
                    protocol_path=protocol_path,
                )

    def test_final_authorization_rejects_changed_authorization_record(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol_path, profile, _ = self._authorized_fixture(root)
            payload = yaml.safe_load(protocol_path.read_text())
            Path(payload["analysis_plan"]["final_authorization_record"]).write_text("changed\n")
            with self.assertRaisesRegex(RuntimeError, "authorization record checksum"):
                assert_final_execution_authorized(
                    profile_name="final",
                    profile=profile,
                    dataset_name="example",
                    raw_data_sha256="raw-sha",
                    analysis_configuration_sha256="analysis-sha",
                    protocol_path=protocol_path,
                )

    def test_final_authorization_rejects_modified_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            protocol_path, profile, manifest_path = self._authorized_fixture(root)
            manifest = pd.read_csv(manifest_path)
            manifest.loc[0, "row_id"] = "altered"
            manifest.to_csv(manifest_path, index=False)
            with self.assertRaisesRegex(RuntimeError, "checksum"):
                assert_final_execution_authorized(
                    profile_name="final",
                    profile=profile,
                    dataset_name="example",
                    raw_data_sha256="raw-sha",
                    analysis_configuration_sha256="analysis-sha",
                    protocol_path=protocol_path,
                )


if __name__ == "__main__":
    unittest.main()
