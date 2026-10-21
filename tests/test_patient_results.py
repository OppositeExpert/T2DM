from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from diabetes_pipeline.calibration.calibrators import IdentityCalibrator
from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.models.registry import build_estimator
from diabetes_pipeline.preprocessing.builders import (
    build_preprocessor,
    transformed_feature_names,
)
from diabetes_pipeline.reporting.patient_results import (
    generate_patient_result,
    render_patient_result_markdown,
)
from diabetes_pipeline.reporting.mixed_patient_results import (
    generate_mixed_patient_result,
    render_mixed_patient_result_markdown,
)


DATASET_CONFIG = {
    "numeric_features": ["a", "b"],
    "categorical_features": [],
}


def _fixture() -> tuple[list[dict], LoadedDataset]:
    X = pd.DataFrame(
        {
            "a": [-2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0] * 5,
            "b": [0.0, 1.0] * 20,
        }
    )
    y = pd.Series([0, 0, 0, 0, 1, 1, 1, 1] * 5, name="outcome")
    reference = LoadedDataset(
        name="fixture",
        X=X,
        y=y,
        row_ids=pd.Series([f"row:{i}" for i in range(len(X))], name="row_id"),
        metadata={
            "display_name": "Fixture cohort",
            "endpoint": "fixture_endpoint",
            "applicability_notes": ["Test data only."],
        },
    )
    preprocessor = build_preprocessor(DATASET_CONFIG, "random_forest")
    transformed = preprocessor.fit_transform(X)
    model = build_estimator(
        "random_forest",
        {"n_estimators": 20, "max_depth": 3},
        seed=42,
    )
    model.fit(transformed, y.to_numpy())
    model_bundle = {
        "model_name": "random_forest",
        "preprocessor": preprocessor,
        "transformed_feature_names": transformed_feature_names(preprocessor),
        "model": model,
    }
    router = {
        "experiment_id": "fixture_study",
        "repeat": 0,
        "outer_fold": 0,
        "configured_features": ["a", "b"],
        "scenarios": {"full": ["a", "b"], "a_only": ["a"]},
        "selected_models": {
            "full": "random_forest",
            "a_only": "random_forest",
        },
        "model_bundles": {"random_forest": model_bundle},
        "scenario_calibrators": {
            "random_forest": {
                "full": IdentityCalibrator(),
                "a_only": IdentityCalibrator(),
            }
        },
        "threshold": 0.5,
        "threshold_policy": "fixed_0_5",
    }
    second = dict(router)
    second["outer_fold"] = 1
    return [router, second], reference


class PatientResultTests(unittest.TestCase):
    def test_probability_first_result_contains_ensemble_shap_and_context(self) -> None:
        routers, reference = _fixture()
        result = generate_patient_result(
            routers,
            pd.DataFrame([{"a": 1.25, "b": 1.0}]),
            reference,
            top_k=2,
        )
        self.assertEqual(result["status"], "predicted")
        self.assertEqual(
            result["feature_availability"]["selected_scenario"], "full"
        )
        self.assertEqual(
            result["probability_result"]["number_of_model_folds"], 2
        )
        self.assertEqual(len(result["explanation"]["top_observed_factors"]), 2)
        self.assertTrue(result["cohort_context"]["comparisons"])
        maximum_error = max(
            row["maximum_additivity_error"]
            for row in result["explanation"]["additivity_checks"]
        )
        self.assertLess(maximum_error, 1e-4)
        rendered = render_patient_result_markdown(result)
        self.assertIn("Estimated calibrated probability", rendered)
        self.assertIn("Strongest model factors", rendered)

    def test_missing_panel_and_out_of_range_inputs_abstain(self) -> None:
        routers, reference = _fixture()
        no_panel = generate_patient_result(
            routers,
            pd.DataFrame([{"a": np.nan, "b": 1.0}]),
            reference,
        )
        self.assertEqual(no_panel["status"], "abstain")
        self.assertEqual(no_panel["reason"], "no_supported_feature_panel")
        self.assertIn("No probability was produced", render_patient_result_markdown(no_panel))

        out_of_range = generate_patient_result(
            routers,
            pd.DataFrame([{"a": 20.0, "b": np.nan}]),
            reference,
        )
        self.assertEqual(out_of_range["status"], "abstain")
        self.assertEqual(out_of_range["reason"], "outside_reference_range")

    def test_mixed_patient_selects_one_expert_and_reserves_age_target(self) -> None:
        routers, reference = _fixture()
        references = {
            name: LoadedDataset(
                name=name,
                X=reference.X,
                y=reference.y,
                row_ids=reference.row_ids,
                metadata={
                    **reference.metadata,
                    "task": "diabetes_screening",
                    "endpoint": f"{name}_screening_endpoint",
                },
            )
            for name in ("pidd", "sylhet", "brfss")
        }
        bundles = {name: routers for name in references}
        patient = {
            "pidd": {"a": 1.25},
            "sylhet": {"a": 0.75},
            "brfss": {"a": 0.5},
        }
        ambiguous = generate_mixed_patient_result(
            bundles,
            patient,
            references,
            top_k=1,
        )
        self.assertEqual(ambiguous["status"], "abstain")
        self.assertEqual(
            ambiguous["reason"],
            "cross_dataset_environment_selection_not_validated",
        )

        result = generate_mixed_patient_result(
            bundles,
            patient,
            references,
            preferred_dataset="pidd",
            top_k=1,
        )
        self.assertEqual(result["status"], "predicted")
        self.assertEqual(result["routing"]["selected_dataset"], "pidd")
        self.assertEqual(
            result["prediction_targets"]["diabetes_probability"]["status"],
            "available",
        )
        self.assertEqual(
            result["prediction_targets"]["onset_age"]["status"],
            "not_implemented",
        )
        self.assertIn(
            "sylhet",
            result["input_usage"]["fields_not_used_in_selected_probability"],
        )
        rendered = render_mixed_patient_result_markdown(result)
        self.assertIn("Estimated calibrated probability", rendered)
        self.assertIn("not implemented", rendered)

    def test_mixed_patient_rejects_readmission_endpoint(self) -> None:
        routers, reference = _fixture()
        hospital = LoadedDataset(
            name="hospital130",
            X=reference.X,
            y=reference.y,
            row_ids=reference.row_ids,
            metadata={
                **reference.metadata,
                "task": "hospital_readmission",
                "endpoint": "readmission_within_30_days",
            },
        )
        with self.assertRaisesRegex(ValueError, "cannot be mixed"):
            generate_mixed_patient_result(
                {"hospital130": routers},
                {"hospital130": {"a": 1.0}},
                {"hospital130": hospital},
            )

        readmission_result = generate_patient_result(
            routers,
            pd.DataFrame([{"a": 1.0, "b": 1.0}]),
            hospital,
            top_k=1,
        )
        rendered = render_patient_result_markdown(readmission_result)
        self.assertIn("Hospital readmission research result", rendered)
        self.assertNotIn("does not rule out diabetes", rendered)


if __name__ == "__main__":
    unittest.main()
