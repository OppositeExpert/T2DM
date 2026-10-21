"""A4-only supplementation: read fitted artifacts, never fit or tune a model."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .benchmark import environment, measured, serialized_bytes
from .common import ROOT, REPORT, PRIVATE, studies, bundle_paths, sha, write_json, markdown_table
from .experiments import contexts
from diabetes_pipeline.routing.policy_evaluator import _supported_scenarios, _predict_batch
from diabetes_pipeline.routing.inference import route_patient

A4 = PRIVATE / "a4_reporting_v2"


def read_cost_csv(path, **kwargs):
    """Preserve the decimal round-trip of nanosecond-scale timing fields."""
    return pd.read_csv(path, float_precision="round_trip", **kwargs)


def publication_table(frame):
    labels={"dataset":"Cohort", "successor_final_fit_sum_s":"Final fit sum (s)",
        "successor_calibration_sum_s":"Calibration sum (s)", "D_single_median_ms":"Single (ms)",
        "D_batch256_median_ms":"Batch 256 (ms)", "exemplar_model_MiB":"Model (MiB)",
        "exemplar_calibrator_MiB":"Calibrator (MiB)", "exemplar_prediction_triple_MiB":"Prediction triple (MiB)",
        "component":"Component", "tasks":"Tasks", "system":"System", "operation":"Operation",
        "total_seconds":"Total (s)", "median_seconds":"Median (s)", "p05_seconds":"p05 (s)",
        "p95_seconds":"p95 (s)", "min_seconds":"Min (s)", "max_seconds":"Max (s)",
        "median_ms":"Median (ms)", "p05_ms":"p05 (ms)", "p95_ms":"p95 (ms)",
        "min_ms":"Min (ms)", "max_ms":"Max (ms)", "batch_n":"Records", "task_count":"Tasks",
        "environment_id":"Environment", "scope":"Storage scope", "combined_MiB":"Combined (MiB)",
        "unique_models":"Distinct models", "repeat":"Repeat", "outer_fold":"Fold",
        "A_median_ms":"A median (ms)", "D_median_ms":"D median (ms)", "D_over_A_median_ratio":"D/A median ratio"}
    frame=frame.copy()
    if "dataset" in frame:
        frame["dataset"]=frame.dataset.map({"pidd":"PIDD","sylhet":"Sylhet","brfss":"BRFSS","hospital130":"Hospital130"})
    if "component" in frame:
        frame["component"]=frame.component.replace({"new_panel_base_oof_seconds":"OOF generation", "new_panel_calibration_seconds":"Calibration selection + fit",
            "new_panel_final_model_fit_seconds":"Final model fit", "new_panel_final_preprocessing_seconds":"Final preprocessing", "new_panel_tuning_seconds":"Tuning (none)"})
    return markdown_table(frame.rename(columns=labels))


def elapsed_utc(start, end):
    a, b = datetime.fromisoformat(start), datetime.fromisoformat(end)
    if a.tzinfo is None or b.tzinfo is None or b < a:
        raise ValueError("Invalid timezone-aware historical interval")
    return (b - a).total_seconds()


def selected_payload(bundle):
    """Storage payload for D alone: no duplicate base object for each panel."""
    families = sorted(set(bundle["selected_models"].values()))
    return {"configured_features": bundle["configured_features"], "scenarios": bundle["scenarios"],
            "selected_models": bundle["selected_models"], "threshold": bundle["threshold"],
            "threshold_policy": bundle["threshold_policy"],
            "model_bundles": {f: {"model": bundle["model_bundles"][f]["model"],
                                    "preprocessor": bundle["model_bundles"][f]["preprocessor"]} for f in families},
            "scenario_calibrators": {f: {p: bundle["scenario_calibrators"][f][p]
                                          for p, family in bundle["selected_models"].items() if family == f} for f in families}}


def routed_predict(bundle, frame, fixed=False):
    assignment = _supported_scenarios(frame, bundle["scenarios"])
    result = np.full(len(frame), np.nan)
    for panel in sorted(set(assignment) - {""}):
        rows = assignment == panel
        family = bundle["robust_single_model"] if fixed else bundle["selected_models"][panel]
        if fixed:
            base = bundle["model_bundles"][family]
            ordered = frame.loc[rows].reindex(columns=bundle["configured_features"]).copy()
            for feature in set(bundle["configured_features"]) - set(bundle["scenarios"][panel]):
                ordered[feature] = np.nan
            raw = base["model"].predict_proba(base["preprocessor"].transform(ordered))
            result[rows] = base["calibrator"].predict(raw)
        else:
            _, result[rows], _ = _predict_batch(bundle, frame.loc[rows], panel, family)
    return result


def prediction_parity(a, b):
    """Parallel forest sums may differ at round-off; metadata stays exact."""
    if a.keys() != b.keys() or a.get("status") != "predicted":
        return False
    for key in a:
        if key in {"probability_raw", "probability_calibrated"}:
            if not np.isclose(a[key], b[key], rtol=0, atol=1e-14): return False
        elif a[key] != b[key]:
            return False
    return True


def collect(resume=False):
    if not (REPORT / "A4_BENCHMARK_COMPLETENESS_AUDIT.md").is_file():
        raise PermissionError("Complete audit before supplementary measurement")
    if (A4 / "supplement_raw_samples.json").exists():
        raise FileExistsError("Preserve measurements; fresh benchmarks require a new versioned output path")
    if (A4 / "in_progress_samples.json").exists() and not resume:
        raise FileExistsError("Preserve interrupted sample checkpoint before another collection")
    env = environment()
    env.update({"run_started_utc": datetime.now(timezone.utc).isoformat(),
                "scope": "missing A4 inference and storage only; no fit/tune/calibration-fit",
                "audit_sha256_before_measurement": sha(REPORT / "A4_BENCHMARK_COMPLETENESS_AUDIT.md"),
                "serialization_in_inference_timer": False, "cold_start_measured": False,
                "repetition_unit": "one complete call (one record or 256-record batch)",
                "percentile_method": "numpy.quantile linear interpolation across 20 serial calls",
                "background_conditions": "single benchmark process; no concurrent agent training/tests; OS background work uncontrolled",
                "fitted_estimator_thread_settings": {}, "input_conditions": {}})
    samples = json.loads((A4 / "in_progress_samples.json").read_text()) if resume else []
    env["retained_checkpoint_workloads"] = len(samples)
    env["resumption_note"] = "Retained timing samples are reused unchanged after a storage-only parity failure; final environment reverified with same interpreter, dependencies and thread command. No best-of-run selection."
    rows = [{"dataset":s["dataset"],"evidence":"a4_supplement_direct_measurement", "system":s["system"],
             "operation":s["operation"],"batch_n":s["batch_n"],"panel":s.get("panel",""),
             "source":str((A4 / "supplement_raw_samples.json").relative_to(ROOT)),
             **{k:v for k,v in s.items() if k not in {"raw_seconds","dataset","system","operation","batch_n","panel"}}} for s in samples]
    storage, history, trial_rows = [], [], []
    parity_count, parity_max_difference = 0, 0.
    write_json(A4 / "in_progress_environment.json", env)
    for dataset, directory, metadata in studies():
        print("A4 inference:", dataset, flush=True)
        c = next(contexts(dataset, directory, metadata))
        bundle = c["bundle"]
        # Small-cohort n=256 is a timing-only workload from predictor order,
        # independent of outcomes, not a new validation population.
        if dataset in {"pidd", "sylhet"}:
            frame = c["loaded"].X
            population = "frozen raw predictor order; includes some model-training records; timing only"
        else:
            frame = c["loaded"].X.iloc[c["evaluation"]["row_position"].to_numpy(int)]
            population = "first-router frozen test predictor order; timing only"
        positions = np.flatnonzero(_supported_scenarios(frame, bundle["scenarios"]) != "")[:256]
        if len(positions) != 256:
            raise ValueError("256 distinct supported input rows required")
        eligible = frame.iloc[positions].reset_index(drop=True)
        env["input_conditions"][dataset] = {"batch_n": 256, "selection": population,
            "source_router": str(c["bundle_path"].relative_to(ROOT)), "router_sha256": sha(c["bundle_path"]),
            "positions_sha256": hashlib.sha256(positions.tobytes()).hexdigest(),
            "outcomes_used_for_selection": False}
        env["fitted_estimator_thread_settings"][dataset] = {}
        for family, base in bundle["model_bundles"].items():
            estimator = base["model"].estimator
            params = estimator.get_params()
            env["fitted_estimator_thread_settings"][dataset][family] = {
                k: params.get(k, "not specified") for k in ["n_jobs", "thread_count", "task_type", "device", "tree_method"]}

        def record(system, operation, n, call, panel=""):
            if any(s["dataset"]==dataset and s["system"]==system and s["operation"]==operation and s["batch_n"]==n for s in samples):
                return
            timing = measured(call)
            samples.append({"dataset": dataset, "system": system, "operation": operation,
                            "batch_n": n, "panel": panel, **timing})
            write_json(A4 / "in_progress_samples.json", samples)
            rows.append({"dataset": dataset, "evidence": "a4_supplement_direct_measurement",
                         "system": system, "operation": operation, "batch_n": n, "panel": panel,
                         "source": str((A4 / "supplement_raw_samples.json").relative_to(ROOT)),
                         **{k:v for k,v in timing.items() if k != "raw_seconds"}})

        for n in [1, 256]:
            f = eligible.head(n).copy()
            panel = _supported_scenarios(f, bundle["scenarios"])[0]
            family = bundle["selected_models"][panel]
            base = bundle["model_bundles"][family]
            ordered = f.reindex(columns=bundle["configured_features"]).copy()
            for feature in set(bundle["configured_features"]) - set(bundle["scenarios"][panel]):
                ordered[feature] = np.nan
            transformed = base["preprocessor"].transform(ordered)
            raw = base["model"].predict_proba(transformed)
            cal = bundle["scenario_calibrators"][family][panel]
            record("framework_first_record_panel", "calibration_application_only", n,
                   lambda: cal.predict(raw), panel)
            if n == 256 and dataset in {"pidd", "sylhet"}:
                record("framework_one_router", "routing_eligibility_only", n,
                       lambda: _supported_scenarios(f, bundle["scenarios"]))
                record("framework_first_record_panel", "preprocessing_transform", n,
                       lambda: base["preprocessor"].transform(ordered), panel)
                record("framework_first_record_panel", "base_model_predict_only", n,
                       lambda: base["model"].predict_proba(transformed), panel)
                record("D_framework_one_router", "end_to_end_prediction", n,
                       lambda: routed_predict(bundle, f))
                record("A_fixed_imputation_one_router", "end_to_end_prediction", n,
                       lambda: routed_predict(bundle, f, True))
        # No inference timers below this point.
        history.append({"dataset": dataset, "run_started_utc": metadata["run_started_at_utc"],
            "run_completed_utc": metadata["run_completed_at_utc"],
            "runner_interval_seconds": elapsed_utc(metadata["run_started_at_utc"], metadata["run_completed_at_utc"]),
            "classification": "DERIVABLE FROM VALID RECORDED TIMESTAMPS",
            "historical_hardware": "NOT RECOVERABLE", "historical_model_n_jobs": metadata["model_n_jobs"],
            "declared_lock_sha256": metadata["requirements_lock_sha256"],
            "retained_lock_matches": metadata["requirements_lock_sha256"] == sha(ROOT / "requirements.lock"),
            "source": str((directory / "experiment_metadata.json").relative_to(ROOT))})
        for path in sorted((directory / "trials").glob("*.csv")):
            t = read_cost_csv(path)
            starts, ends = pd.to_datetime(t.datetime_start), pd.to_datetime(t.datetime_complete)
            derived = (ends - starts).dt.total_seconds()
            saved = pd.to_timedelta(t.duration).dt.total_seconds()
            if len(t) != 75 or derived.isna().any() or (derived < 0).any() or not np.allclose(saved, derived, atol=1e-6, rtol=0):
                raise ValueError("Invalid historical trial duration records")
            trial_rows.append({"dataset": dataset, "search": path.stem, "trials": len(t),
                "trial_duration_sum_seconds": saved.sum(), "trial_duration_median_seconds": saved.median(),
                "trial_duration_p05_seconds": saved.quantile(.05), "trial_duration_p95_seconds": saved.quantile(.95),
                "search_timestamp_span_seconds": (ends.max() - starts.min()).total_seconds(),
                "timezone": "naive as saved; no cross-file timezone conversion assumed",
                "classification": "DERIVABLE FROM VALID RECORDED TIMESTAMPS",
                "source": str(path.relative_to(ROOT)), "source_sha256": sha(path)})

        def store(scope, base, calibrator, source, panel="", family="", repeat=0, fold=0, actual=None):
            triple = {"model": base["model"], "preprocessor": base["preprocessor"], "calibrator": calibrator}
            storage.append({"dataset": dataset, "scope": scope, "panel": panel, "family": family,
                "repeat": repeat, "outer_fold": fold, "preprocessor_bytes": serialized_bytes(base["preprocessor"]),
                "model_bytes": serialized_bytes(base["model"]), "calibrator_bytes": serialized_bytes(calibrator),
                "combined_bytes": serialized_bytes(triple), "actual_file_bytes": actual,
                "source": str(source.relative_to(ROOT)), "source_sha256": sha(source),
                "method": "independent and combined joblib compress=3; actual file stat separately"})

        print("A4 storage:", dataset, flush=True)
        complete_bytes = selected_bytes = selected_models = 0
        for path in bundle_paths(directory):
            b = joblib.load(path)
            repeat, fold = int(b.get("repeat",0)), int(b.get("outer_fold",0))
            pruned = selected_payload(b)
            # Verify storage-only payload can perform each forced panel. Exact
            # same loaded objects; no fitting and no saved predictions.
            # An assembled complete predictor row is a parity probe only.
            # Hospital130 has no observed all-feature-complete row; never
            # include this manufactured probe in the latency workload.
            probe = c["loaded"].X.head(1).copy()
            for feature in b["configured_features"]:
                if pd.isna(probe[feature].iloc[0]):
                    observed = c["loaded"].X[feature].dropna()
                    if len(observed) == 0:
                        raise ValueError("Cannot construct complete storage parity probe")
                    probe[feature] = observed.iloc[0]
            for panel, family in b["selected_models"].items():
                a = route_patient(b, probe, scenario_name=panel)
                z = route_patient(pruned, probe, scenario_name=panel)
                if not prediction_parity(a, z):
                    raise ValueError("Pruned storage payload changes inference")
                parity_count += 1
                parity_max_difference = max(parity_max_difference, abs(a["probability_raw"]-z["probability_raw"]),
                                            abs(a["probability_calibrated"]-z["probability_calibrated"]))
                store("original_selected_panel_configuration", b["model_bundles"][family],
                      b["scenario_calibrators"][family][panel], path, panel, family, repeat, fold)
            size = serialized_bytes(pruned)
            count = len(pruned["model_bundles"])
            selected_bytes += size; selected_models += count; complete_bytes += path.stat().st_size
            storage.append({"dataset":dataset,"scope":"selected_runtime_one_router_payload","repeat":repeat,
                "outer_fold":fold,"combined_bytes":size,"unique_models":count,"source":str(path.relative_to(ROOT)),
                "source_sha256":sha(path),"method":"joblib compress=3 pruned D payload; shared fold-family stored once; parity checked all panels"})
        for path in sorted((directory / "models").glob("*.joblib")):
            base = joblib.load(path)
            store("original_full_model_alternative",base,base["calibrator"],path,"full",base["model_name"],
                  int(base.get("repeat",0)),int(base.get("outer_fold",0)),path.stat().st_size)
        reduced_actual = reduced_triple = reduced_count = 0
        for path in sorted((PRIVATE / "panel_tasks" / dataset).glob("*/*/bundle.joblib")):
            base = joblib.load(path)
            task = json.loads((path.parent / "task.json").read_text())
            store("independently_retrained_reduced_configuration",base,base["calibrator"],path,task["panel"],
                  task["family"],task["repeat"],task["fold"],path.stat().st_size)
            reduced_actual += path.stat().st_size; reduced_triple += storage[-1]["combined_bytes"]; reduced_count += 1
        for scope, size, count in [("selected_runtime_all_routers_payload",selected_bytes,selected_models),
                                   ("actual_complete_router_collection",complete_bytes,len(bundle_paths(directory))*4),
                                   ("independently_retrained_reduced_collection_actual",reduced_actual,reduced_count),
                                   ("independently_retrained_reduced_collection_prediction_triples",reduced_triple,reduced_count)]:
            storage.append({"dataset":dataset,"scope":scope,"combined_bytes":size,"unique_models":count,
                "source":str((directory/'availability_routing/router_bundles' if scope.startswith(('selected','actual'))
                               else PRIVATE/'panel_tasks'/dataset).relative_to(ROOT)),
                "method":"sum of separately serialized router payloads or actual bundle files; no sharing across distinct fold-family keys"})
    env["run_completed_utc"] = datetime.now(timezone.utc).isoformat()
    env["storage_parity"] = {"forced_panel_checks":parity_count,"maximum_probability_absolute_difference":parity_max_difference,
        "probability_absolute_tolerance":1e-14,"all_other_output_fields_exact":True,
        "probe":"assembled complete predictor row for storage parity only; never latency input"}
    write_json(A4 / "supplement_raw_samples.json", samples)
    write_json(REPORT / "A4_BENCHMARK_ENVIRONMENT.json", env)
    pd.DataFrame(rows).to_csv(A4 / "supplement_cost_rows.csv",index=False)
    pd.DataFrame(storage).to_csv(REPORT / "A4_STORAGE_DETAILS.csv",index=False)
    pd.DataFrame(history).to_csv(REPORT / "A4_HISTORICAL_TIMING.csv",index=False)
    pd.DataFrame(trial_rows).to_csv(REPORT / "A4_HISTORICAL_TRIAL_TIMING.csv",index=False)
    print("Completed missing measurements without fitting:",len(rows),"timing rows,",len(storage),"storage rows",flush=True)


def reports():
    """Regenerate publication tables only from retained measurements."""
    prior = A4 / "previous_handoff/analysis/journal_revision/06_COMPUTATIONAL_COST.csv"
    old = read_cost_csv(prior)
    supplement = read_cost_csv(A4 / "supplement_cost_rows.csv")
    storage = read_cost_csv(REPORT / "A4_STORAGE_DETAILS.csv")
    for column in ["preprocessor_bytes","model_bytes","calibrator_bytes","combined_bytes","actual_file_bytes"]:
        storage[column.replace("_bytes","_MiB")]=storage[column]/2**20
    storage.to_csv(REPORT / "A4_STORAGE_DETAILS.csv",index=False)
    history = read_cost_csv(REPORT / "A4_HISTORICAL_TIMING.csv")
    trials = read_cost_csv(REPORT / "A4_HISTORICAL_TRIAL_TIMING.csv")
    canonical = read_cost_csv(REPORT / "A4_COMPONENT_STORAGE_VERIFICATION.csv")
    registry = {d:(p,m) for d,p,m in studies()}
    # Fill missing legacy provenance without changing any retained measurements.
    old["environment_id"] = np.where(old.evidence == "original_recorded_timing", "H_historical_unknown_hardware", "L_prior_local")
    for dataset, (directory, metadata) in registry.items():
        task_files = iter(sorted((PRIVATE / "panel_tasks" / dataset).glob("*/*/task.json")))
        reduced = [p for p in task_files if p.parent.name != "full"]
        size_iterator = iter(reduced)
        for index in old.index[old.dataset == dataset]:
            op = old.at[index,"operation"]
            if pd.notna(old.at[index,"source"]):
                continue
            if op == "new_panel_combined_artifact_size":
                p = next(size_iterator).parent / "bundle.joblib"
            elif old.at[index,"evidence"] == "new_local_controlled_measurement" and pd.notna(old.at[index,"median_seconds"]):
                p = PRIVATE / "benchmark_raw_samples.json"
            elif op == "actual_original_artifact_storage":
                p = directory
            else:
                p = bundle_paths(directory)[0]
            old.at[index,"source"] = str(p.relative_to(ROOT))
    supplement["environment_id"] = "N_A4_supplement"
    extra = []
    for _, row in storage.iterrows():
        extra.append({"dataset":row.dataset,"evidence":"a4_storage_verification", "system":row.get("family", ""),
            "operation":"a4_storage_"+row.scope,"panel":row.get("panel", ""),"repeat":row.get("repeat",np.nan),
            "outer_fold":row.get("outer_fold",np.nan),"bytes":row.combined_bytes,
            "preprocessor_bytes":row.get("preprocessor_bytes",np.nan),"model_bytes":row.get("model_bytes",np.nan),
            "calibrator_bytes":row.get("calibrator_bytes",np.nan),"actual_file_bytes":row.get("actual_file_bytes",np.nan),
            "source":"analysis/journal_revision/A4_STORAGE_DETAILS.csv", "artifact_source":row.source,
            "compression":row.method,"environment_id":"N_A4_supplement"})
    for _, row in history.iterrows():
        extra.append({"dataset":row.dataset,"operation":"historical_runner_invocation_interval", "system":"five_model_runner",
            "evidence":"historical_timestamp_derivation","total_seconds":row.runner_interval_seconds,
            "source":row.source,"environment_id":"H_historical_unknown_hardware"})
    for _, row in trials.iterrows():
        extra.append({"dataset":row.dataset,"operation":"historical_trial_objective_duration_sum", "system":row.search,
            "evidence":"historical_timestamp_derivation","total_seconds":row.trial_duration_sum_seconds,
            "median_seconds":row.trial_duration_median_seconds,"task_count":row.trials,
            "source":row.source,"environment_id":"H_historical_unknown_hardware"})
    for _, row in canonical.iterrows():
        extra.append({"dataset":row.dataset,"operation":"a4_canonical_exemplar_"+row.operation,
            "system":"original_first_router_runtime_panel","evidence":"a4_saved_serialization_file_bytes",
            "bytes":row.current_saved_bytes,"source":row.source,"artifact_source":row.original_router_source,
            "compression":"joblib compress=3; saved file stat+SHA","environment_id":"N_A4_supplement"})
    costs = pd.concat([old, supplement, pd.DataFrame(extra)],ignore_index=True)
    costs["value_origin"] = np.select([costs.evidence == "original_recorded_timing",
        costs.evidence == "historical_timestamp_derivation",costs.operation == "new_panel_tuning_seconds"],
        ["historical direct timers; aggregates derived","historical timestamp derivation","design fact: no tuning performed"],
        default="post-review direct measurement or explicitly described aggregation")
    for col in ["median","p05","p95","min","max"]:
        costs[col+"_ms"] = (costs[col+"_seconds"]*1000).where(costs.repetitions.notna())
    costs["storage_MiB"] = costs.bytes / 2**20
    costs["source_sha256"] = costs.source.map(lambda s:sha(ROOT/s) if (ROOT/s).is_file() else "directory; individual hashes in protected baseline or A4 storage ledger")
    costs["result_key"] = [f"cost_{i:05d}" for i in range(len(costs))]
    costs.to_csv(REPORT / "06_COMPUTATIONAL_COST.csv",index=False)

    # All supplementary inference rows retain actual n (including prior 154/104).
    inference = costs[costs.repetitions.notna()].copy()
    inference.to_csv(REPORT / "A4_INFERENCE_SUMMARY.csv",index=False)
    training = []
    for (dataset,operation),group in old[old.evidence == "new_post_review_execution_timing"].groupby(["dataset","operation"]):
        vals=group.total_seconds
        training.append({"dataset":dataset,"component":operation,"tasks":len(group),"total_seconds":vals.sum(),
            "median_seconds":vals.median(),"p05_seconds":vals.quantile(.05),"p95_seconds":vals.quantile(.95),
            "min_seconds":vals.min(),"max_seconds":vals.max(),"evidence":"already completed successor task timers",
            "source":"06_COMPUTATIONAL_COST.csv; per-task source column"})
    training=pd.DataFrame(training)
    training.to_csv(REPORT / "A4_TRAINING_SUMMARY.csv",index=False)
    main=[]
    for dataset in registry:
        t=training[training.dataset == dataset].set_index("component")
        d=inference[(inference.dataset == dataset)&(inference.system == "D_framework_one_router")&
                    (inference.operation == "end_to_end_prediction")].set_index("batch_n")
        # Representative actual runtime panel from the first frozen evaluation
        # record, matching the retained first-router storage exemplar.
        sample=canonical[canonical.dataset==dataset].set_index("operation")
        main.append({"dataset":dataset,"reduced_tasks":int(t.iloc[0].tasks),
            "successor_final_fit_sum_s":t.loc["new_panel_final_model_fit_seconds","total_seconds"],
            "successor_calibration_sum_s":t.loc["new_panel_calibration_seconds","total_seconds"],
            "D_single_median_ms":d.loc[1,"median_ms"],"D_batch256_median_ms":d.loc[256,"median_ms"],
            "exemplar_model_MiB":sample.loc["model_serialized_bytes","current_saved_bytes"]/2**20,
            "exemplar_calibrator_MiB":sample.loc["calibrator_serialized_bytes","current_saved_bytes"]/2**20,
            "exemplar_prediction_triple_MiB":sample.loc["model_preprocessor_calibrator_serialized_bytes","current_saved_bytes"]/2**20,
            "source":"06_COMPUTATIONAL_COST.csv; A4_TRAINING_SUMMARY.csv; A4_COMPONENT_STORAGE_VERIFICATION.csv"})
    main=pd.DataFrame(main)
    main.to_csv(REPORT / "A4_MAIN_TEXT_TABLE.csv",index=False)
    historical=old[old.evidence == "original_recorded_timing"][["dataset","system","operation","task_count","total_seconds","median_seconds","min_seconds","max_seconds","source"]]
    historical.to_csv(REPORT / "A4_HISTORICAL_MODEL_COSTS.csv",index=False)
    paired=[]
    for dataset in registry:
        for n in [1,256]:
            sample=inference[(inference.dataset==dataset)&(inference.batch_n==n)&(inference.operation=="end_to_end_prediction")]
            a=sample[sample.system=="A_fixed_imputation_one_router"].iloc[0]
            d=sample[sample.system=="D_framework_one_router"].iloc[0]
            paired.append({"dataset":dataset,"batch_n":n,"A_median_ms":a.median_ms,"D_median_ms":d.median_ms,
                "D_over_A_median_ratio":d.median_ms/a.median_ms,"environment_id":d.environment_id,
                "source":"06_COMPUTATIONAL_COST.csv; matched input/environment within each row"})
    paired=pd.DataFrame(paired);paired.to_csv(REPORT / "A4_COMPARATOR_COSTS.csv",index=False)
    env=json.loads((REPORT/"A4_BENCHMARK_ENVIRONMENT.json").read_text())
    cond="""Loaded CPU artifacts; perf_counter_ns elapsed wall time; three untimed warmups followed by 20 serial timed calls for each workload; median and linearly interpolated p05/p95 with observed minimum/maximum. Each call handles one record or one entire 256-record batch; batch latency is not per-record latency. OMP_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1, VECLIB_MAXIMUM_THREADS=1, MKL_NUM_THREADS unset. Saved estimators retain their own thread settings (typically n_jobs/thread_count=4); this is not an all-single-thread estimator benchmark. No disk loading, serialization, SHAP, explanations or report generation is inside inference timers. No cold-start latency was measured. No concurrent agent training/tests ran during the supplement; OS background activity was uncontrolled. Earlier controlled inference ran after the earlier long-running jobs finished. Already recorded successor training timers sometimes overlapped other work and are representative elapsed component costs, not an isolated hardware speed leaderboard."""
    method="""Historical tuning and final estimator fitting are reported from saved timers in the authoritative studies. PIDD/Sylhet metric rows were deduplicated by family/repeat/outer-fold (25 fitted models per family); holdout cohorts have one final model per family. Tuning comprises 75 Optuna trials per search, including objective validation, and excludes subsequent best-parameter OOF construction and final fitting. Separate historical OOF, preprocessing, calibration and inference times were not recorded. The completed matched-parameter reduced-schema successor supplies representative OOF, preprocessing, final-fit and calibration-selection timers; no new tuning occurred. Its OOF loop includes five preprocessing/fit/predict cycles and bookkeeping, while final fitting excludes preprocessing and calibration includes candidate cross-fitting, selection and final mapping. These are different workloads from the historical full-schema models and are never substituted for their missing timings."""
    selection="""Earlier single-record and BRFSS/Hospital130 batch benchmarks use the first supported records in the first frozen evaluation partition. Prior PIDD/Sylhet batches were only 154/104 records and remain labeled with their actual sizes. The A4 supplement times the first 256 supported PIDD/Sylhet predictor rows in frozen raw order; some were training records for that router. Outcomes do not select the timing inputs, no performance metrics are computed, and no scientific predictions are saved. This is a representative throughput workload, not a new validation population. Only the missing 256-record components/end-to-end calls and calibration application were timed anew. Calibration-only timings use the first input's selected panel on precomputed raw scores. Existing preprocessing/model components use that panel for the whole batch, whereas routed end-to-end calls select each record's panel. Component medians cannot be summed to reconstruct mixed-panel end-to-end latency."""
    storage_text="""All storage uses MiB = bytes/1,048,576 (not decimal MB). Original file sizes were verified by file stat; model, preprocessing, calibrator and prediction-triple sizes use controlled independent joblib compress=3 serialization. Compression is non-additive: the triple is serialized jointly, not obtained by summing compressed component sizes. A4_STORAGE_DETAILS.csv covers every selected original panel/fold configuration, all five full-model alternatives and every already fitted reduced panel. A selected-runtime payload stores one model/preprocessor per distinct fold-family and only the mappings needed by D; forced-panel prediction parity was verified for every panel (maximum probability difference 1.11e-16 from parallel arithmetic; decisions/metadata exact). These private storage-only payloads are saved with byte counts and SHA-256, excluding alternative systems, SHAP background/reference data and unused metadata; they do not replace preserved routers. All-router payload totals sum those saved payload files; distinct fitted fold-family keys are counted separately, with no shared model counted again per panel. The actual complete-router collection additionally retains four families/all mappings/metadata. The original archive sum includes all five benchmark families plus duplicated model objects in routers and is not a deployment requirement. The independent reduced collection excludes the reused full controls; a combined original-plus-reduced deployment would need both collections. Serialized bytes are not resident/peak RAM. Earlier in-memory whole-router and some component compressed sizes were not reproduced exactly in a fresh process; warming did not explain the whole-router differences. The cause is unestablished. Legacy observations remain in 06; A4_STORAGE_VERIFICATION.csv and A4_COMPONENT_STORAGE_VERIFICATION.csv disclose all differences. Publication example/component sizes and deployment totals use saved, hash-verified compressed files. Other configuration serializations describe their captured object state; no cross-process byte-stability claim is made for arbitrary reserialization."""
    hardware=(f"Observed local benchmark hardware: {env['cpu']}, {env['hardware_model']} {env['hardware_details']['machine_name']}, "
        f"{env['logical_cpus']} logical CPUs (hardware processor descriptor {env['hardware_details']['number_processors']}), installed RAM {env['hardware_details']['physical_memory']} "
        f"({env['ram_bytes']} bytes); {env['operating_system']}, {env['architecture']}. CPU only. Python {env['python']}. "
        "Installed dependency versions: "+", ".join(k+" "+v for k,v in env['package_versions'].items())+". "
        "BENCHMARK_ENVIRONMENT.json retains the earlier observed environment; A4_BENCHMARK_ENVIRONMENT.json separately captures this supplement. "
        "Historical metadata records model_n_jobs=4 and a requirements-lock hash matching the retained lock, which declares these core package versions. "
        "Historical CPU/RAM/OS/interpreter, installed-version snapshot, free RAM, peak process RAM, accelerator telemetry and concurrency are unavailable. Current hardware must not be attributed to historical training. No GPU timing claim is made for history.")
    limitations="""A4 reporting completeness: COMPLETE. Historical component timing reconstruction: PARTIAL. Exact historical training replay: BLOCKED (original source fingerprint unavailable; HISTORICAL_SOURCE_SEARCH.json). Historical timers remain evidence of recorded costs, not a promise that durations can be reproduced. Metadata start/end differences recover only the recorded runner invocation interval, including other runner work; they do not cover separately invoked routing, explanation or publication stages and are not total pipeline time. No missing component was calculated by subtraction. Trial CSV timestamps are timezone-naive as saved; within-file durations were checked against their duration column without assuming a timezone conversion. Trial-objective sums are diagnostic subsets of tuning, not additional compute to add to tuning. Separate historical calibration/OOF/preprocessing/inference times, entire-pipeline runtime and peak RAM remain unavailable. The small-cohort 256 workloads and first-panel component examples have the limits stated above. Only 20 serial repetitions describe local variability; no independent-run uncertainty, deployment capacity, energy cost, optimized panel-model search or clinical validation is claimed. No further model training is needed for A4."""
    maincols=["dataset","successor_final_fit_sum_s","successor_calibration_sum_s","D_single_median_ms","D_batch256_median_ms","exemplar_model_MiB","exemplar_calibrator_MiB","exemplar_prediction_triple_MiB"]
    main_md=publication_table(main[maincols])
    timed_cols=["dataset","system","operation","batch_n","median_ms","p05_ms","p95_ms","min_ms","max_ms","environment_id"]
    deployments=storage[storage.scope.isin(["selected_runtime_one_router_payload","selected_runtime_all_routers_payload","actual_complete_router_collection","independently_retrained_reduced_collection_actual"])].copy()
    deployments["combined_MiB"]=deployments.combined_bytes/2**20
    # All routers have per-fold details in the CSV; main supplement shows first
    # router plus cohort collections without concealing the distributions.
    deploy_table=deployments[(deployments.scope!="selected_runtime_one_router_payload")|((deployments["repeat"]==0)&(deployments.outer_fold==0))]
    historical_md=publication_table(historical.drop(columns="source"))
    doc=["# A4 publication-ready computational cost", "", "A4 reporting: **COMPLETE**. Exact historical computational replay: **BLOCKED**; component reconstruction: **PARTIAL**. No training was performed for this completion task.",
        "", "## Methodology", "",method,"",cond,"",selection,
        "", "## Main-text-ready table", "", "Final-fit and calibration columns below are SUMS over the completed reduced-schema successor tasks (125 PIDD, 100 Sylhet, five BRFSS, four Hospital130), not fitting times for the original router exemplars. Inference is original fitted-artifact D with one router. Storage is the first-router runtime-panel example, with compressed files saved for byte/hash verification. Model and calibrator columns are independent serializations; prediction triple also contains preprocessing. Values derive from A4_MAIN_TEXT_TABLE.csv / 06_COMPUTATIONAL_COST.csv / A4_COMPONENT_STORAGE_VERIFICATION.csv.","",main_md,
        "", "Suggested accompanying text: Computational costs were separated into hyperparameter search, OOF generation, final preprocessing/model fitting, calibration selection/fitting and warmed prediction. Historical search/final-fit timers were retained; representative component costs and loaded-artifact inference were measured locally. Historical component gaps and execution-environment limits are disclosed. The reported latencies exclude loading and explanations.",
        "", "## Supplement: historical costs and runner intervals", "", "Training/calibration units are seconds. Historical family rows are sums and per-task distribution summaries; 25 tasks/family in repeated cohorts and one in each holdout. All five simpler/full-model alternatives use the same cohort's recorded workflow and tuning budget; unknown resource contention precludes a controlled hardware speed ranking. Compare within cohort, without assigning current hardware to history.","",historical_md,
        "",markdown_table(history[["dataset","run_started_utc","run_completed_utc","runner_interval_seconds","classification"]]),
        "", "A4_HISTORICAL_TRIAL_TIMING.csv contains every search's 75 trial-duration distributions and timestamp spans, with exact source hashes. These are not added to tuning totals.",
        "", "## Supplement: completed successor component distributions", "",publication_table(training.drop(columns=["evidence","source"])),
        "", "All per-task durations, including panel/family/fold and direct task.json sources, remain in 06_COMPUTATIONAL_COST.csv. Zero tuning is a design fact, not a stopwatch result. OOF and final/calibration component totals cannot reconstruct whole successor wall time because other work and concurrency are outside these timers.",
        "", "## Supplement: latency distributions", "",publication_table(inference[timed_cols]),
        "", "The n=154/104 historical local benchmark rows remain alongside the new n=256 rows. The public single-record API and all-router research ensemble are separate workloads. Ensemble probability-only cost does not equal five OOF probabilities or a patient report with SHAP.",
        "", "## Comparison with simpler alternatives", "",publication_table(paired.drop(columns="source")),
        "", "A is the fixed-imputation robust-family/full-calibrator comparator; D includes scenario selection and panel mapping. Each ratio is a descriptive ratio of medians on matched inputs/environment, not a paired significance test. All five original families' training and storage are also available; Logistic Regression offers a simpler fitted alternative, but no new Logistic Regression latency or predictive comparison was run for A4.",
        "", "## Storage requirements", "",storage_text,"",publication_table(deploy_table[["dataset","scope","repeat","outer_fold","unique_models","combined_MiB"]]),
        "",markdown_table(read_cost_csv(REPORT/"A4_STORAGE_VERIFICATION.csv")[["dataset","legacy_recorded_bytes","current_loaded_bytes","current_warmed_bytes","actual_file_bytes","warmed_difference_bytes"]]),
        "",markdown_table(canonical[["dataset","operation","legacy_recorded_bytes","current_saved_bytes","difference_bytes"]]),
        "", "Per-configuration preprocessing/model/calibrator/triple bytes and MiB conversions are supplied by A4_STORAGE_DETAILS.csv and 06_COMPUTATIONAL_COST.csv; actual full/reduced bundle bytes are separate columns. Panel-config triples must not be summed to estimate router storage because they repeat shared models.",
        "", "## Hardware and software", "",hardware,
        "", "## Limitations and status", "",limitations,
        "", "## Numerical provenance and reproduction", "", "Every 06 row has result_key, source and source_sha256. Original timers point to authoritative historical CSVs; successor timers point to task.json; L timings point to benchmark_raw_samples.json; N timings point to a4_reporting_v2/supplement_raw_samples.json; storage points to A4_STORAGE_DETAILS.csv with fitted-object file hashes, and canonical example files to A4_COMPONENT_STORAGE_VERIFICATION.csv. A4_MAIN_TEXT_TABLE.csv, A4_TRAINING_SUMMARY.csv, A4_INFERENCE_SUMMARY.csv, A4_HISTORICAL_MODEL_COSTS.csv and A4_COMPARATOR_COSTS.csv are deterministic views of 06. Historical intervals/trial summaries point to metadata/trial CSVs. ANALYSIS_SOURCE_MAP.csv maps every cost and derived-table row to its command, source, split/protocol and output hash. See REPRODUCE.md for read-only table reconstruction, verification and optional separately versioned timing collection. Existing measurements are retained by default; re-timing is not needed to reproduce these tables.", ""]
    (REPORT / "A4_PUBLICATION_READY_SUMMARY.md").write_text("\n".join(doc))
    (REPORT / "06_COMPUTATIONAL_COST.md").write_text("# Computational cost\n\nA4 reporting COMPLETE; historical reconstruction PARTIAL; exact historical replay BLOCKED.\n\n"+
        method+"\n\n"+cond+"\n\n"+selection+"\n\n"+main_md+"\n\n"+storage_text+"\n\n"+hardware+"\n\n"+limitations+
        "\n\nFull distributions, sources, supplement tables and instructions: A4_PUBLICATION_READY_SUMMARY.md, A4_* CSVs, ANALYSIS_SOURCE_MAP.csv and REPRODUCE.md.\n")
    reconcile_docs()
    source_map()


def reconcile_docs():
    status=read_cost_csv(REPORT/"WORK_STATUS.csv")
    name="Mentor requirement A4 reporting completeness"
    status=status[status.work!=name]
    status=pd.concat([status,pd.DataFrame([{"work":name,"status":"COMPLETE",
        "boundary":"Every cost category addressed with sources/conditions; missing historical measurements disclosed; no new training"}])],ignore_index=True)
    status.loc[status.work=="Historical component cost reconstruction","boundary"]="Original tuning/final-fit timers and valid runner intervals available; original OOF/preprocessing/calibration/inference and peak RAM unavailable"
    status.to_csv(REPORT/"WORK_STATUS.csv",index=False)
    p=REPORT/"MENTOR_RESPONSE_EVIDENCE.md";text=p.read_text()
    start=text.index("## A4 cost");end=text.index("\n## ",start+5)
    text=text[:start]+"""## A4 cost

