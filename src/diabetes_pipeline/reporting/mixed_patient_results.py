"""One-patient routing across multiple cohort-specific diabetes models."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pandas as pd

from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.reporting.patient_results import (
    DISCLAIMER,
    generate_patient_result,
)
from diabetes_pipeline.settings import source_tree_sha256


DEFAULT_DATASET_PRIORITY = {
    # Direct laboratory/clinical measurements are preferred when a validated
    # PIDD panel is satisfied, followed by the symptom questionnaire and then
    # the population survey. This is a transparent routing rule, not a claim
    # that probabilities from these cohorts are interchangeable.
    "pidd": 300,
    "sylhet": 200,
    "brfss": 100,
}


def _one_row(value: Mapping[str, Any] | pd.DataFrame) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        if len(value) != 1:
            raise ValueError("Each dataset input must contain exactly one patient row")
        return value.copy()
    if not isinstance(value, Mapping):
        raise ValueError("Each dataset input must be a feature object")
    return pd.DataFrame([dict(value)])


def _candidate_rank(
    dataset_name: str,
    result: dict[str, Any],
    priorities: Mapping[str, int],
) -> tuple[int, float, int, str]:
    availability = result["feature_availability"]
    used_count = len(availability["features_used"])
    available_count = len(availability["available_features"])
    coverage = used_count / available_count if available_count else 0.0
    return (int(priorities.get(dataset_name, 0)), coverage, used_count, dataset_name)


def generate_mixed_patient_result(
    router_bundles_by_dataset: Mapping[
        str, Iterable[dict[str, Any] | Path | str]
    ],
    patient_by_dataset: Mapping[str, Mapping[str, Any] | pd.DataFrame],
    references_by_dataset: Mapping[str, LoadedDataset],
    *,
    preferred_dataset: str | None = None,
    dataset_priority: Mapping[str, int] | None = None,
    allow_experimental_auto_selection: bool = False,
    top_k: int = 5,
    abstain_outside_reference: bool = True,
) -> dict[str, Any]:
    """Select one eligible diabetes-screening expert for a mixed patient input.

    Each dataset router is evaluated independently. The function deliberately
    selects one expert instead of averaging cohort-specific probabilities,
    because cross-dataset fusion requires a separately validated harmonized
    model trained on patients with jointly observed attributes.
    """

    if not patient_by_dataset:
        raise ValueError("At least one dataset-specific patient object is required")
    unknown = sorted(
        set(patient_by_dataset)
        - set(router_bundles_by_dataset)
        - set(references_by_dataset)
    )
    if unknown:
        raise ValueError(f"No router/reference was supplied for datasets: {unknown}")
    priorities = dict(DEFAULT_DATASET_PRIORITY)
    if dataset_priority is not None:
        priorities.update({str(key): int(value) for key, value in dataset_priority.items()})

    dataset_results: dict[str, dict[str, Any]] = {}
    provided_fields: dict[str, list[str]] = {}
    for dataset_name in sorted(patient_by_dataset):
        if dataset_name not in router_bundles_by_dataset:
            raise ValueError(f"No router bundles supplied for '{dataset_name}'")
        if dataset_name not in references_by_dataset:
            raise ValueError(f"No reference dataset supplied for '{dataset_name}'")
        reference = references_by_dataset[dataset_name]
        if reference.metadata.get("task") != "diabetes_screening":
            raise ValueError(
                f"Dataset '{dataset_name}' predicts {reference.metadata.get('task')!r}; "
                "it cannot be mixed into a diabetes-screening result"
            )
        patient_frame = _one_row(patient_by_dataset[dataset_name])
        provided_fields[dataset_name] = sorted(
            feature
            for feature in patient_frame.columns
            if pd.notna(patient_frame.iloc[0][feature])
        )
        dataset_results[dataset_name] = generate_patient_result(
            router_bundles_by_dataset[dataset_name],
            patient_frame,
            reference,
            top_k=top_k,
            abstain_outside_reference=abstain_outside_reference,
        )

    eligible = {
        name: result
        for name, result in dataset_results.items()
        if result["status"] == "predicted"
    }
    if not eligible:
        return {
            "schema_version": "2.0",
            "status": "abstain",
            "intended_use": "research_validation_only",
            "task": "diabetes_screening",
            "reason": "no_supported_dataset_panel",
            "dataset_attempts": {
                name: {
                    "status": result["status"],
                    "reason": result.get("reason"),
                    "details": result.get("details", {}),
                }
                for name, result in sorted(dataset_results.items())
            },
            "provided_fields_by_dataset": provided_fields,
            "prediction_targets": {
                "diabetes_probability": {"status": "unavailable", "value": None},
                "onset_age": {
                    "status": "not_implemented",
                    "predicted_age_years": None,
                },
            },
            "disclaimer": DISCLAIMER,
            "pipeline_source_tree_sha256": source_tree_sha256(),
        }

    candidate_summaries = {
        name: {
            "status": result["status"],
            "estimated_probability_percent": (
                result["probability_result"]["estimated_probability_percent"]
                if result["status"] == "predicted"
                else None
            ),
            "selected_scenario": (
                result["feature_availability"]["selected_scenario"]
                if result["status"] == "predicted"
                else None
            ),
            "features_used": (
                result["feature_availability"]["features_used"]
                if result["status"] == "predicted"
                else []
            ),
            "research_evidence": result.get("research_evidence", {}),
            "abstention_reason": result.get("reason"),
        }
        for name, result in sorted(dataset_results.items())
    }

    if preferred_dataset is None and len(eligible) > 1 and not allow_experimental_auto_selection:
        return {
            "schema_version": "2.1",
            "status": "abstain",
            "intended_use": "research_validation_only",
            "task": "diabetes_screening",
            "reason": "cross_dataset_environment_selection_not_validated",
            "details": {
                "eligible_datasets": sorted(eligible),
                "candidate_results": candidate_summaries,
                "required_action": (
                    "Specify a clinically and population-appropriate preferred_dataset, "
                    "or explicitly opt into the unvalidated experimental selector for "
                    "software demonstration only."
                ),
            },
            "prediction_targets": {
                "diabetes_probability": {"status": "unavailable", "value": None},
                "onset_age": {
                    "status": "not_implemented",
                    "predicted_age_years": None,
                },
            },
            "research_evidence": {
                "cross_dataset_selector_validated": False,
                "publication_claim_eligible": False,
                "interpretation": (
                    "No matched multi-environment patient cohort exists to validate "
                    "automatic selection among PIDD, Sylhet, and BRFSS."
                ),
            },
            "disclaimer": DISCLAIMER,
            "pipeline_source_tree_sha256": source_tree_sha256(),
        }

    if preferred_dataset is not None:
        if preferred_dataset not in eligible:
            raise ValueError(
                f"Preferred dataset '{preferred_dataset}' did not produce an eligible prediction"
            )
        selected_dataset = preferred_dataset
        selection_reason = "explicit_preferred_dataset"
    elif len(eligible) == 1:
        selected_dataset = next(iter(eligible))
        selection_reason = "only_eligible_dataset"
    else:
        selected_dataset = max(
            eligible,
            key=lambda name: _candidate_rank(name, eligible[name], priorities),
        )
        selection_reason = "unvalidated_experimental_measurement_specificity_then_panel_coverage"

    selected = eligible[selected_dataset]
    selected_probability = dict(selected["probability_result"])
    selected_used = set(selected["feature_availability"]["features_used"])
    fields_not_used: dict[str, list[str]] = {}
    for dataset_name, fields in provided_fields.items():
        if dataset_name == selected_dataset:
            unused = sorted(set(fields) - selected_used)
        else:
            unused = list(fields)
        if unused:
            fields_not_used[dataset_name] = unused

    selected_publication_eligible = bool(
        selected.get("research_evidence", {}).get(
            "publication_claim_eligible", False
        )
    )
    selector_validated = len(eligible) == 1 or preferred_dataset is not None
    return {
        "schema_version": "2.1",
        "status": "predicted",
        "intended_use": "research_validation_only",
        "task": "diabetes_screening",
        "routing": {
            "selected_dataset": selected_dataset,
            "selected_dataset_display_name": selected.get("dataset_display_name"),
            "selected_endpoint": selected.get("endpoint"),
            "selection_reason": selection_reason,
            "selection_policy": (
                "Select one eligible cohort-specific expert; never average or pool "
                "probabilities across datasets without a separately validated "
                "harmonized model."
            ),
            "cross_dataset_selector_validated": False,
            "experimental_auto_selection_used": bool(
                len(eligible) > 1
                and preferred_dataset is None
                and allow_experimental_auto_selection
            ),
            "dataset_priority": priorities,
            "candidate_results": candidate_summaries,
        },
        "probability_result": selected_probability,
        "prediction_targets": {
            "diabetes_probability": {
                "status": "available",
                "estimated_probability": selected_probability["estimated_probability"],
                "estimated_probability_percent": selected_probability[
                    "estimated_probability_percent"
                ],
                "source_dataset": selected_dataset,
            },
            "onset_age": {
                "status": "not_implemented",
                "predicted_age_years": None,
                "extension_contract": (
                    "A future separately trained and validated time-to-event or "
                    "age-at-onset model may populate this target without changing "
                    "the diabetes_probability contract."
                ),
            },
        },
        "input_usage": {
            "provided_fields_by_dataset": provided_fields,
            "selected_expert_features_used": sorted(selected_used),
            "fields_not_used_in_selected_probability": fields_not_used,
            "non_fusion_note": (
                "Fields belonging only to unselected datasets were evaluated by "
                "their own eligible experts but were not fused into the selected "
                "percentage. Joint use requires matched multi-source patient data."
            ),
        },
        "selected_dataset_result": selected,
        "research_evidence": {
            "selected_study_publication_claim_eligible": selected_publication_eligible,
            "environment_selection_is_explicit_or_unambiguous": selector_validated,
            "cross_dataset_selector_validated": False,
            "publication_claim_eligible": bool(
                selected_publication_eligible and selector_validated
            ),
            "interpretation": (
                "The probability inherits the evidence tier of the selected "
                "dataset study. Automatic cross-dataset expert selection remains "
                "unvalidated and is excluded from publication claims."
            ),
        },
        "disclaimer": DISCLAIMER,
        "pipeline_source_tree_sha256": source_tree_sha256(),
    }


def render_mixed_patient_result_markdown(result: dict[str, Any]) -> str:
    """Render a compact patient-facing research summary for the mixed router."""

    lines = [
        "# Mixed-source diabetes screening research result",
        "",
        f"**Status:** {str(result['status']).replace('_', ' ').title()}",
        "",
    ]
    if result["status"] == "abstain":
        if result["reason"] == "cross_dataset_environment_selection_not_validated":
            explanation = (
                "No unified percentage was produced because multiple cohort-specific "
                "experts were eligible and automatic cross-dataset selection has not "
                "been validated on matched patients."
            )
        else:
            explanation = (
                "No percentage was produced because none of the supplied dataset "
                "attributes satisfied an evaluated feature panel."
            )
        lines.extend(
            [
                explanation,
                "",
                f"**Reason:** {str(result['reason']).replace('_', ' ')}",
                "",
                f"> {result['disclaimer']}",
            ]
        )
        return "\n".join(lines) + "\n"

    probability = result["probability_result"]
    routing = result["routing"]
    lines.extend(
        [
            "**Estimated calibrated probability:** "
            f"{float(probability['estimated_probability_percent']):.1f}%",
            "",
            f"**Selected dataset expert:** {routing['selected_dataset_display_name']} "
            f"(`{routing['selected_dataset']}`)",
            "",
            f"**Selected panel:** "
            f"`{result['selected_dataset_result']['feature_availability']['selected_scenario']}`",
            "",
            probability["threshold_interpretation"],
            "",
            "The onset-age target is intentionally not implemented yet. It has a "
            "separate output slot so a future age model cannot silently alter the "
            "probability result.",
            "",
            result["input_usage"]["non_fusion_note"],
            "",
            f"> {result['disclaimer']}",
        ]
    )
    return "\n".join(lines) + "\n"
