"""Controlled local CPU benchmarks, separate from scientific outcome analysis."""
from __future__ import annotations

import importlib.metadata
import io
import json
import os
import platform
import subprocess
import sys
import time

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_info

from diabetes_pipeline.routing.inference import route_patient
from diabetes_pipeline.routing.policy_evaluator import _supported_scenarios, _predict_batch

from .common import ROOT, REPORT, PRIVATE, studies, bundle_paths, save_table, markdown_table, write_json
from .experiments import contexts


def measured(call, *, warmups=3, repetitions=20):
    for _ in range(warmups):
        call()
    values = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        call()
        values.append((time.perf_counter_ns() - start) / 1e9)
    return {"median_seconds": float(np.median(values)), "p05_seconds": float(np.quantile(values, .05)),
            "p95_seconds": float(np.quantile(values, .95)), "min_seconds": min(values), "max_seconds": max(values),
            "repetitions": repetitions, "warmups": warmups, "raw_seconds": values}


def serialized_bytes(value):
    stream = io.BytesIO()
    joblib.dump(value, stream, compress=3)
    return stream.tell()


def environment():
    def sysctl(key):
        try:
            return subprocess.check_output(["sysctl", "-n", key], text=True, stderr=subprocess.DEVNULL).strip()
        except (OSError, subprocess.CalledProcessError):
            return "unavailable"
    hardware = {}
    try:
        payload = json.loads(subprocess.check_output(["/usr/sbin/system_profiler", "SPHardwareDataType", "-json"], text=True))
        entry = payload["SPHardwareDataType"][0]
        # Explicit allowlist: never retain serial numbers or hardware UUIDs.
        hardware = {key: entry[key] for key in ["machine_model", "machine_name", "chip_type", "physical_memory", "number_processors"] if key in entry}
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError, IndexError):
        pass
    distributions = ["numpy", "pandas", "scipy", "scikit-learn", "xgboost", "lightgbm", "catboost", "optuna", "joblib", "threadpoolctl"]
    model, cpu, ram = sysctl("hw.model"), sysctl("machdep.cpu.brand_string"), sysctl("hw.memsize")
    if model == "unavailable":
        model = hardware.get("machine_model", "unavailable")
    if cpu == "unavailable":
        cpu = hardware.get("chip_type", "unavailable")
    if ram == "unavailable" and hardware.get("physical_memory", "").endswith(" GB"):
        ram = int(float(hardware["physical_memory"].split()[0]) * 1024 ** 3)
    return {"hardware_model": model, "cpu": cpu, "hardware_details": hardware,
            "logical_cpus": os.cpu_count(), "ram_bytes": ram,
            "gpu_used": False, "gpu": "not used; CPU-only estimators", "operating_system": platform.platform(),
            "python": sys.version, "architecture": platform.machine(),
            "package_versions": {d: importlib.metadata.version(d) for d in distributions},
            "thread_environment": {key: os.environ.get(key, "unset") for key in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "MKL_NUM_THREADS"]},
            "threadpools": threadpool_info(), "estimator_n_jobs": 4,
            "timing_method": "perf_counter_ns elapsed wall-clock; loaded artifacts; 3 warmups; 20 serial repetitions",
            "disk_load_included": False, "shap_and_report_rendering_included": False}