Mentor requirement A4 reporting completeness: COMPLETE.
Historical component reconstruction: PARTIAL. Exact historical computational replay: BLOCKED.

Work completed: Existing training/tuning/OOF/calibration timers audited; valid historical runner intervals and trial timestamps checked; only missing calibration application and small-cohort 256-record inference timed; all relevant fitted-artifact storage verified with shared models counted once.

Evidence generated/output: A4_BENCHMARK_COMPLETENESS_AUDIT.md; 06_COMPUTATIONAL_COST.csv/.md; A4_PUBLICATION_READY_SUMMARY.md; A4_* tables; BENCHMARK_ENVIRONMENT.json; A4_BENCHMARK_ENVIRONMENT.json; A4_VERIFICATION.json.

Key finding: Every requested cost category is addressed with defined units, timing conditions and historical/new provenance. No new fitting or tuning was needed.

Limitations: Separate historical OOF/preprocessing/calibration/inference durations, entire-pipeline elapsed time, original hardware/runtime snapshot and peak RAM remain unavailable. New timings are representative, not reconstructed historical durations.
"""+text[end:];p.write_text(text)
    p=REPORT/"FINAL_MODEL_ANALYSIS_REPORT.md";text=p.read_text()
    text=text.replace("Overall status: PARTIAL. Declared successor experiments", "Overall status: PARTIAL. Mentor A4 computational reporting is COMPLETE; this does not complete historical replay. Declared successor experiments")
    start=text.index("## 11. Computational cost");end=text.index("\n## 12.",start)
    main=read_cost_csv(REPORT/"A4_MAIN_TEXT_TABLE.csv")
    text=text[:start]+"## 11. Computational cost\n\nA4 reporting completeness: COMPLETE. Historical component reconstruction: PARTIAL; exact historical replay: BLOCKED. Existing historical tuning/final-fit timers and completed successor OOF/preprocessing/final-fit/calibration timers were reused. Only missing calibration-application latency, exact 256-record PIDD/Sylhet throughput and storage decomposition/unique-model collections were supplemented; no model or calibration fitting occurred.\n\n"+markdown_table(main.drop(columns="source"))+"\n\nTraining/calibration columns are successor SUMS in seconds; inference is milliseconds per loaded one-router call on original fitted artifacts. Storage is MiB (2^20 bytes), independent model/calibrator and combined prediction triple for the first original runtime-panel exemplar. See A4_PUBLICATION_READY_SUMMARY.md for historical family timings, preprocessing/OOF components, exact conditions, p05/p95/ranges, all storage configurations, source files and limitations. Current Apple M2 Pro/16 GB hardware is not attributed to historical training.\n"+text[end:]
    p.write_text(text)
    p=REPORT/"REPRODUCE.md";text=p.read_text();marker="\n## A4 reporting supplement"
    text=text.split(marker)[0]
    text+="""
