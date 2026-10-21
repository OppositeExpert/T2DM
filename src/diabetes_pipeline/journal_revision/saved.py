"""Sensitivity, routing, and selective analyses from unchanged saved predictions."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.evaluation.selective_prediction import _accepted_mask, DEFAULT_COVERAGES
from diabetes_pipeline.routing.policy_evaluator import _supported_scenarios

from .common import (ROOT, REPORT, PRIVATE, EXPECTED, DIAGNOSTICS, aggregate, align,
                     read_csv, metrics, numeric_probability, studies, panels,
                     save_table, markdown_table, write_json)


def repeat_sensitivity(dataset, directory):
    sources = [
        ("base_full", directory / "predictions.csv", ["model"]),
        ("forced_panel_model", directory / "availability_routing/stress_predictions.csv", ["scenario", "model"]),
        ("forced_panel_system", directory / "availability_routing/system_predictions.csv", ["scenario", "system"]),
        ("runtime_policy", directory / "runtime_policy_evaluation/policy_decisions.csv", ["system"]),
    ]
    records = []
    for analysis, path, keys in sources:
        frame = read_csv(path)
        if "status" in frame:
            frame = frame[frame["status"] == "predicted"].copy()
        versions = ["probability_calibrated"]
        if "probability_raw" in frame:
            versions.append("probability_raw")
        for version in versions:
            current = frame.copy()
            current["probability_calibrated"] = numeric_probability(current, version)
            aggregated = aggregate(current, keys, 5)
            for identity, group in current.groupby(keys, sort=True):
                identity = identity if isinstance(identity, tuple) else (identity,)
                labels = dict(zip(keys, identity))
                paired = aggregated
                for key, value in labels.items():
                    paired = paired[paired[key] == value]
                expected = EXPECTED[dataset]
                if len(paired) != expected[0] or int(paired["target"].sum()) != expected[1]:
                    raise ValueError("Repeated estimand population mismatch")
                individual = []
                for repeat, sample in group.groupby("repeat", sort=True):
                    sample, _ = align(sample, paired)
                    individual.append(metrics(sample))
                    records.append({"dataset": dataset, "analysis": analysis, **labels,
                                    "probability_version": version, "summary": "per_repeat",
                                    "repeat": int(repeat), "evaluation_n": len(sample),
                                    "positive_events": int(sample["target"].sum()), **individual[-1]})
                values = pd.DataFrame(individual)
                primary = metrics(paired)
                summaries = {"repeat_metric_mean": values.mean().to_dict(),
                             "repeat_metric_sample_sd": values.std(ddof=1).to_dict(),
                             "participant_mean_probability_metric": primary,
                             "repeat_metric_mean_minus_primary": {k: values[k].mean() - primary[k] for k in DIAGNOSTICS}}
                for label, result in summaries.items():
                    records.append({"dataset": dataset, "analysis": analysis, **labels,
                                    "probability_version": version, "summary": label, "repeat": "",
                                    "evaluation_n": len(paired), "positive_events": int(paired["target"].sum()), **result})
    return records


def routing_distribution(dataset, directory, metadata, loaded):
    participants = read_csv(directory / "runtime_policy_evaluation/participant_policy_predictions.csv")
    decisions = read_csv(directory / "runtime_policy_evaluation/policy_decisions.csv")
    participant = participants[participants["system"] == "availability_router"].copy()
    decision = decisions[decisions["system"] == "availability_router"].copy()
    total, events = EXPECTED[dataset]
    if len(participant) != total or participant["row_id"].duplicated().any() or int(participant["target"].sum()) != events:
        raise ValueError(f"Runtime population mismatch: {dataset}")
    repeats = 5 if dataset in {"pidd", "sylhet"} else 1
    if decision.duplicated(["row_id", "repeat"]).any() or len(decision) != repeats * total:
        raise ValueError("Runtime repeat completeness mismatch")
    if decision.groupby("row_id")["repeat"].nunique().ne(repeats).any():
        raise ValueError("Missing runtime repeat")
    for col in ["target", "group_id", "status", "scenario"]:
        if decision.groupby("row_id")[col].nunique(dropna=False).ne(1).any():
            raise ValueError(f"Runtime repeat {col} instability")
    manifest = read_csv(Path(metadata["split_manifest"]))
    role = manifest[manifest["role"] == ("validation" if repeats == 5 else "test")]
    unique = role.drop_duplicates("row_id").sort_values("row_id").reset_index(drop=True)
    part_sorted = participant.sort_values("row_id").reset_index(drop=True)
    for col in ["row_id", "target", "group_id"]:
        if not np.array_equal(unique[col].to_numpy(), part_sorted[col].to_numpy()):
            raise ValueError(f"Runtime split {col} mismatch")
    X = loaded.X.iloc[unique["row_position"].to_numpy(int)].reset_index(drop=True)
    definitions = {k: v["available_features"] for k, v in panels()[dataset]["scenarios"].items()}
    reconstructed = _supported_scenarios(X, definitions)
    if not np.array_equal(reconstructed, part_sorted["scenario"].fillna("").to_numpy()):
        raise ValueError(f"Reconstructed panel assignment differs: {dataset}")
    accepted = participant["status"].eq("predicted")
    records = [{"dataset": dataset, "row_type": "population_total", "panel": "ALL",
                "evaluation_records": total, "positive_events": events, "accepted_records": int(accepted.sum()),
                "abstained_records": int((~accepted).sum()), "accepted_events": int(participant.loc[accepted, "target"].sum()),
                "rejected_events": int(participant.loc[~accepted, "target"].sum()),
                "population_pct": 100., "event_pct": 100., "coverage": accepted.mean(),
                "provenance": "saved assignments independently validated against original inputs"}]
    for (scenario, status), subset in participant.groupby(["scenario", "status"], dropna=False, sort=True):
        positive = int(subset["target"].sum())
        records.append({"dataset": dataset, "row_type": "unique_panel", "panel": scenario or "UNSUPPORTED",
                        "status": status, "evaluation_records": len(subset), "positive_events": positive,
                        "population_pct": 100 * len(subset) / total, "event_pct": 100 * positive / events,
                        "accepted_panel_event_prevalence": positive / len(subset) if status == "predicted" else np.nan,
                        "selected_families": "|".join(sorted(set(subset["selected_models"]))),
                        "selected_calibrators": "|".join(sorted(set(subset["calibration_methods"]))),
                        "abstention_reason": "|".join(sorted(set(subset["abstention_reason"]) - {""})),
                        "eligibility": "all panel predictors observed" if status == "predicted" else "no complete supported panel"})
    # Each repeat is reported separately; these counts must never be added to unique population rows.
    for identity, subset in decision.groupby(["repeat", "scenario", "model", "calibration_method"], sort=True, dropna=False):
        repeat, scenario, family, calibration = identity
        records.append({"dataset": dataset, "row_type": "per_repeat_panel_family_calibrator", "repeat": repeat,
                        "panel": scenario or "UNSUPPORTED", "selected_families": family,
                        "selected_calibrators": calibration, "evaluation_records": len(subset),
                        "positive_events": int(subset["target"].sum()), "population_pct": 100 * len(subset) / total,
                        "event_pct": 100 * int(subset["target"].sum()) / events})
    order = sorted(definitions, key=lambda k: (len(definitions[k]), k == "full", k), reverse=True)
    for selected in sorted(set(reconstructed)):
        rows = reconstructed == selected
        for larger in order:
            if selected and order.index(larger) >= order.index(selected):
                continue
            missing = X.loc[rows, definitions[larger]].isna().sum()
            for feature, n in missing[missing.gt(0)].items():
                records.append({"dataset": dataset, "row_type": "larger_panel_missing_feature",
                                "panel": selected or "UNSUPPORTED", "blocked_panel": larger,
                                "missing_predictor": feature, "evaluation_records": int(n),
                                "population_pct": 100 * n / total,
                                "fallback_reason": "larger panel requires this unobserved input; reasons can overlap"})
    return records


def selective(dataset, directory):
    source = read_csv(directory / "runtime_policy_evaluation/participant_policy_predictions.csv")
    original = read_csv(directory / "selective_prediction/acceptance_decisions.csv")
    rows = []
    for system in ["availability_router", "robust_single_model"]:
        frame = source[source["system"] == system].sort_values("row_id").reset_index(drop=True)
        if frame["row_id"].duplicated().any():
            raise ValueError("Duplicate selective identity")
        p = pd.to_numeric(frame["probability_calibrated"], errors="coerce")
        frame["probability_calibrated"] = p
        frame["confidence"] = np.where(frame["status"].eq("predicted"), 2 * (p - .5).abs(), -np.inf)
        eligibility = frame["status"].eq("predicted").to_numpy()
        for coverage in DEFAULT_COVERAGES:
            mask = _accepted_mask(frame, coverage)
            old = original[(original["system"] == system) & (original["target_coverage"] == coverage)].sort_values("row_id")
            if not np.array_equal(old["row_id"].to_numpy(), frame["row_id"].to_numpy()) or not np.array_equal(old["accepted"].to_numpy(bool), mask):
                raise ValueError("Original confidence acceptance rule not reproduced")
            kept, rejected = frame.loc[mask], frame.loc[~mask]
            total_events = int(frame["target"].sum())
            availability_events = int(frame.loc[~eligibility, "target"].sum())
            confidence_events = int(frame.loc[eligibility & ~mask, "target"].sum())
            rows.append({"dataset": dataset, "system": system, "nominal_coverage": coverage,
                         "actual_observation_coverage": mask.mean(), "positive_event_coverage": kept["target"].sum() / total_events,
                         "total_n": len(frame), "total_positive_events": total_events,
                         "accepted_n": len(kept), "rejected_n": len(rejected),
                         "accepted_positive_events": int(kept["target"].sum()),
                         "rejected_positive_events": int(rejected["target"].sum()),
                         "availability_abstained_n": int((~eligibility).sum()),
                         "confidence_rejected_n": int((eligibility & ~mask).sum()),
                         "availability_abstained_events": availability_events, "confidence_rejected_events": confidence_events,
                         "accepted_prevalence": kept["target"].mean(), "rejected_prevalence": rejected["target"].mean(),
                         "acceptance_matches_original": True,
                         "selection_unit": "complete group, mean confidence" if frame["group_id"].str.len().gt(0).any() else "individual",
                         **metrics(kept)})
    return rows


def run_saved(selected="all"):
    repeat_rows, routing_rows, selective_rows = [], [], []
    for dataset, directory, metadata in studies():
        if selected != "all" and dataset != selected:
            continue
        print(f"Saved-output analyses: {dataset}", flush=True)
        if dataset in {"pidd", "sylhet"}:
            repeat_rows += repeat_sensitivity(dataset, directory)
        loaded = load_dataset(dataset)
        routing_rows += routing_distribution(dataset, directory, metadata, loaded)
        selective_rows += selective(dataset, directory)
    if selected != "all":
        raise ValueError("Aggregate saved reports require --dataset all")
    repeated = pd.DataFrame(repeat_rows)
    subset = repeated[(repeated["analysis"] == "runtime_policy") &
                      (repeated["system"] == "availability_router") &
                      (repeated["probability_version"] == "probability_calibrated")]
    save_table("01_PER_REPEAT_SENSITIVITY", repeated,
        "# Per-repeat sensitivity\n\nCOMPLETE. Exactly one OOF probability per record per repeat, five repeats; stable identities, outcomes and groups validated. "
        "Full base families (raw/calibrated), every forced panel/model/system, and all runtime policies are included in the CSV.\n\n"
        "Metrics are calculated within each repeat after joining its five outer validation folds. Repeat means and sample SD (ddof=1) are descriptive. "
        "Repeats reuse participants and are not independent samples. SD is not a participant-level confidence interval. "
        "The primary estimand remains metrics of five-repeat participant-mean probabilities. `repeat_metric_mean_minus_primary` quantifies the nonlinear aggregation difference.\n\n"
        + markdown_table(subset[["dataset", "summary", "repeat", "auroc", "average_precision", "brier_score", "log_loss"]]) +
        "\n\nCalibration intercept/slope are the joint unpenalized logistic recalibration diagnostic implemented in `evaluation/metrics.py`; "
        "the intercept is not a separately estimated calibration-in-the-large offset model. No evaluation recalibrator is applied.\n\n"
        "Inference: `route_patient` uses one fitted base model and scenario mapping within one router bundle. "
        "`generate_patient_result` averages probabilities across supplied router bundles (25 for repeated-cohort research inference, one for partitioned cohorts). "
        "Held-out repeated evaluation averages five OOF probabilities per record, not all 25 models. See INFERENCE_BEHAVIOR.md.")
    routing = pd.DataFrame(routing_rows)
    save_table("02_ROUTING_DISTRIBUTION", routing,
        "# Runtime routing distribution\n\nCOMPLETE. Saved assignments are independently reconstructed from original raw inputs and frozen eligibility rules; "
        "every assignment matches. The reconstruction is validation of the saved provenance, not a substitute inferred from rounded AUROC.\n\n"
        + markdown_table(routing[routing["row_type"].isin(["population_total", "unique_panel"])][
            ["dataset", "row_type", "panel", "evaluation_records", "positive_events", "population_pct", "event_pct", "coverage"]]) +
        "\n\nCSV `unique_panel` rows count each evaluation identity once. `per_repeat_panel_family_calibrator` rows report family/calibrator selections separately "
        "within repeats and must not be summed across repeats as participants. `larger_panel_missing_feature` rows give overlapping, nonexclusive reasons for fallback. "
        "All supported panel predictors must be observed; panels rank by predictor count, then full-panel flag, then reverse lexical name. "
        "Unsupported cases abstain with `no_supported_feature_panel`.\n\n"
        "Hospital130: the detailed saved/reconstructed counts establish whether encounter-utilization is selected for every encounter. "
        "The full and admission-clinical panels require fields with missing inputs. Forced full-schema evaluation permits training-fitted imputation; "
        "runtime eligibility instead demands a complete supported panel. Compare the actual unique-panel counts, models and predictions, not just rounded performance. "
        "The dedicated statistical report verifies the exact full-panel, stress and runtime estimates.")
    selection = pd.DataFrame(selective_rows)
    focus = selection[(selection["system"] == "availability_router") & selection["nominal_coverage"].eq(.7)]
    save_table("03_SELECTIVE_PREDICTION", selection,
        "# Selective prediction\n\nCOMPLETE. Original runtime probabilities and all five prespecified targets are used; every accepted identity matches saved decisions. "
        "Confidence is 2|p-0.5|. Individual ties use ascending string record ID. Grouped cohorts rank complete groups by mean confidence, "
        "then group ID, and include the last group whose start is below ceil(N x target); actual coverage may slightly overshoot. "
        "Availability abstention precedes confidence rejection and is reported separately. Targets use the entire evaluation population denominator.\n\n"
        + markdown_table(focus[["dataset", "nominal_coverage", "actual_observation_coverage", "positive_event_coverage", "accepted_n", "accepted_positive_events", "rejected_positive_events", "accepted_prevalence", "rejected_prevalence", "brier_score"]]) +
        "\n\nMathematically, Brier on the accepted set S is E[(p-Y)^2 | S] = pi_S E[(1-p)^2 | Y=1,S] + "
        "(1-pi_S) E[p^2 | Y=0,S]. Certainty filtering in low-prevalence cohorts retains many low-p negatives. "
        "Lower accepted prevalence and exclusion of hard positive cases can therefore reduce this conditional Brier even when most events are rejected. "
        "It is a different population and cannot establish better population-wide prediction. Event coverage, excluded events and rejected prevalence must accompany accepted metrics. "
        "The 100% target is capped by availability eligibility (BRFSS); it does not recover unsupported cases. No new model training or uncertainty approximation was used.")
    write_json(REPORT / "saved_analysis_validation.json", {"passed": True, "repeat_rows": len(repeated),
               "routing_rows": len(routing), "selective_rows": len(selection), "all_acceptance_decisions_match": True,
               "all_raw_reconstructed_panel_assignments_match": True})
    print("Saved-output reports complete", flush=True)