def run_benchmark(selected="all"):
    rows, samples = [], []
    env = environment()
    write_json(REPORT / "BENCHMARK_ENVIRONMENT.json", env)
    for dataset, directory, metadata in studies():
        if selected != "all" and dataset != selected:
            continue
        print(f"Computational benchmark: {dataset}", flush=True)
        c = next(contexts(dataset, directory, metadata))
        bundle, loaded, role = c["bundle"], c["loaded"], c["evaluation"]
        X = loaded.X.iloc[role["row_position"].to_numpy(int)].reset_index(drop=True)
        # Sample first supported evaluation records in frozen order, outcome-blind.
        chosen = _supported_scenarios(X, bundle["scenarios"])
        eligible = X.loc[chosen != ""].head(256).reset_index(drop=True)
        all_bundles = [joblib.load(path) for path in bundle_paths(directory)]
        def record(label, operation, n, call):
            timing = measured(call)
            samples.append({"dataset": dataset, "system": label, "operation": operation, "batch_n": n, **timing})
            rows.append({"dataset": dataset, "evidence": "new_local_controlled_measurement", "system": label,
                         "operation": operation, "batch_n": n, **{k:v for k,v in timing.items() if k != "raw_seconds"}})
        for n in [1, min(256, len(eligible))]:
            frame = eligible.head(n).copy()
            record("framework_one_router", "routing_eligibility_only", n,
                   lambda f=frame: _supported_scenarios(f, bundle["scenarios"]))
            assignments = _supported_scenarios(frame, bundle["scenarios"])
            panel = assignments[0]
            family = bundle["selected_models"][panel]
            model = bundle["model_bundles"][family]
            masked = frame.reindex(columns=bundle["configured_features"]).copy()
            for feature in set(bundle["configured_features"]) - set(bundle["scenarios"][panel]):
                masked[feature] = np.nan
            transformed = model["preprocessor"].transform(masked)
            record("framework_first_record_panel", "preprocessing_transform", n,
                   lambda m=masked: model["preprocessor"].transform(m))
            record("framework_first_record_panel", "base_model_predict_only", n,
                   lambda t=transformed: model["model"].predict_proba(t))
            def batch_predict(f, fixed=False):
                selected_panels = _supported_scenarios(f, bundle["scenarios"])
                result = np.full(len(f), np.nan)
                for scenario in sorted(set(selected_panels) - {""}):
                    mask = selected_panels == scenario
                    selected_family = bundle["robust_single_model"] if fixed else bundle["selected_models"][scenario]
                    if fixed:
                        base = bundle["model_bundles"][selected_family]
                        ordered = f.loc[mask].reindex(columns=bundle["configured_features"]).copy()
                        for feature in set(bundle["configured_features"]) - set(bundle["scenarios"][scenario]):
                            ordered[feature] = np.nan
                        raw = base["model"].predict_proba(base["preprocessor"].transform(ordered))
                        calibrated = base["calibrator"].predict(raw)
                    else:
                        raw, calibrated, _ = _predict_batch(bundle, f.loc[mask], scenario, selected_family)
                    result[mask] = calibrated
                return result
            record("D_framework_one_router", "end_to_end_prediction", n, lambda f=frame: batch_predict(f))
            record("A_fixed_imputation_one_router", "end_to_end_prediction", n, lambda f=frame: batch_predict(f, True))
            if n == 1:
                record("D_route_patient", "single_record_public_router_API", n,
                       lambda f=frame: route_patient(bundle, f))
                record(f"D_{len(all_bundles)}_router_research_ensemble", "probability_only_all_available_router_ensemble", n,
                       lambda f=frame: np.mean([route_patient(b, f)["probability_calibrated"] for b in all_bundles]))
        # Serialized component sizes are measured independently; compression is not additive.
        panel = chosen[chosen != ""][0]
        family = bundle["selected_models"][panel]
        model = bundle["model_bundles"][family]
        calibrator = bundle["scenario_calibrators"][family][panel]
        for operation, obj in [("model_serialized_bytes", model["model"]),
                               ("preprocessor_serialized_bytes", model["preprocessor"]),
                               ("calibrator_serialized_bytes", calibrator),
                               ("model_preprocessor_calibrator_serialized_bytes", {"model": model["model"], "preprocessor": model["preprocessor"], "calibrator": calibrator}),
                               ("complete_one_router_serialized_bytes", bundle)]:
            rows.append({"dataset": dataset, "system": "original_first_router_runtime_panel", "operation": operation,
                         "evidence": "new_local_controlled_measurement", "bytes": serialized_bytes(obj), "compression": "joblib compress=3"})
        rows.append({"dataset": dataset, "system": "all_original_model_and_router_files", "operation": "actual_original_artifact_storage",
                     "evidence": "existing_file_sizes", "bytes": sum(p.stat().st_size for p in (directory / "models").glob("*.joblib")) +
                     sum(p.stat().st_size for p in bundle_paths(directory)), "compression": "original serialization; router bundles duplicate base objects"})
        # Historical tuning and final-fitting costs really exist; no retroactive timing inference.
        if dataset in {"pidd", "sylhet"}:
            historical = pd.read_csv(directory / "fold_metrics.csv")
            historical = historical.drop_duplicates(["model", "repeat", "outer_fold"])
        else:
            historical = pd.read_csv(directory / "best_parameters.csv")
        for family, group in historical.groupby("model", sort=True):
            for column in ["tuning_seconds", "fit_seconds"]:
                rows.append({"dataset": dataset, "system": family, "operation": "historical_" + column,
                             "evidence": "original_recorded_timing", "total_seconds": group[column].sum(),
                             "median_seconds": group[column].median(), "min_seconds": group[column].min(), "max_seconds": group[column].max(),
                             "task_count": len(group), "source": str((directory / ("fold_metrics.csv" if dataset in {"pidd", "sylhet"} else "best_parameters.csv")).relative_to(ROOT))})
        for path in sorted((PRIVATE / "panel_tasks" / dataset).glob("repeat_*_fold_*/*/task.json")):
            task = json.loads(path.read_text())
            if task["panel"] == "full":
                continue
            for column in ["base_oof_seconds", "calibration_seconds", "final_model_fit_seconds", "final_preprocessing_seconds", "tuning_seconds"]:
                rows.append({"dataset": dataset, "system": task["family"], "panel": task["panel"], "repeat": task["repeat"], "outer_fold": task["fold"],
                             "operation": "new_panel_" + column, "evidence": "new_post_review_execution_timing", "total_seconds": task[column],
                             "source": str(path.relative_to(ROOT))})
            new_bundle = path.parent / "bundle.joblib"
            rows.append({"dataset": dataset, "system": task["family"], "panel": task["panel"], "operation": "new_panel_combined_artifact_size",
                         "evidence": "existing_file_sizes", "bytes": new_bundle.stat().st_size})
        representative = next((PRIVATE / "panel_tasks" / dataset).glob("repeat_*_fold_*/*/bundle.joblib"), None)
        if representative is not None:
            trained = joblib.load(representative)
            for n in [1, min(256, len(eligible))]:
                panel_frame = eligible.head(n).loc[:, trained["features"]]
                record("retrained_" + representative.parent.name + "_" + trained["family"], "end_to_end_reduced_panel_prediction", n,
                       lambda f=panel_frame: trained["calibrator"].predict(trained["model"].predict_proba(trained["preprocessor"].transform(f))))
    write_json(PRIVATE / "benchmark_raw_samples.json", samples)
    frame = pd.DataFrame(rows)
    local = frame[(frame["operation"] == "end_to_end_prediction")]
    save_table("06_COMPUTATIONAL_COST", frame,
        "# Computational cost\n\nCOMPLETE for controlled CPU inference/storage and recorded training components. "
        "Historical tuning/final-fit columns are reused as historical measurements; original calibration and OOF times were not separately logged. "
        "New panel OOF, calibration selection/final mapping, final fitting and preprocessing times are separately measured. No new tuning occurred.\n\n"
        "Environment: `BENCHMARK_ENVIRONMENT.json` contains actual hardware model/CPU/RAM/OS/Python/packages/thread settings. "
        "All inference uses loaded artifacts, 3 warmups, 20 serial perf_counter_ns repetitions, one record and up to 256 supported records "
        "in frozen evaluation order, selected without outcomes. CSV gives median, 5th/95th percentiles and ranges; raw samples stay private. "
        "No disk loading, SHAP computation or patient-report rendering is included. Component `framework_first_record_panel` applies the first record's "
        "panel to the whole batch for a standardized model-only measurement; end-to-end batch timings route every record independently. "
        "The repeated-cohort all-router ensemble timing covers probability-only inference across 25 routers, which differs from five OOF predictions used per evaluation participant.\n\n"
        + markdown_table(local[["dataset", "system", "batch_n", "median_seconds", "p05_seconds", "p95_seconds"]]) +
        "\n\nModel, preprocessing, calibrator, combined model artifact, complete router and actual original storage are reported separately. "
        "Compression=3 component sizes are controlled new serializations; compression is not additive. Actual disk sums include model duplication inside router bundles. "
        "Original historical fit/tuning times are not replaced by these new local timings. The CSV's long-form operation/evidence fields distinguish all cost types. "
        "No original peak process RAM or GPU training measurement is available; hardware RAM is not a measured peak workload requirement. "
        "These local timings are workload- and hardware-specific; concurrent execution during the run is recorded in the handoff.")
    print("Computational benchmark complete", flush=True)
