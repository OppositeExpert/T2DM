"""Inference contract for a fitted availability router."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _available_features(patient: pd.DataFrame, configured: list[str]) -> set[str]:
    return {
        feature
        for feature in configured
        if feature in patient.columns and patient[feature].notna().iloc[0]
    }


def route_patient(
    router_bundle: dict[str, Any],
    patient: pd.DataFrame,
    *,
    scenario_name: str | None = None,
) -> dict[str, Any]:
    """Route one patient to a supported panel/model or explicitly abstain."""

    if len(patient) != 1:
        raise ValueError("Availability routing accepts exactly one patient at a time")
    configured_features = list(router_bundle["configured_features"])
    scenarios = dict(router_bundle["scenarios"])
    available = _available_features(patient, configured_features)

    if scenario_name is not None:
        if scenario_name not in scenarios:
            raise ValueError(f"Unknown availability scenario '{scenario_name}'")
        required = set(scenarios[scenario_name])
        if not required.issubset(available):
            return {
                "status": "abstain",
                "reason": "required_scenario_features_missing",
                "scenario": scenario_name,
                "missing_required_features": sorted(required - available),
            }
        selected_scenario = scenario_name
    else:
        supported = [
            name
            for name, features in scenarios.items()
            if set(features).issubset(available)
        ]
        if not supported:
            return {
                "status": "abstain",
                "reason": "no_supported_feature_panel",
                "available_features": sorted(available),
            }
        selected_scenario = max(
            supported,
            key=lambda name: (len(scenarios[name]), name == "full", name),
        )

    model_name = str(router_bundle["selected_models"][selected_scenario])
    model_bundle = router_bundle["model_bundles"][model_name]
    calibrator = router_bundle["scenario_calibrators"][model_name][
        selected_scenario
    ]
    ordered = patient.reindex(columns=configured_features).copy()
    unavailable_for_scenario = sorted(
        set(configured_features) - set(scenarios[selected_scenario])
    )
    for feature in unavailable_for_scenario:
        # Whole-column assignment safely promotes integer JSON inputs to a
        # missing-capable dtype and also works for categorical columns.
        ordered[feature] = np.nan
    transformed = model_bundle["preprocessor"].transform(ordered)
    raw_probability = float(model_bundle["model"].predict_proba(transformed)[0])
    calibrated_probability = float(
        calibrator.predict(np.asarray([raw_probability], dtype=float))[0]
    )
    threshold = float(router_bundle.get("threshold", 0.5))
    return {
        "status": "predicted",
        "scenario": selected_scenario,
        "model": model_name,
        "calibration_method": str(
            getattr(calibrator, "method", type(calibrator).__name__)
        ),
        "probability_raw": raw_probability,
        "probability_calibrated": calibrated_probability,
        "threshold": threshold,
        "threshold_policy": str(
            router_bundle.get("threshold_policy", "fixed_0_5")
        ),
        "prediction": int(calibrated_probability >= threshold),
        "available_features": sorted(available),
        "features_used": list(scenarios[selected_scenario]),
        "features_ignored": unavailable_for_scenario,
    }
