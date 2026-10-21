from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd
import yaml
import matplotlib

from diabetes_pipeline.publication.exporter import (
    _attach_endpoint_context,
    _latex_table,
)
from diabetes_pipeline.publication.figure import _attach_dataset_identity
from diabetes_pipeline.publication.governance import (
    assert_final_internal_validation_authorized,
    final_protocol_sha256,
    validate_final_internal_profile,
)
from diabetes_pipeline.settings import ConfigurationError, load_experiment_profile


class FinalPublicationGovernanceTests(unittest.TestCase):
    def test_publication_figure_uses_noninteractive_backend(self) -> None:
        self.assertEqual(matplotlib.get_backend().lower(), "agg")

    def test_figure_preserves_existing_matching_dataset_identity(self) -> None:
        frame = pd.DataFrame({"dataset": ["brfss"], "score": [0.8]})
        result = _attach_dataset_identity(frame, "brfss")
        self.assertEqual(result.columns.tolist().count("dataset"), 1)

    def test_figure_rejects_contradictory_dataset_identity(self) -> None:
        frame = pd.DataFrame({"dataset": ["hospital130"]})
        with self.assertRaisesRegex(RuntimeError, "contradictory dataset"):
            _attach_dataset_identity(frame, "brfss")

    def test_exporter_latex_does_not_require_optional_jinja(self) -> None:
        result = _latex_table(
            pd.DataFrame({"model_name": ["random_forest"], "score": [0.81234]})
        )
        self.assertIn(r"model\_name", result)
        self.assertIn(r"random\_forest", result)
        self.assertIn("0.8123", result)
        self.assertIn(r"\end{tabular}", result)

    def test_exporter_attaches_endpoint_context_without_duplicate_columns(self) -> None:
        frame = pd.DataFrame(
            {
                "dataset": ["brfss"],
                "task": ["classification"],
                "endpoint": ["diabetes_status"],
                "auroc": [0.8],
            }
        )
        result = _attach_endpoint_context(
            frame,
            dataset="brfss",
            task="classification",
            endpoint="diabetes_status",
        )
        self.assertEqual(
            list(result.columns),
            ["dataset", "task", "endpoint", "auroc"],
        )
        self.assertEqual(result.columns.tolist().count("endpoint"), 1)

    def test_exporter_rejects_contradictory_endpoint_context(self) -> None:
        frame = pd.DataFrame({"endpoint": ["readmission_within_30_days"]})
        with self.assertRaisesRegex(RuntimeError, "contradictory endpoint"):
            _attach_endpoint_context(
                frame,
                dataset="brfss",
                task="classification",
                endpoint="diabetes_status",
            )

    def test_final_internal_profile_has_unreduced_frozen_budgets(self) -> None:
        profile = load_experiment_profile("final_internal_validation")
        validate_final_internal_profile(profile)
        self.assertEqual(profile["n_trials"], 75)
        self.assertEqual(profile["n_bootstrap"], 2000)
        self.assertTrue(profile["locked"])
        self.assertTrue(all(value is None for value in profile["sample_limits"].values()))

    def test_final_internal_profile_rejects_reduced_budget(self) -> None:
        profile = load_experiment_profile("final_internal_validation")
        with self.assertRaisesRegex(ConfigurationError, "n_trials"):
            validate_final_internal_profile({**profile, "n_trials": 74})

    def test_authorization_binds_protocol_data_split_source_and_analysis(self) -> None:
        profile = load_experiment_profile("final_internal_validation")
        protocol = {
            "protocol_id": "fixture-v1",
            "protocol_sha256": None,
            "status": "frozen",
            "profile": {"name": "final_internal_validation"},
            "evaluation_strategies": {"brfss": "internal_validation_only"},
            "datasets": {"brfss": {"independent_holdout": False}},
            "frozen_bindings": {
                "raw_data_sha256": {"brfss": "raw"},
                "split_manifest_sha256": {"brfss": "split"},
                "dataset_configuration_sha256": {"brfss": "dataset"},
                "analysis_configuration_sha256": {"brfss": "analysis"},
                "source_tree_sha256": "source",
                "requirements_lock_sha256": "requirements",
            },
            "execution": {"authorized": True},
        }
        protocol["protocol_sha256"] = final_protocol_sha256(protocol)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "protocol.yaml"
            path.write_text(yaml.safe_dump(protocol), encoding="utf-8")
            protocol_id = assert_final_internal_validation_authorized(
                dataset_name="brfss",
                profile=profile,
                models=[
                    "logistic_regression",
                    "random_forest",
                    "xgboost",
                    "lightgbm",
                    "catboost",
                ],
                raw_data_sha256="raw",
                split_manifest_sha256="split",
                dataset_configuration_sha256="dataset",
                analysis_configuration_sha256="analysis",
                source_tree_sha256="source",
                requirements_lock_sha256="requirements",
                protocol_path=path,
            )
            self.assertEqual(protocol_id, "fixture-v1")
            with self.assertRaisesRegex(RuntimeError, "raw_data_sha256"):
                assert_final_internal_validation_authorized(
                    dataset_name="brfss",
                    profile=profile,
                    models=[
                        "logistic_regression",
                        "random_forest",
                        "xgboost",
                        "lightgbm",
                        "catboost",
                    ],
                    raw_data_sha256="changed",
                    split_manifest_sha256="split",
                    dataset_configuration_sha256="dataset",
                    analysis_configuration_sha256="analysis",
                    source_tree_sha256="source",
                    requirements_lock_sha256="requirements",
                    protocol_path=path,
                )


if __name__ == "__main__":
    unittest.main()
