"""Safe, probability-first patient reports from cross-validation router bundles.

The output is intentionally a research artifact. It preserves the distinction
between calibrated probability, an operating threshold, model explanation, and
unadjusted cohort context instead of presenting a model prediction as a
diagnosis.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import joblib
import numpy as np
import pandas as pd
from scipy import sparse

from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.explainability.shap_analysis import _compute_shap
from diabetes_pipeline.routing.inference import route_patient
from diabetes_pipeline.settings import source_tree_sha256


DISCLAIMER = (
    "Research validation output only. This is not a diagnosis or a treatment "
    "recommendation. Clinical use requires prospective validation and qualified "
    "medical review."
)
SHAP_NOTE = (
    "SHAP describes how inputs influenced the underlying model output; it does "
    "not establish that a feature caused diabetes. Contributions are normalized "
    "within each fold before aggregation because model families use different "
    "SHAP scales."
)
CONTEXT_NOTE = (
    "Cohort context is an unadjusted descriptive comparison from the reference "
    "dataset. It is not a clinical cutoff, causal effect, or personalized "
    "recommendation."
)


def _native(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    return str(value)


def _dense(values: Any) -> np.ndarray:
    return values.toarray() if sparse.issparse(values) else np.asarray(values)


def _load_router_bundles(
    bundles: Iterable[dict[str, Any] | Path | str],
) -> list[dict[str, Any]]:
    loaded: list[dict[str, Any]] = []
    for bundle in bundles:
        payload = joblib.load(bundle) if isinstance(bundle, (Path, str)) else bundle
        if not isinstance(payload, dict):
            raise ValueError("Every router bundle must be a dictionary")
        required = {
            "configured_features",
            "scenarios",
            "selected_models",
            "model_bundles",
            "scenario_calibrators",
        }
        missing = sorted(required - set(payload))
        if missing:
            raise ValueError(f"Router bundle is missing keys: {missing}")
        loaded.append(payload)
    if not loaded:
        raise ValueError("At least one router bundle is required")
    loaded.sort(key=lambda item: (int(item.get("repeat", 0)), int(item.get("outer_fold", 0))))
    return loaded


def _bundle_evidence_tier(bundle: dict[str, Any]) -> str:
    explicit = bundle.get("evidence_tier")
    if explicit is not None:
        return str(explicit)
    experiment_id = str(bundle.get("experiment_id", "")).lower()
    if "smoke" in experiment_id:
        return "execution_only"
    if "pilot" in experiment_id or "development" in experiment_id:
        return "development_only"
    return "unknown"


def _coerce_patient(
    patient: pd.DataFrame,
    reference: LoadedDataset,
    configured_features: list[str],
) -> tuple[pd.DataFrame | None, list[dict[str, Any]]]:
    if len(patient) != 1:
        raise ValueError("Patient reporting accepts exactly one row")
    coerced = patient.copy()
    errors: list[dict[str, Any]] = []
    for feature in configured_features:
        if feature not in coerced.columns or pd.isna(coerced.iloc[0][feature]):
            continue
        if pd.api.types.is_numeric_dtype(reference.X[feature]):
            try:
                value = float(coerced.iloc[0][feature])
            except (TypeError, ValueError):
                errors.append(
                    {
                        "feature": feature,
                        "reason": "not_numeric",
                        "provided_value": str(coerced.iloc[0][feature]),
                    }
                )
                continue
            if not np.isfinite(value):
                errors.append(
                    {
                        "feature": feature,
                        "reason": "not_finite",
                        "provided_value": str(coerced.iloc[0][feature]),
                    }
                )
                continue
            coerced.loc[:, feature] = value
    return (None, errors) if errors else (coerced, [])


def _source_feature(component: str, configured_features: list[str]) -> str:
    if component.startswith("missingindicator_"):
        return component.removeprefix("missingindicator_")
    if component in configured_features:
        return component
    for feature in sorted(configured_features, key=len, reverse=True):
        if component.startswith(f"{feature}_"):
            return feature
    return component


def _explain_routed_patient(
    router_bundle: dict[str, Any],
    patient: pd.DataFrame,
    routed: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    configured_features = list(router_bundle["configured_features"])
    scenario = str(routed["scenario"])
    model_name = str(routed["model"])
    used_features = set(router_bundle["scenarios"][scenario])
    model_bundle = router_bundle["model_bundles"][model_name]

    ordered = patient.reindex(columns=configured_features).copy()
    unavailable = sorted(set(configured_features) - used_features)
    for feature in unavailable:
        ordered[feature] = np.nan
    transformed = _dense(model_bundle["preprocessor"].transform(ordered))
    estimator = model_bundle["model"].estimator
    values, base_values, scale, model_output = _compute_shap(
        model_name,
        estimator,
        transformed,
        transformed,
    )
    reconstructed = base_values + values.sum(axis=1)
    error = float(np.max(np.abs(reconstructed - model_output)))
    if error > 1e-4:
        raise RuntimeError(
            f"Patient SHAP additivity check failed for {model_name}: {error:.6g}"
        )

    transformed_names = list(model_bundle["transformed_feature_names"])
    if values.shape != (1, len(transformed_names)):
        raise ValueError(
            "Patient SHAP output does not match the transformed feature contract"
        )
    grouped: dict[str, float] = {}
    components: dict[str, list[str]] = {}
    for component, contribution in zip(transformed_names, values[0], strict=True):
        source = _source_feature(component, configured_features)
        grouped[source] = grouped.get(source, 0.0) + float(contribution)
        components.setdefault(source, []).append(component)

    observed = patient.iloc[0]
    records: list[dict[str, Any]] = []
    for feature in sorted(used_features):
        contribution = float(grouped.get(feature, 0.0))
        records.append(
            {
                "feature": feature,
                "observed_value": _native(observed.get(feature)),
                "shap_value": contribution,
                "absolute_shap_value": abs(contribution),
                "direction": (
                    "raises_model_output"
                    if contribution > 0
                    else "lowers_model_output"
                    if contribution < 0
                    else "neutral"
                ),
                "components": components.get(feature, []),
                "explanation_scale": scale,
            }
        )
    denominator = sum(row["absolute_shap_value"] for row in records)
    ordered_records = sorted(
        records,
        key=lambda row: (-float(row["absolute_shap_value"]), str(row["feature"])),
    )
    for rank, row in enumerate(ordered_records, start=1):
        row["within_fold_rank"] = rank
        row["within_fold_normalized_importance"] = (
            float(row["absolute_shap_value"] / denominator)
            if denominator > 0
            else 0.0
        )
    return ordered_records, {
        "explanation_scale": scale,
        "maximum_additivity_error": error,
        "base_value": float(base_values[0]),
        "model_output": float(model_output[0]),
        "unavailable_features_masked": unavailable,
    }


def _aggregate_factors(
    fold_factors: list[list[dict[str, Any]]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    all_features = sorted(
        {row["feature"] for factors in fold_factors for row in factors}
    )
    for feature in all_features:
        rows = [
            next(row for row in factors if row["feature"] == feature)
            for factors in fold_factors
            if any(row["feature"] == feature for row in factors)
        ]
        positive = sum(float(row["shap_value"]) > 0 for row in rows)
        negative = sum(float(row["shap_value"]) < 0 for row in rows)
        directional = positive + negative
        positive_fraction = positive / directional if directional else 0.5
        if directional == 0:
            direction = "neutral"
        elif positive_fraction >= 0.8:
            direction = "mostly_raises_model_output"
        elif positive_fraction <= 0.2:
            direction = "mostly_lowers_model_output"
        else:
            direction = "mixed_across_folds"
        records.append(
            {
                "feature": feature,
                "observed_value": rows[0]["observed_value"],
                "mean_within_fold_normalized_importance": float(
                    np.mean(
                        [row["within_fold_normalized_importance"] for row in rows]
                    )
                ),
                "median_within_fold_rank": float(
                    np.median([row["within_fold_rank"] for row in rows])
                ),
                "direction": direction,
                "folds_raising_output": positive,
                "folds_lowering_output": negative,
                "folds_explained": len(rows),
                "direction_agreement": float(
                    max(positive, negative) / directional if directional else 1.0
                ),
            }
        )
    records.sort(
        key=lambda row: (
            -float(row["mean_within_fold_normalized_importance"]),
            float(row["median_within_fold_rank"]),
            str(row["feature"]),
        )
    )
    return records[:top_k]


def _reference_range_violations(
    patient: pd.DataFrame,
    reference_X: pd.DataFrame,
    used_features: list[str],
) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    row = patient.iloc[0]
    for feature in used_features:
        value = row.get(feature)
        if pd.isna(value) or not pd.api.types.is_numeric_dtype(reference_X[feature]):
            continue
        observed = pd.to_numeric(reference_X[feature], errors="coerce").dropna()
        if observed.empty:
            continue
        lower = float(observed.min())
        upper = float(observed.max())
        numeric_value = float(value)
        if numeric_value < lower or numeric_value > upper:
            violations.append(
                {
                    "feature": feature,
                    "provided_value": numeric_value,
                    "reference_minimum": lower,
                    "reference_maximum": upper,
                }
            )
    return violations


def _cohort_context(
    reference: LoadedDataset,
    patient: pd.DataFrame,
    factors: list[dict[str, Any]],
    *,
    bins: int = 5,
    minimum_rows: int = 20,
) -> list[dict[str, Any]]:
    context: list[dict[str, Any]] = []
    overall_prevalence = float(reference.y.mean())
    patient_row = patient.iloc[0]
    for factor in factors:
        feature = str(factor["feature"])
        if feature not in reference.X or not pd.api.types.is_numeric_dtype(
            reference.X[feature]
        ):
            continue
        patient_value = patient_row.get(feature)
        if pd.isna(patient_value):
            continue
        frame = pd.DataFrame(
            {
                "value": pd.to_numeric(reference.X[feature], errors="coerce"),
                "target": reference.y,
            }
        ).dropna()
        unique_count = int(frame["value"].nunique())
        if unique_count < 2:
            continue
        try:
            frame["bin"] = pd.qcut(
                frame["value"], q=min(bins, unique_count), duplicates="drop"
            )
        except ValueError:
            continue
        matching = frame[frame["bin"].map(lambda interval: float(patient_value) in interval)]
        if matching.empty or len(matching) < minimum_rows:
            continue
        interval = matching["bin"].iloc[0]
        bin_prevalence = float(matching["target"].mean())
        context.append(
            {
                "feature": feature,
                "observed_value": _native(patient_value),
                "reference_bin_lower": float(interval.left),
                "reference_bin_upper": float(interval.right),
                "reference_bin_rows": int(len(matching)),
                "reference_bin_observed_prevalence": bin_prevalence,
                "reference_cohort_observed_prevalence": overall_prevalence,
                "absolute_prevalence_difference": float(
                    bin_prevalence - overall_prevalence
                ),
                "scope": "unadjusted_reference_cohort_bin",
            }
        )
    return context


def _abstention_result(
    *,
    reference: LoadedDataset,
    reason: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "status": "abstain",
        "intended_use": "research_validation_only",
        "dataset": reference.name,
        "task": reference.metadata.get("task"),
        "endpoint": reference.metadata.get("endpoint"),
        "reason": reason,
        "details": details,
        "disclaimer": DISCLAIMER,
        "pipeline_source_tree_sha256": source_tree_sha256(),
    }


def generate_patient_result(
    router_bundles: Iterable[dict[str, Any] | Path | str],
    patient: pd.DataFrame,
    reference: LoadedDataset,
    *,
    scenario_name: str | None = None,
    top_k: int = 5,
    abstain_outside_reference: bool = True,
) -> dict[str, Any]:
    """Return an ensemble probability, SHAP factors, context, or abstention.

    Cross-validation bundles are used as a research ensemble. Their spread is
    reported as model-fold variability and must not be interpreted as a formal
    confidence interval.
    """

    if top_k < 1:
        raise ValueError("top_k must be at least one")
    loaded = _load_router_bundles(router_bundles)
    configured = list(loaded[0]["configured_features"])
    for bundle in loaded[1:]:
        if list(bundle["configured_features"]) != configured:
            raise ValueError("Router bundles do not share a feature contract")
        if dict(bundle["scenarios"]) != dict(loaded[0]["scenarios"]):
            raise ValueError("Router bundles do not share availability scenarios")

    patient, input_errors = _coerce_patient(patient, reference, configured)
    if input_errors:
        return _abstention_result(
            reference=reference,
            reason="invalid_input",
            details={"invalid_features": input_errors},
        )
    assert patient is not None
    routed_results = [
        route_patient(bundle, patient, scenario_name=scenario_name)
        for bundle in loaded
    ]
    abstentions = [row for row in routed_results if row["status"] == "abstain"]
    if abstentions:
        return _abstention_result(
            reference=reference,
            reason=str(abstentions[0]["reason"]),
            details={key: value for key, value in abstentions[0].items() if key != "status"},
        )

    selected_scenarios = {str(row["scenario"]) for row in routed_results}
    if len(selected_scenarios) != 1:
        raise RuntimeError("Router bundles selected inconsistent feature panels")
    selected_scenario = selected_scenarios.pop()
    used_features = list(routed_results[0]["features_used"])
    range_violations = _reference_range_violations(
        patient, reference.X, used_features
    )
    if range_violations and abstain_outside_reference:
        return _abstention_result(
            reference=reference,
            reason="outside_reference_range",
            details={
                "scenario": selected_scenario,
                "range_violations": range_violations,
                "policy": "abstain_when_any_used_numeric_value_is_outside_the_reference_range",
            },
        )

    fold_factor_records: list[list[dict[str, Any]]] = []
    explanation_checks: list[dict[str, Any]] = []
    fold_predictions: list[dict[str, Any]] = []
    for bundle, routed in zip(loaded, routed_results, strict=True):
        factors, check = _explain_routed_patient(bundle, patient, routed)
        fold_factor_records.append(factors)
        repeat = int(bundle.get("repeat", 0))
        outer_fold = int(bundle.get("outer_fold", 0))
        explanation_checks.append(
            {"repeat": repeat, "outer_fold": outer_fold, **check}
        )
        fold_predictions.append(
            {
                "repeat": repeat,
                "outer_fold": outer_fold,
                "model": routed["model"],
                "calibration_method": routed["calibration_method"],
                "probability_raw": float(routed["probability_raw"]),
                "probability_calibrated": float(
                    routed["probability_calibrated"]
                ),
                "threshold": float(routed["threshold"]),
                "threshold_position": (
                    "at_or_above" if routed["prediction"] else "below"
                ),
            }
        )

    probabilities = np.asarray(
        [row["probability_calibrated"] for row in fold_predictions], dtype=float
    )
    thresholds = np.asarray([row["threshold"] for row in fold_predictions], dtype=float)
    if not np.allclose(thresholds, thresholds[0], rtol=0.0, atol=1e-12):
        raise RuntimeError("Router bundles use inconsistent operating thresholds")
    threshold = float(thresholds[0])
    factors = _aggregate_factors(fold_factor_records, top_k=top_k)
    context = _cohort_context(reference, patient, factors)
    available_features = sorted(
        feature
        for feature in configured
        if feature in patient.columns and pd.notna(patient.iloc[0][feature])
    )
    unknown_features = sorted(set(patient.columns) - set(configured))
    model_counts = Counter(str(row["model"]) for row in fold_predictions)
    calibration_counts = Counter(
        str(row["calibration_method"]) for row in fold_predictions
    )
    study_ids = sorted(
        {str(bundle.get("experiment_id", "unknown")) for bundle in loaded}
    )
    study_profiles = sorted(
        {str(bundle.get("study_profile", "unknown")) for bundle in loaded}
    )
    evidence_tiers = sorted({_bundle_evidence_tier(bundle) for bundle in loaded})
    publication_claim_eligible = all(
        bool(bundle.get("publication_claim_eligible", False)) for bundle in loaded
    )
    task = str(reference.metadata.get("task", "diabetes_screening"))
    at_or_above = float(np.mean(probabilities)) >= threshold
    if task == "hospital_readmission":
        threshold_interpretation = (
            "The mean probability is at or above the predeclared research "
            "operating threshold. This is a readmission-risk flag, not a clinical "
            "determination."
            if at_or_above
            else "The mean probability is below the predeclared research "
            "operating threshold. This does not rule out readmission."
        )
    else:
        threshold_interpretation = (
            "The mean probability is at or above the predeclared research "
            "operating threshold. This is a screening flag, not a diagnosis."
            if at_or_above
            else "The mean probability is below the predeclared research "
            "operating threshold. This does not rule out diabetes."
        )
    return {
        "schema_version": "1.0",
        "status": "predicted",
        "intended_use": "research_validation_only",
        "dataset": reference.name,
        "dataset_display_name": reference.metadata.get("display_name"),
        "task": task,
        "endpoint": reference.metadata.get("endpoint"),
        "study_experiment_ids": study_ids,
        "research_evidence": {
            "study_profiles": study_profiles,
            "evidence_tiers": evidence_tiers,
            "publication_claim_eligible": publication_claim_eligible,
            "interpretation": (
                "Final, locked study artifacts eligible for manuscript claims."
                if publication_claim_eligible
                else "Development or execution evidence only; this patient result "
                "must not be presented as a final paper estimate or clinical output."
            ),
        },
        "feature_availability": {
            "selected_scenario": selected_scenario,
            "available_features": available_features,
            "features_used": used_features,
            "features_ignored_by_panel": routed_results[0]["features_ignored"],
            "unknown_input_fields_ignored": unknown_features,
        },
        "probability_result": {
            "estimated_probability": float(np.mean(probabilities)),
            "estimated_probability_percent": float(100.0 * np.mean(probabilities)),
            "model_fold_standard_deviation": float(np.std(probabilities, ddof=0)),
            "model_fold_minimum": float(np.min(probabilities)),
            "model_fold_maximum": float(np.max(probabilities)),
            "number_of_model_folds": int(len(probabilities)),
            "operating_threshold": threshold,
            "threshold_policy": str(
                loaded[0].get("threshold_policy", "fixed_0_5")
            ),
            "folds_at_or_above_threshold": int(np.sum(probabilities >= threshold)),
            "threshold_interpretation": threshold_interpretation,
            "spread_interpretation": (
                "The min/max and standard deviation describe variation across "
                "cross-validation model folds; they are not a confidence interval."
            ),
        },
        "model_provenance": {
            "selection_basis": "inner_cross_fitted_masked_predictions",
            "model_selection_counts": dict(sorted(model_counts.items())),
            "calibration_method_counts": dict(sorted(calibration_counts.items())),
            "fold_predictions": fold_predictions,
        },
        "explanation": {
            "top_observed_factors": factors,
            "method_note": SHAP_NOTE,
            "availability_note": (
                "Factors are restricted to measurements in the selected panel. "
                "Unavailable fields were masked exactly as in the routing evaluation."
            ),
            "additivity_checks": explanation_checks,
        },
        "cohort_context": {
            "comparisons": context,
            "method_note": CONTEXT_NOTE,
        },
        "applicability": {
            "within_observed_numeric_ranges": not range_violations,
            "range_warnings": range_violations,
            "dataset_notes": list(reference.metadata.get("applicability_notes", [])),
        },
        "disclaimer": DISCLAIMER,
        "pipeline_source_tree_sha256": source_tree_sha256(),
    }


def _percent(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def _display_direction(direction: str) -> str:
    return {
        "mostly_raises_model_output": "Raised estimate",
        "mostly_lowers_model_output": "Lowered estimate",
        "mixed_across_folds": "Mixed across folds",
        "neutral": "Neutral",
    }.get(direction, direction.replace("_", " ").capitalize())


def render_patient_result_markdown(result: dict[str, Any]) -> str:
    """Render the structured research result without changing its meaning."""

    title = (
        "Hospital readmission research result"
        if result.get("task") == "hospital_readmission"
        else "Diabetes screening research result"
    )
    lines = [
        f"# {title}",
        "",
        f"**Status:** {str(result['status']).replace('_', ' ').title()}",
        "",
    ]
    if result["status"] == "abstain":
        lines.extend(
            [
                "No probability was produced because the input is outside the "
                "system's evaluated conditions.",
                "",
                f"**Reason:** {str(result['reason']).replace('_', ' ')}",
                "",
                "```json",
                pd.Series(result.get("details", {})).to_json(indent=2),
                "```",
                "",
                f"> {result['disclaimer']}",
            ]
        )
        return "\n".join(lines) + "\n"

    probability = result["probability_result"]
    availability = result["feature_availability"]
    provenance = result["model_provenance"]
    lines.extend(
        [
            f"**Estimated calibrated probability:** "
            f"{_percent(probability['estimated_probability'])}",
            "",
            f"**Model-fold spread:** {_percent(probability['model_fold_minimum'])} "
            f"to {_percent(probability['model_fold_maximum'])} "
            f"(SD {_percent(probability['model_fold_standard_deviation'])})",
            "",
            f"**Research threshold:** {_percent(probability['operating_threshold'])}; "
            f"{probability['folds_at_or_above_threshold']} of "
            f"{probability['number_of_model_folds']} folds were at or above it.",
            "",
            probability["threshold_interpretation"],
            "",
            f"**Selected feature panel:** `{availability['selected_scenario']}` "
            f"({len(availability['features_used'])} measurements used)",
            "",
        ]
    )
    ignored = availability["features_ignored_by_panel"]
    if ignored:
        lines.extend(
            [
                "Unavailable or panel-excluded fields were masked: "
                + ", ".join(ignored)
                + ".",
                "",
            ]
        )

    lines.extend(
        [
            "## Strongest model factors",
            "",
            "| Feature | Value | Direction | Fold agreement | Relative strength |",
            "|---|---:|---|---:|---:|",
        ]
    )
    for factor in result["explanation"]["top_observed_factors"]:
        value = "missing" if factor["observed_value"] is None else factor["observed_value"]
        lines.append(
            f"| {factor['feature']} | {value} | "
            f"{_display_direction(str(factor['direction']))} | "
            f"{_percent(factor['direction_agreement'])} | "
            f"{_percent(factor['mean_within_fold_normalized_importance'])} |"
        )
    lines.extend(["", result["explanation"]["method_note"], ""])

    comparisons = result["cohort_context"]["comparisons"]
    if comparisons:
        lines.extend(
            [
                "## Reference-cohort context",
                "",
                "| Feature | Reference band | Observed prevalence in band | "
                "Overall cohort prevalence |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in comparisons:
            lines.append(
                f"| {row['feature']} | {row['reference_bin_lower']:.3g} to "
                f"{row['reference_bin_upper']:.3g} | "
                f"{_percent(row['reference_bin_observed_prevalence'])} "
                f"(n={row['reference_bin_rows']}) | "
                f"{_percent(row['reference_cohort_observed_prevalence'])} |"
            )
        lines.extend(["", result["cohort_context"]["method_note"], ""])

    model_counts = ", ".join(
        f"{model}: {count} fold(s)"
        for model, count in provenance["model_selection_counts"].items()
    )
    lines.extend(
        [
            "## Provenance and limitations",
            "",
            f"Models selected across folds: {model_counts}.",
            "",
            probability["spread_interpretation"],
            "",
        ]
    )
    for note in result["applicability"]["dataset_notes"]:
        lines.append(f"- {note}")
    lines.extend(["", f"> {result['disclaimer']}"])
    return "\n".join(lines) + "\n"