## A4 reporting supplement

For this completed cost-only task, do not invoke pilot/train, the full study orchestrator, or the legacy benchmark. No further fitting is necessary. Preserve the old sealed ZIP and private previous_handoff snapshot. Original private artifacts, prior measurement samples and A4 supplement samples must be restored for numerical reproduction; a Git clone alone does not contain them.

The A4 table generator reads retained measurements and performs no fitting or new timing:

```bash
.venv-pipeline/bin/python scripts/complete_a4_reporting.py report
.venv-pipeline/bin/python scripts/complete_a4_reporting.py verify
.venv-pipeline/bin/python scripts/verify_journal_revision.py
.venv-pipeline/bin/python -m pytest -q
```

The legacy `report` command regenerates the earlier report format. If it is used, run the A4 `report` command afterwards to restore the current computational sections/provenance. Numerical A4 reports are reproducible from saved measurements; current handoff hashes deliberately detect accidental edits. A4 verification checks the old-to-new measurement values, every table, original/protected and successor scientific artifacts, old ZIP and manuscript files. A4_VERIFICATION.json records results. The successor handoff checksum manifest is extended only after the authorized A4 change boundary and all preserved earlier non-A4 hashes pass; previous_handoff retains the prior manifest/files.

Optional new measurement collection is not needed for this report. To remeasure, preserve the whole package and use a separate checkout with a separately versioned A4 output directory; do not replace current raw samples. After the same audit and source review, the timing-only entry point is:

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv-pipeline/bin/python scripts/complete_a4_reporting.py collect
.venv-pipeline/bin/python scripts/complete_a4_reporting.py storage
.venv-pipeline/bin/python scripts/complete_a4_reporting.py components
.venv-pipeline/bin/python scripts/complete_a4_reporting.py report
.venv-pipeline/bin/python scripts/complete_a4_reporting.py verify
```

The delivered collect phase refuses to overwrite existing samples. It only loads fitted objects, predicts, serializes in memory and reads logs/file sizes; it contains no model/calibration fit or tuning call. It captures A4_BENCHMARK_ENVIRONMENT.json, 3 warmups/20 repetitions, all samples, estimator threads, source hashes and timing input conditions. The storage/components phases save separately versioned compressed prediction payloads/examples and their file-size/hash ledgers; they refuse replacement of existing payload directories. If collection stops during storage after saving timing checkpoints, preserve the failed log and use `resume` to reuse captured samples without retiming them. New timing distributions and cross-process serialization sizes may differ; issue a new handoff version and preserve both. Historical execution hardware/source remains unavailable, so exact historical replay stays BLOCKED independently of A4 COMPLETE.
"""
    p.write_text(text)


def source_map():
    """Retain scientific source rows; replace only cost rows and add A4 views."""
    p=REPORT/"ANALYSIS_SOURCE_MAP.csv";mapping=read_cost_csv(p)
    keep=mapping[~mapping.output_file.str.contains(r"/(?:06_COMPUTATIONAL_COST|A4_)")].copy()
    registry={d:(s,m) for d,s,m in studies()}
    additions=[]
    for file in [REPORT/"06_COMPUTATIONAL_COST.csv",*sorted(REPORT.glob("A4_*.csv"))]:
        table=read_cost_csv(file)
        for index,row in table.iterrows():
            dataset=row.dataset;directory,meta=registry[dataset]
            source=row.get("source", "analysis/journal_revision/06_COMPUTATIONAL_COST.csv")
            if not isinstance(source,str) or not (ROOT/source).exists():
                source="analysis/journal_revision/06_COMPUTATIONAL_COST.csv"
            additions.append({"result_id":f"{file.name}:row_{index+2}","dataset":dataset,"endpoint":meta["endpoint"],
                "experiment":"A4_cost_reporting","configuration":row.get("panel",row.get("scope","")),
                "system":row.get("system",row.get("family","")),"input_artifact":source,"input_artifacts":json.dumps([source]),
                "input_sha256":sha(ROOT/source) if (ROOT/source).is_file() else "per-file protected baseline / A4 storage ledger",
                "source_script":"scripts/complete_a4_reporting.py","source_module":"src/diabetes_pipeline/journal_revision/a4.py",
                "configuration_file":"analysis/journal_revision/A4_BENCHMARK_COMPLETENESS_AUDIT.md",
                "split_manifest":str(Path(meta["split_manifest"]).relative_to(ROOT)),"split_sha256":meta["split_manifest_sha256"],
                "seed":"no new training; timing inputs outcome-blind frozen order",
                "output_file":str(file.relative_to(ROOT)),"output_sha256":sha(file),
                "git_commit":json.loads((REPORT/"analysis_source_fingerprints.json").read_text())["git_commit"],
                "result_generation_command":".venv-pipeline/bin/python scripts/complete_a4_reporting.py report"})
    mapping=pd.concat([keep,pd.DataFrame(additions)],ignore_index=True)
    mapping.to_csv(p,index=False)
    p=REPORT/"ANALYSIS_SOURCE_MAP.md";text=p.read_text();text=text.split("\n## A4 extension")[0]
    text=text.replace("| analysis/journal_revision/06_COMPUTATIONAL_COST.csv | benchmark | .venv-pipeline/bin/python scripts/run_journal_revision.py benchmark |",
        "| analysis/journal_revision/06_COMPUTATIONAL_COST.csv | A4 cost reporting | .venv-pipeline/bin/python scripts/complete_a4_reporting.py report |")
    p.write_text(text+"\n## A4 extension\n\nEvery 06 and A4 CSV row is mapped to the A4 generator and direct source or exact derived-table input. Earlier non-cost scientific mappings are retained. Measurement origin and environment are explicit in 06; trial/storage ledgers bind individual artifacts. No participant/group IDs are exported.\n")
    p=REPORT/"analysis_source_fingerprints.json";fp=json.loads(p.read_text())
    for relative in ["src/diabetes_pipeline/journal_revision/a4.py","scripts/complete_a4_reporting.py","tests/test_a4_reporting.py"]:
        if (ROOT/relative).exists(): fp["files"][relative]=sha(ROOT/relative)
    write_json(p,fp)


def storage_verification():
    """Persist only pruned storage payloads; keep original routers unchanged."""
    payload_dir=A4/"storage_payloads"
    if payload_dir.exists():raise FileExistsError("Preserve saved payloads; do not replace")
    payload_dir.mkdir()
    p=REPORT/"A4_STORAGE_DETAILS.csv"
    (A4/"storage_details_before_payload_persistence.csv").write_bytes(p.read_bytes())
    storage=read_cost_csv(p)
    diagnostic_path=A4/"router_serialization_diagnostics.csv"
    if not diagnostic_path.exists():
        legacy=read_cost_csv(A4/"previous_handoff/analysis/journal_revision/06_COMPUTATIONAL_COST.csv")
        diagnostic_rows=[]
        for dataset,directory,metadata in studies():
            c=next(contexts(dataset,directory,metadata));b=c["bundle"]
            X=c["loaded"].X.iloc[c["evaluation"]["row_position"].to_numpy(int)]
            frame=X.loc[_supported_scenarios(X,b["scenarios"])!=""].head(256).reset_index(drop=True)
            prior=int(legacy[(legacy.dataset==dataset)&(legacy.operation=="complete_one_router_serialized_bytes")].iloc[0].bytes)
            loaded=serialized_bytes(b)
            for n in [1,len(frame)]:
                routed_predict(b,frame.head(n));routed_predict(b,frame.head(n),True)
                if n==1:route_patient(b,frame.head(1))
            warmed=serialized_bytes(b)
            diagnostic_rows.append({"dataset":dataset,"legacy_recorded_bytes":prior,"current_loaded_bytes":loaded,
                "current_warmed_bytes":warmed,"actual_file_bytes":c["bundle_path"].stat().st_size,
                "loaded_difference_bytes":loaded-prior,"warmed_difference_bytes":warmed-prior})
        pd.DataFrame(diagnostic_rows).to_csv(diagnostic_path,index=False)
    diagnostics=read_cost_csv(diagnostic_path)
    for dataset,directory,metadata in studies():
        for path in bundle_paths(directory):
            bundle=joblib.load(path)
            stream=io.BytesIO();joblib.dump(selected_payload(bundle),stream,compress=3)
            output=payload_dir/f"{dataset}_{path.name}";output.write_bytes(stream.getvalue())
            match=(storage.dataset==dataset)&(storage.scope=="selected_runtime_one_router_payload")&(
                storage["repeat"]==int(bundle.get("repeat",0)))&(storage.outer_fold==int(bundle.get("outer_fold",0)))
            if match.sum()!=1:raise ValueError("Payload storage key mismatch")
            storage.loc[match,"combined_bytes"]=output.stat().st_size
            storage.loc[match,"serialized_payload_source"]=str(output.relative_to(ROOT))
            storage.loc[match,"serialized_payload_sha256"]=sha(output)
            storage.loc[match,"method"]="saved joblib compress=3 pruned D payload; stat+SHA verified; shared fold-family once"
        match=(storage.dataset==dataset)&(storage.scope=="selected_runtime_all_routers_payload")
        singles=storage[(storage.dataset==dataset)&(storage.scope=="selected_runtime_one_router_payload")]
        storage.loc[match,"combined_bytes"]=singles.combined_bytes.sum()
        diagnostics.loc[diagnostics.dataset==dataset,"source"]=str(bundle_paths(directory)[0].relative_to(ROOT))
        diagnostics.loc[diagnostics.dataset==dataset,"source_sha256"]=sha(bundle_paths(directory)[0])
    for column in ["preprocessor_bytes","model_bytes","calibrator_bytes","combined_bytes","actual_file_bytes"]:
        storage[column.replace("_bytes","_MiB")]=storage[column]/2**20
    storage.to_csv(p,index=False)
    diagnostics["legacy_exact_byte_reproduction"]=diagnostics.legacy_recorded_bytes==diagnostics.current_warmed_bytes
    diagnostics["method"]="read-only serialization before/after untimed warm prediction; disk bytes+hash canonical; cause of legacy difference unestablished"
    diagnostics.to_csv(REPORT/"A4_STORAGE_VERIFICATION.csv",index=False)


def component_storage_verification():
    folder=A4/"exemplar_serializations"
    if folder.exists():raise FileExistsError("Preserve canonical example serializations")
    folder.mkdir()
    legacy=read_cost_csv(A4/"previous_handoff/analysis/journal_revision/06_COMPUTATIONAL_COST.csv")
    rows=[]
    for dataset,directory,metadata in studies():
        c=next(contexts(dataset,directory,metadata));b=c["bundle"]
        X=c["loaded"].X.iloc[c["evaluation"]["row_position"].to_numpy(int)]
        choices=_supported_scenarios(X,b["scenarios"]);panel=choices[choices!=""][0]
        family=b["selected_models"][panel];base=b["model_bundles"][family];cal=b["scenario_calibrators"][family][panel]
        triple={"model":base["model"],"preprocessor":base["preprocessor"],"calibrator":cal}
        for operation,obj in [("model_serialized_bytes",base["model"]),("preprocessor_serialized_bytes",base["preprocessor"]),
                              ("calibrator_serialized_bytes",cal),("model_preprocessor_calibrator_serialized_bytes",triple)]:
            stream=io.BytesIO();joblib.dump(obj,stream,compress=3)
            path=folder/f"{dataset}_{operation}.joblib";path.write_bytes(stream.getvalue())
            old=int(legacy[(legacy.dataset==dataset)&(legacy.operation==operation)].iloc[0].bytes)
            rows.append({"dataset":dataset,"panel":panel,"family":family,"operation":operation,
                "legacy_recorded_bytes":old,"current_saved_bytes":path.stat().st_size,
                "difference_bytes":path.stat().st_size-old,"exact_byte_reproduction":path.stat().st_size==old,
                "source":str(path.relative_to(ROOT)),"source_sha256":sha(path),
                "original_router_source":str(c["bundle_path"].relative_to(ROOT)),"original_router_sha256":sha(c["bundle_path"]),
                "method":"independent compressed joblib=3 saved file; stat+SHA; no fitting"})
    pd.DataFrame(rows).to_csv(REPORT/"A4_COMPONENT_STORAGE_VERIFICATION.csv",index=False)


AUTHORIZED_EXISTING = {
    "06_COMPUTATIONAL_COST.csv", "06_COMPUTATIONAL_COST.md", "WORK_STATUS.csv",
    "MENTOR_RESPONSE_EVIDENCE.md", "FINAL_MODEL_ANALYSIS_REPORT.md", "REPRODUCE.md",
    "ANALYSIS_SOURCE_MAP.csv", "ANALYSIS_SOURCE_MAP.md", "analysis_source_fingerprints.json",
    "FINAL_HANDOFF_CHECKSUMS.json", "QA_REPORT.md", "FINAL_VERIFICATION.json", "GIT_WORKING_TREE_STATUS.txt",
}


def verify():
    """Independent read-only checks, except writing a successor QA receipt."""
    from .audit import verify_protected
    from pandas.testing import assert_frame_equal
    import ast
    source_tree=ast.parse(Path(__file__).read_text())
    forbidden={"fit","fit_transform","tune_model","select_calibrator"}
    for node in ast.walk(source_tree):
        if isinstance(node,ast.Call):
            name=node.func.attr if isinstance(node.func,ast.Attribute) else node.func.id if isinstance(node.func,ast.Name) else ""
            if name in forbidden:raise ValueError("A4 implementation acquired a fitting/tuning call")
    protected=verify_protected()
    before=json.loads((A4/"pre_a4_manifest.json").read_text())
    changed=[]
    for absolute,digest in before["files"].items():
        p=Path(absolute)
        authorized=p.parent==REPORT and p.name in AUTHORIZED_EXISTING
        if not p.is_file() or sha(p)!=digest:
            if not authorized: raise ValueError(f"Unauthorized before-A4 change: {p}")
            changed.append(str(p.relative_to(ROOT)))
    old_manifest=json.loads((A4/"previous_handoff/FINAL_HANDOFF_CHECKSUMS.json").read_text())
    for relative,digest in old_manifest["files"].items():
        if sha(A4/"previous_handoff"/relative)!=digest:
            raise ValueError("Preserved sealed handoff changed")
        p=ROOT/relative
        if not (p.parent==REPORT and p.name in AUTHORIZED_EXISTING) and sha(p)!=digest:
            raise ValueError("Earlier non-A4 handoff source/report changed")
    costs=read_cost_csv(REPORT/"06_COMPUTATIONAL_COST.csv")
    old=read_cost_csv(A4/"previous_handoff/analysis/journal_revision/06_COMPUTATIONAL_COST.csv")
    retained=costs.iloc[:len(old)]
    for column in old:
        if column=="source":
            mask=old.source.notna()
            if not old.loc[mask,column].equals(retained.loc[mask,column]):raise ValueError("Existing source changed")
        elif pd.api.types.is_numeric_dtype(old[column]):
            if not np.allclose(old[column],retained[column],rtol=2e-15,atol=0,equal_nan=True):
                raise ValueError("Retained computational measurement changed: "+column)
        else:
            assert_frame_equal(old[[column]],retained[[column]],check_dtype=False)
    for _,row in retained[retained.evidence=="new_post_review_execution_timing"].iterrows():
        task=json.loads((ROOT/row.source).read_text())
        if not np.isclose(row.total_seconds,task[row.operation.removeprefix("new_panel_")],rtol=2e-14,atol=0):
            raise ValueError("Task timer mismatch")
    for _,row in retained[retained.operation=="new_panel_combined_artifact_size"].iterrows():
        if (ROOT/row.source).stat().st_size!=row.bytes:raise ValueError("Earlier reduced-artifact byte count mismatch")
    timing_count=0
    for filename, env_id in [(PRIVATE/"benchmark_raw_samples.json","L_prior_local"),(A4/"supplement_raw_samples.json","N_A4_supplement")]:
        for sample in json.loads(filename.read_text()):
            subset=costs[(costs.environment_id==env_id)&(costs.dataset==sample["dataset"])&
                (costs.system==sample["system"])&(costs.operation==sample["operation"])&(costs.batch_n==sample["batch_n"])]
            if len(subset)!=1:raise ValueError("Timing row is missing or duplicated")
            row=subset.iloc[0];vals=np.asarray(sample["raw_seconds"])
            actual=[np.median(vals),np.quantile(vals,.05),np.quantile(vals,.95),vals.min(),vals.max()]
            expected=[row.median_seconds,row.p05_seconds,row.p95_seconds,row.min_seconds,row.max_seconds]
            if len(vals)!=20 or row.repetitions!=20 or row.warmups!=3 or not np.allclose(actual,expected,rtol=2e-14,atol=1e-18):
                raise ValueError("Latency distribution does not reconcile to raw samples")
            timing_count+=1
    for _,row in costs.iterrows():
        p=ROOT/row.source
        if not p.exists():raise ValueError("Missing cost source: "+row.source)
        if p.is_file() and sha(p)!=row.source_sha256:raise ValueError("Cost source hash mismatch")
    storage=read_cost_csv(REPORT/"A4_STORAGE_DETAILS.csv")
    for _,row in storage[storage.source_sha256.notna()].iterrows():
        p=ROOT/row.source
        if sha(p)!=row.source_sha256:raise ValueError("Storage artifact changed")
        if pd.notna(row.actual_file_bytes) and p.stat().st_size!=row.actual_file_bytes:raise ValueError("Actual storage mismatch")
    for _,row in storage[storage.serialized_payload_source.notna()].iterrows():
        p=ROOT/row.serialized_payload_source
        if sha(p)!=row.serialized_payload_sha256 or p.stat().st_size!=row.combined_bytes:raise ValueError("Saved deployment payload changed")
    for dataset,group in storage.groupby("dataset"):
        single=group[group.scope=="selected_runtime_one_router_payload"]
        total=group[group.scope=="selected_runtime_all_routers_payload"].iloc[0]
        if single.combined_bytes.sum()!=total.combined_bytes or single.unique_models.sum()!=total.unique_models:
            raise ValueError("Selected router storage double-count/collection mismatch")
        configs=group[group.scope=="original_selected_panel_configuration"]
        unique=len(configs.drop_duplicates(["repeat","outer_fold","family"]))
        if unique!=total.unique_models:raise ValueError("Shared fold-family count mismatch")
        for scope,col in [("independently_retrained_reduced_collection_actual","actual_file_bytes"),
                          ("independently_retrained_reduced_collection_prediction_triples","combined_bytes")]:
            detail=group[group.scope=="independently_retrained_reduced_configuration"]
            target=group[group.scope==scope].iloc[0]
            if detail[col].sum()!=target.combined_bytes or len(detail)!=target.unique_models:raise ValueError("Reduced collection mismatch")
    inference=read_cost_csv(REPORT/"A4_INFERENCE_SUMMARY.csv")
    assert_frame_equal(inference,costs[costs.repetitions.notna()].reset_index(drop=True),check_dtype=False,rtol=2e-14,atol=1e-18)
    training=read_cost_csv(REPORT/"A4_TRAINING_SUMMARY.csv")
    for _,row in training.iterrows():
        group=costs[(costs.dataset==row.dataset)&(costs.operation==row.component)]
        vals=group.total_seconds
        actual=[len(group),vals.sum(),vals.median(),vals.quantile(.05),vals.quantile(.95),vals.min(),vals.max()]
        target=row[["tasks","total_seconds","median_seconds","p05_seconds","p95_seconds","min_seconds","max_seconds"]].to_numpy(float)
        if not np.allclose(actual,target,rtol=2e-14,atol=1e-18):raise ValueError("Training table mismatch")
    main=read_cost_csv(REPORT/"A4_MAIN_TEXT_TABLE.csv")
    for _,row in main.iterrows():
        train=training[training.dataset==row.dataset].set_index("component")
        vals=costs[(costs.dataset==row.dataset)&(costs.system=="D_framework_one_router")&(costs.operation=="end_to_end_prediction")].set_index("batch_n")
        expected=[train.loc["new_panel_final_model_fit_seconds","total_seconds"],train.loc["new_panel_calibration_seconds","total_seconds"],
            vals.loc[1,"median_seconds"]*1000,vals.loc[256,"median_seconds"]*1000]
        if not np.allclose(expected,row[["successor_final_fit_sum_s","successor_calibration_sum_s","D_single_median_ms","D_batch256_median_ms"]].to_numpy(float),rtol=2e-14):
            raise ValueError("Main table cost mismatch")
        for col,op in [("exemplar_model_MiB","model_serialized_bytes"),("exemplar_calibrator_MiB","calibrator_serialized_bytes"),
                       ("exemplar_prediction_triple_MiB","model_preprocessor_calibrator_serialized_bytes")]:
            value=costs[(costs.dataset==row.dataset)&(costs.operation=="a4_canonical_exemplar_"+op)].iloc[0].bytes/2**20
            if not np.isclose(value,row[col],rtol=2e-14,atol=0):raise ValueError("Main storage mismatch")
    comparison=read_cost_csv(REPORT/"A4_COMPARATOR_COSTS.csv")
    for _,row in comparison.iterrows():
        base=costs[(costs.dataset==row.dataset)&(costs.batch_n==row.batch_n)&(costs.operation=="end_to_end_prediction")].set_index("system")
        a,d=base.loc["A_fixed_imputation_one_router","median_ms"],base.loc["D_framework_one_router","median_ms"]
        if not np.allclose([a,d,d/a],row[["A_median_ms","D_median_ms","D_over_A_median_ratio"]].to_numpy(float),rtol=2e-14):raise ValueError("Comparator mismatch")
    history=read_cost_csv(REPORT/"A4_HISTORICAL_TIMING.csv")
    historical=read_cost_csv(REPORT/"A4_HISTORICAL_MODEL_COSTS.csv")
    checked_hist=0
    for dataset,directory,metadata in studies():
        h=history[history.dataset==dataset].iloc[0]
        if h.runner_interval_seconds!=elapsed_utc(metadata["run_started_at_utc"],metadata["run_completed_at_utc"]):raise ValueError("Historical interval mismatch")
        table=read_cost_csv(directory/("fold_metrics.csv" if dataset in {"pidd","sylhet"} else "best_parameters.csv"))
        table=table.drop_duplicates(["model","repeat","outer_fold"] if dataset in {"pidd","sylhet"} else ["model"])
        for family,group in table.groupby("model"):
            for col in ["tuning_seconds","fit_seconds"]:
                target=historical[(historical.dataset==dataset)&(historical.system==family)&(historical.operation=="historical_"+col)].iloc[0]
                if not np.allclose([group[col].sum(),group[col].median(),group[col].min(),group[col].max()],
                    target[["total_seconds","median_seconds","min_seconds","max_seconds"]].to_numpy(float),rtol=2e-14):raise ValueError("Historical timer mismatch")
                checked_hist+=1
        original_disk=retained[(retained.dataset==dataset)&(retained.operation=="actual_original_artifact_storage")].iloc[0].bytes
        disk=sum(p.stat().st_size for p in (directory/"models").glob("*.joblib"))+sum(p.stat().st_size for p in bundle_paths(directory))
        if original_disk!=disk:raise ValueError("Original archive storage mismatch")
        c=next(contexts(dataset,directory,metadata))
        evaluation=c["loaded"].X.iloc[c["evaluation"]["row_position"].to_numpy(int)]
        chosen=_supported_scenarios(evaluation,c["bundle"]["scenarios"])
        panel=chosen[chosen!=""][0]
        detail=storage[(storage.dataset==dataset)&(storage.scope=="original_selected_panel_configuration")&
            (storage["repeat"]==0)&(storage.outer_fold==0)&(storage.panel==panel)].iloc[0]
        for op,column in [("model_serialized_bytes","model_bytes"),("preprocessor_serialized_bytes","preprocessor_bytes"),
                          ("calibrator_serialized_bytes","calibrator_bytes"),("model_preprocessor_calibrator_serialized_bytes","combined_bytes")]:
            prior=retained[(retained.dataset==dataset)&(retained.operation==op)].iloc[0].bytes
            components=read_cost_csv(REPORT/"A4_COMPONENT_STORAGE_VERIFICATION.csv")
            component=components[(components.dataset==dataset)&(components.operation==op)].iloc[0]
            if prior!=component.legacy_recorded_bytes or sha(ROOT/component.source)!=component.source_sha256 or (ROOT/component.source).stat().st_size!=component.current_saved_bytes:
                raise ValueError("Component serialization file/legacy record mismatch")
            if component.current_saved_bytes-prior!=component.difference_bytes or sha(ROOT/component.original_router_source)!=component.original_router_sha256:
                raise ValueError("Component serialization discrepancy/source mismatch")
        prior=retained[(retained.dataset==dataset)&(retained.operation=="complete_one_router_serialized_bytes")].iloc[0].bytes
        diagnostic=read_cost_csv(REPORT/"A4_STORAGE_VERIFICATION.csv")
        diagnostic=diagnostic[diagnostic.dataset==dataset].iloc[0]
        if prior!=diagnostic.legacy_recorded_bytes or sha(ROOT/diagnostic.source)!=diagnostic.source_sha256 or (ROOT/diagnostic.source).stat().st_size!=diagnostic.actual_file_bytes:
            raise ValueError("Whole-router discrepancy ledger/source mismatch")
        if diagnostic.current_warmed_bytes-diagnostic.legacy_recorded_bytes!=diagnostic.warmed_difference_bytes or bool(diagnostic.legacy_exact_byte_reproduction)!=(diagnostic.current_warmed_bytes==diagnostic.legacy_recorded_bytes):
            raise ValueError("Whole-router serialization limitation not accurately disclosed")
    trial_table=read_cost_csv(REPORT/"A4_HISTORICAL_TRIAL_TIMING.csv")
    for _,row in trial_table.iterrows():
        p=ROOT/row.source;t=read_cost_csv(p)
        delta=(pd.to_datetime(t.datetime_complete)-pd.to_datetime(t.datetime_start)).dt.total_seconds()
        if len(t)!=row.trials or sha(p)!=row.source_sha256 or not np.isclose(delta.sum(),row.trial_duration_sum_seconds,rtol=2e-14):raise ValueError("Trial timestamps mismatch")
    summary=(REPORT/"A4_PUBLICATION_READY_SUMMARY.md").read_text()
    main_cols=["dataset","successor_final_fit_sum_s","successor_calibration_sum_s","D_single_median_ms","D_batch256_median_ms","exemplar_model_MiB","exemplar_calibrator_MiB","exemplar_prediction_triple_MiB"]
    for p in [REPORT/"06_COMPUTATIONAL_COST.md",REPORT/"A4_PUBLICATION_READY_SUMMARY.md"]:
        if publication_table(main[main_cols]) not in p.read_text():raise ValueError("Displayed main table differs from source CSV")
    if publication_table(training.drop(columns=["evidence","source"])) not in summary:raise ValueError("Displayed training table mismatch")
    if publication_table(comparison.drop(columns="source")) not in summary:raise ValueError("Displayed comparator table mismatch")
    latency_cols=["dataset","system","operation","batch_n","median_ms","p05_ms","p95_ms","min_ms","max_ms","environment_id"]
    if publication_table(inference[latency_cols]) not in summary:raise ValueError("Displayed latency table mismatch")
    if publication_table(historical.drop(columns="source")) not in summary:raise ValueError("Displayed historical model table mismatch")
    if markdown_table(history[["dataset","run_started_utc","run_completed_utc","runner_interval_seconds","classification"]]) not in summary:
        raise ValueError("Displayed historical interval table mismatch")
    deployments=storage[storage.scope.isin(["selected_runtime_one_router_payload","selected_runtime_all_routers_payload","actual_complete_router_collection","independently_retrained_reduced_collection_actual"])].copy()
    deployments["combined_MiB"]=deployments.combined_bytes/2**20
    display=deployments[(deployments.scope!="selected_runtime_one_router_payload")|((deployments["repeat"]==0)&(deployments.outer_fold==0))]
    if publication_table(display[["dataset","scope","repeat","outer_fold","unique_models","combined_MiB"]]) not in summary:
        raise ValueError("Displayed storage collection table mismatch")
    components=read_cost_csv(REPORT/"A4_COMPONENT_STORAGE_VERIFICATION.csv")
    if markdown_table(components[["dataset","operation","legacy_recorded_bytes","current_saved_bytes","difference_bytes"]]) not in summary:
        raise ValueError("Displayed component discrepancy table mismatch")
    diagnostic=read_cost_csv(REPORT/"A4_STORAGE_VERIFICATION.csv")
    if markdown_table(diagnostic[["dataset","legacy_recorded_bytes","current_loaded_bytes","current_warmed_bytes","actual_file_bytes","warmed_difference_bytes"]]) not in summary:
        raise ValueError("Displayed whole-router discrepancy table mismatch")
    mapping=read_cost_csv(REPORT/"ANALYSIS_SOURCE_MAP.csv")
    for output,group in mapping.groupby("output_file"):
        p=ROOT/output
        if len(group)!=len(read_cost_csv(p)) or set(group.output_sha256)!={sha(p)}:raise ValueError("Source-map table mismatch")
    for p in REPORT.glob("*.csv"):
        if {"row_id","group_id"}&set(read_cost_csv(p,nrows=0).columns):raise ValueError("Private identifiers exported")
    status=read_cost_csv(REPORT/"WORK_STATUS.csv").set_index("work")
    if status.loc["Mentor requirement A4 reporting completeness","status"]!="COMPLETE" or status.loc["Exact end-to-end historical training replay","status"]!="BLOCKED":raise ValueError("Status boundary lost")
    result={"passed":True,"A4_reporting":"COMPLETE","historical_components":"PARTIAL","historical_replay":"BLOCKED",
        "original_protected_files":protected["protected_files"],"before_A4_files_checked":len(before["files"]),
        "preserved_previous_seal_files":len(old_manifest["files"]),"retained_cost_rows":len(old),
        "latency_distributions_checked":timing_count,"new_latency_workloads":len(json.loads((A4/"supplement_raw_samples.json").read_text())),"storage_configurations_and_collections":len(storage),
        "historical_timer_aggregates_checked":checked_hist,"historical_searches_checked":len(trial_table),
        "historical_trials_checked":int(trial_table.trials.sum()),"source_map_rows":len(mapping),
        "authorized_existing_changes":changed,"no_new_model_or_calibrator_fitting":True,
        "old_zip_and_manuscript_unchanged":True,"scientific_artifacts_and_configurations_unchanged":True,
        "all_reported_cost_sources_exist":True,"tables_reconcile":True,
        "legacy_in_memory_whole_router_sizes_exactly_reproduced":bool(read_cost_csv(REPORT/"A4_STORAGE_VERIFICATION.csv").legacy_exact_byte_reproduction.all()),
        "whole_router_serialization_difference_disclosed":"A4_STORAGE_VERIFICATION.csv and A4_COMPONENT_STORAGE_VERIFICATION.csv; original file sizes/hash unchanged",
        "legacy_component_counts_not_exactly_reproduced":int((components.difference_bytes!=0).sum()),
        "saved_exemplar_components_verified":len(components),
        "saved_selected_runtime_payloads_verified":int(storage.serialized_payload_source.notna().sum()),
        "csv_numeric_round_trip_tolerance":"rtol 2e-15 for retained measurements; no scientific verification tolerance changed"}
    write_json(REPORT/"A4_VERIFICATION.json",result)
    print(json.dumps(result,indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["collect", "resume", "storage", "components", "report", "verify"])
    args=parser.parse_args()
    {"collect":collect,"resume":lambda:collect(True),"storage":storage_verification,"components":component_storage_verification,"report":reports,"verify":lambda:verify()}[args.phase]()
