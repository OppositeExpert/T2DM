"""Controlled matched-panel retraining and frozen-family calibration ablations."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from diabetes_pipeline.calibration.calibrators import select_calibrator
from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.evaluation.panel_training_ablations import _panel_dataset_config
from diabetes_pipeline.models.registry import MODEL_NAMES, build_estimator
from diabetes_pipeline.preprocessing.builders import build_preprocessor
from diabetes_pipeline.routing.holdout_evaluator import _development_splits
from diabetes_pipeline.routing.policy_evaluator import _predict_batch, _validate_router_bundle
from diabetes_pipeline.settings import get_dataset_config
from diabetes_pipeline.training.tuning import inner_splits, positive_class_weight

from .common import (ROOT, REPORT, PRIVATE, EXPECTED, METRICS, studies, panels, bundle_paths,
                     read_csv, aggregate, align, metrics, sha, git_commit, write_json, save_table, markdown_table)
from .statistics import paired_bootstrap, holm


def contexts(dataset, directory, metadata):
    loaded = load_dataset(dataset)
    manifest = read_csv(Path(metadata["split_manifest"]))
    cfg = get_dataset_config(dataset)
    unique = manifest.drop_duplicates("row_position").sort_values("row_position")
    if not np.array_equal(unique["row_id"].to_numpy(str), loaded.row_ids.to_numpy(str)):
        raise ValueError("Raw data/split stable record identity mismatch")
    if not np.array_equal(unique["target"].to_numpy(int), loaded.y.to_numpy(int)):
        raise ValueError("Raw data/split outcome identity mismatch")
    expected_groups = loaded.groups.to_numpy(str) if loaded.groups is not None else np.full(len(loaded.X), "")
    if not np.array_equal(unique["group_id"].to_numpy(str), expected_groups):
        raise ValueError("Raw data/split group identity mismatch")
    holdout = dataset in {"brfss", "hospital130"}
    for path in bundle_paths(directory):
        bundle = joblib.load(path)
        _validate_router_bundle(bundle, metadata, cfg)
        repeat, fold = int(bundle.get("repeat", 0)), int(bundle.get("outer_fold", 0))
        if holdout:
            train = manifest[manifest["role"] == "development"].sort_values("row_position").reset_index(drop=True)
            evaluation = manifest[manifest["role"] == "test"].sort_values("row_position").reset_index(drop=True)
            splits = _development_splits(train)
        else:
            current = manifest[(manifest["repeat"] == repeat) & (manifest["outer_fold"] == fold)]
            train = current[current["role"] == "train"].sort_values("row_position").reset_index(drop=True)
            evaluation = current[current["role"] == "validation"].sort_values("row_position").reset_index(drop=True)
            splits = None
        if set(train["row_id"]) & set(evaluation["row_id"]):
            raise ValueError("Training/evaluation records overlap")
        grouped = loaded.groups is not None
        groups = train["group_id"].to_numpy(str) if grouped else None
        if grouped and set(groups) & set(evaluation["group_id"]):
            raise ValueError("Training/evaluation groups overlap")
        yield {"dataset": dataset, "directory": directory, "metadata": metadata, "cfg": cfg,
               "loaded": loaded, "manifest": manifest, "bundle": bundle, "bundle_path": path,
               "train": train, "evaluation": evaluation, "groups": groups, "predefined_splits": splits,
               "repeat": repeat, "fold": fold, "holdout": holdout}


def task_path(context, panel):
    return PRIVATE / "panel_tasks" / context["dataset"] / f"repeat_{context['repeat']}_fold_{context['fold']}" / panel


def fit_task(context, panel):
    d, b = context["dataset"], context["bundle"]
    family = b["selected_models"][panel]
    base = b["model_bundles"][family]
    features = list(b["scenarios"][panel])
    destination = task_path(context, panel)
    signature_data = {"dataset": d, "repeat": context["repeat"], "fold": context["fold"],
                      "panel": panel, "features": features, "family": family, "params": base["best_params"],
                      "router_sha256": sha(context["bundle_path"]), "plan_sha256": sha(REPORT / "experiment_plan.json"),
                      "source_sha256": sha(Path(__file__)), "split_sha256": context["metadata"]["split_manifest_sha256"]}
    signature = hashlib.sha256(json.dumps(signature_data, sort_keys=True).encode()).hexdigest()
    record_file = destination / "task.json"
    if record_file.exists():
        record = json.loads(record_file.read_text())
        if record["signature"] != signature:
            raise ValueError(f"Checkpoint signature mismatch; preserve and use a new successor output path: {destination}")
        for filename, digest in record["output_hashes"].items():
            if sha(destination / filename) != digest:
                raise ValueError("Checkpoint content fingerprint mismatch")
        return record
    train, evaluation, loaded = context["train"], context["evaluation"], context["loaded"]
    X = loaded.X.iloc[train["row_position"].to_numpy(int)].reset_index(drop=True)
    y = train["target"].to_numpy(int)
    X_eval = loaded.X.iloc[evaluation["row_position"].to_numpy(int)].reset_index(drop=True)
    raw_original, p_original, original_calibration = _predict_batch(b, X_eval, panel, family)
    base_seed = 42 + context["repeat"] * 1000 + context["fold"]
    router_index = panels()[d]["router_models"].index(family)
    oof_seed = 42 + 100000 + router_index * 10000 if context["holdout"] else base_seed + 40000
    calibration_seed = 42 + 200000 + router_index * 10000 if context["holdout"] else base_seed + 50000
    final_seed = 42 + MODEL_NAMES.index(family) * 100000 + 30000 if context["holdout"] else base_seed + 20000
    calibration_seconds = oof_seconds = fit_seconds = preprocessing_seconds = 0.
    fit_records = []
    if panel == "full":
        raw_new, p_new = raw_original.copy(), p_original.copy()
        method = original_calibration
        strategy = "identical_full_schema_artifact_reused"
        selection_scores = []
        serialized = None
    else:
        cfg = _panel_dataset_config(context["cfg"], features)
        X_panel = X.loc[:, features].copy()
        eval_panel = X_eval.loc[:, features].copy()
        resolved = context["predefined_splits"]
        if resolved is None:
            resolved = list(inner_splits(y, n_splits=5, seed=oof_seed, groups=context["groups"]))
        oof = np.full(len(y), np.nan)
        coverage = np.zeros(len(y), int)
        start_oof = time.perf_counter()
        for inner_fold, (training, validation) in enumerate(resolved):
            if set(training) & set(validation):
                raise ValueError("Inner training/validation overlap")
            if context["groups"] is not None and set(context["groups"][training]) & set(context["groups"][validation]):
                raise ValueError("Inner group overlap")
            start = time.perf_counter()
            preprocessor = build_preprocessor(cfg, family)
            Xt = preprocessor.fit_transform(X_panel.iloc[training])
            Xv = preprocessor.transform(X_panel.iloc[validation])
            prep_elapsed = time.perf_counter() - start
            estimator = build_estimator(family, base["best_params"], seed=oof_seed + 30000 + inner_fold,
                                        n_jobs=4, positive_class_weight=positive_class_weight(y[training]))
            start = time.perf_counter()
            estimator.fit(Xt, y[training])
            elapsed = time.perf_counter() - start
            oof[validation] = estimator.predict_proba(Xv)
            coverage[validation] += 1
            fit_records.append({"inner_fold": inner_fold, "preprocessing_seconds": prep_elapsed,
                                "model_fit_seconds": elapsed, "training_n": len(training), "validation_n": len(validation),
                                "training_ids_sha256": hashlib.sha256("\n".join(train.iloc[training]["row_id"]).encode()).hexdigest(),
                                "validation_ids_sha256": hashlib.sha256("\n".join(train.iloc[validation]["row_id"]).encode()).hexdigest()})
        oof_seconds = time.perf_counter() - start_oof
        if not np.isfinite(oof).all() or np.any(coverage != 1):
            raise ValueError("Invalid training-only OOF construction")
        start = time.perf_counter()
        selection = select_calibrator(["identity", "sigmoid", "isotonic"], oof, y,
                                      n_splits=5, seed=calibration_seed, groups=context["groups"],
                                      minimum_samples_by_method={"isotonic": 1000})
        calibration_seconds = time.perf_counter() - start
        start = time.perf_counter()
        preprocessor = build_preprocessor(cfg, family)
        transformed = preprocessor.fit_transform(X_panel)
        preprocessing_seconds = time.perf_counter() - start
        estimator = build_estimator(family, base["best_params"], seed=final_seed, n_jobs=4,
                                    positive_class_weight=positive_class_weight(y))
        start = time.perf_counter()
        estimator.fit(transformed, y)
        fit_seconds = time.perf_counter() - start
        raw_new = estimator.predict_proba(preprocessor.transform(eval_panel))
        p_new = selection.calibrator.predict(raw_new)
        method, selection_scores = selection.method, selection.scores
        strategy = "independently_fitted_reduced_schema_frozen_hyperparameters"
        serialized = {"preprocessor": preprocessor, "model": estimator, "calibrator": selection.calibrator,
                      "features": features, "family": family, "parameters": base["best_params"],
                      "signature": signature, "evidence_tier": "post_review_internal_validation"}
    output = evaluation[["row_id", "group_id", "target"]].copy()
    output["dataset"] = d
    output["repeat"] = context["repeat"]
    output["outer_fold"] = context["fold"]
    output["scenario"] = panel
    output["model"] = family
    output["probability_original"] = p_original
    output["probability_original_raw"] = raw_original
    output["probability_calibrated"] = p_new
    output["probability_raw"] = raw_new
    output["calibration_method"] = method
    destination.mkdir(parents=True, exist_ok=True)
    prediction_file = destination / "predictions.csv.gz"
    output.to_csv(prediction_file, index=False, compression={"method": "gzip", "mtime": 0})
    hashes = {prediction_file.name: sha(prediction_file)}
    if serialized is not None:
        model_path = destination / "bundle.joblib"
        joblib.dump(serialized, model_path, compress=3)
        hashes[model_path.name] = sha(model_path)
    record = {**signature_data, "signature": signature, "git_commit": git_commit(), "strategy": strategy,
              "original_calibration": original_calibration, "new_calibration": method,
              "calibration_selection_scores": selection_scores, "training_n": len(train), "evaluation_n": len(evaluation),
              "new_optuna_trials": 0, "tuning_seconds": 0., "oof_seed": oof_seed, "calibration_seed": calibration_seed,
              "final_seed": final_seed, "model_threads": 4, "inner_fit_records": fit_records,
              "base_oof_seconds": oof_seconds, "calibration_seconds": calibration_seconds,
              "final_model_fit_seconds": fit_seconds, "final_preprocessing_seconds": preprocessing_seconds,
              "group_separation_verified": True, "training_evaluation_disjoint": True,
              "calibration_evaluation_labels_accessed": False, "output_hashes": hashes}
    write_json(record_file, record)
    print(f"Panel task {d} repeat={context['repeat']} fold={context['fold']} {panel} {family}: "
          f"OOF={oof_seconds:.2f}s fit={fit_seconds:.2f}s calibration={calibration_seconds:.2f}s", flush=True)
    return record


def run_pilot(selected="all"):
    if not (REPORT / "PHASE_0_FEASIBILITY_AUDIT.md").exists():
        raise PermissionError("Complete Phase 0 before any fitting")
    pilots = {"pidd": "no_insulin_or_skinfold", "brfss": "routine_survey", "hospital130": "encounter_utilization"}
    rows = []
    for dataset, directory, metadata in studies():
        if dataset not in pilots or (selected != "all" and dataset != selected):
            continue
        context = next(contexts(dataset, directory, metadata))
        record = fit_task(context, pilots[dataset])
        rows.append({"dataset": dataset, "panel": pilots[dataset], "family": record["family"],
                     "training_n": record["training_n"], "oof_seconds": record["base_oof_seconds"],
                     "fit_seconds": record["final_model_fit_seconds"], "calibration_seconds": record["calibration_seconds"]})
    result = pd.DataFrame(rows)
    result.to_csv(REPORT / "pilot_timing.csv", index=False)
    total = result[["oof_seconds", "fit_seconds", "calibration_seconds"]].sum(axis=1)
    # Small-cohort timing covers 225 non-full tasks; each large pilot bounds an initial planning estimate.
    by_dataset = dict(zip(result["dataset"], total))
    estimate = by_dataset.get("pidd", 10) * 225 + by_dataset.get("brfss", 150) * 5 + by_dataset.get("hospital130", 300) * 4
    write_json(REPORT / "compute_projection.json", {"pilot_tasks": rows, "remaining_base_fit_upper_count": 1404,
               "planning_seconds": estimate, "planning_range_seconds": [estimate / 2, estimate * 3],
               "method": "Small-cohort matched task x225 plus BRFSS x5 and Hospital130 x4; planning estimate only, family/panel runtimes vary",
               "new_tuning_trials": 0})
    print(f"Pilot complete; planning estimate {estimate/60:.1f} min, broad range {estimate/120:.1f}-{estimate/20:.1f} min", flush=True)


def run_train(selected="all"):
    if not (REPORT / "PHASE_0_FEASIBILITY_AUDIT.md").exists() or not (REPORT / "compute_projection.json").exists():
        raise PermissionError("Audit and pilot cost estimate required before full fitting")
    for dataset, directory, metadata in studies():
        if selected != "all" and selected != dataset:
            continue
        for context in contexts(dataset, directory, metadata):
            for panel in context["bundle"]["scenarios"]:
                fit_task(context, panel)
    print("Requested matched-panel training tasks complete", flush=True)


def run_ablation(selected="all"):
    summary, effects = [], []
    for dataset, directory, metadata in studies():
        if selected != "all" and selected != dataset:
            continue
        print(f"Calibration/switching ablation: {dataset}", flush=True)
        original = read_csv(directory / "runtime_policy_evaluation/policy_decisions.csv")
        accepted = original[original["status"] == "predicted"].copy()
        new_frames = []
        for path in bundle_paths(directory):
            bundle = joblib.load(path)
            repeat, fold = int(bundle.get("repeat", 0)), int(bundle.get("outer_fold", 0))
            fold_frame = accepted[(accepted["repeat"] == repeat) & (accepted["outer_fold"] == fold)]
            for system, original_system in [("A", "robust_single_model"), ("B", "robust_single_model"),
                                             ("C", "availability_router"), ("D", "availability_router")]:
                current = fold_frame[fold_frame["system"] == original_system].copy()
                for family, group in current.groupby("model", sort=False):
                    base = bundle["model_bundles"][family]
                    if system in {"A", "C"}:
                        probability = base["calibrator"].predict(group["probability_raw"].to_numpy(float))
                        current.loc[group.index, "probability_calibrated"] = probability
                        current.loc[group.index, "calibration_method"] = base["calibration_method"]
                    else:
                        for panel, panel_group in group.groupby("scenario", sort=False):
                            reconstructed = bundle["scenario_calibrators"][family][panel].predict(panel_group["probability_raw"].to_numpy(float))
                            if not np.allclose(reconstructed, panel_group["probability_calibrated"].to_numpy(float), rtol=0, atol=1e-12):
                                raise ValueError("Scenario calibration failed to reproduce saved B/D")
                current["system"] = system
                new_frames.append(current)
        predictions = pd.concat(new_frames, ignore_index=True)
        output = PRIVATE / "ablations" / dataset
        output.mkdir(parents=True, exist_ok=True)
        predictions.to_csv(output / "per_repeat_predictions.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
        aggregated = aggregate(predictions, ["system"], 5 if dataset in {"pidd", "sylhet"} else 1)
        aggregated.to_csv(output / "participant_predictions.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
        frames = {name: aggregated[aggregated["system"] == name] for name in ["A", "B", "C", "D"]}
        point, contrast = paired_bootstrap(frames, [("B", "A"), ("D", "C"), ("C", "A"), ("D", "B"), ("D", "A")],
                                          seed=42 + 2100000, name=f"ablation_{dataset}")
        contrast["dataset"] = dataset
        contrast["endpoint"] = metadata["endpoint"]
        contrast["comparison_family"] = f"{dataset}:five_declared_ablation_contrasts_per_metric"
        effects.append(contrast)
        for system, frame in frames.items():
            row = {"dataset": dataset, "endpoint": metadata["endpoint"], "system": system,
                   "family_policy": "fixed original robust family" if system in {"A", "B"} else "original development panel-selected family",
                   "calibration_policy": "original full-schema mapping" if system in {"A", "C"} else "panel-specific mapping",
                   "evaluation_n": len(frame), "population_n": EXPECTED[dataset][0], "coverage": len(frame) / EXPECTED[dataset][0], **metrics(frame)}
            for m in METRICS:
                q = point[(point["system"] == system) & (point["metric"] == m)].iloc[0]
                row[f"{m}_ci_lower"], row[f"{m}_ci_upper"] = q.ci_lower, q.ci_upper
            summary.append(row)
    effects = holm(pd.concat(effects, ignore_index=True), ["dataset", "metric"])
    effects.to_csv(REPORT / "05_ABLATION_PAIRED_CONTRASTS.csv", index=False)
    table = pd.DataFrame(summary)
    save_table("05_CALIBRATION_SWITCHING_ABLATION", table,
        "# Calibration and model-family switching ablations\n\nCOMPLETE for the declared conditional 2x2 design. No component was newly fitted. "
        "All systems share the same availability eligibility, panel order, evaluation identities and training-fitted imputation. "
        "A/B hold the original robust family fixed; C/D hold the original scenario-selected family fixed. A/C apply each base bundle's original full-schema "
        "calibrator to the identical masked raw scores used in B/D. B/D use the original panel-specific mapping, validated to 1e-12 against saved probabilities. "
        "Thus historical robust comparator equals B; original framework equals D. A is the requested fixed-imputation comparator. "
        "Fixed family means fixed within an outer training partition, not one family across all repeated folds. "
        "The original development selection used panel-calibrated scores. Family choices are frozen across calibration arms to isolate mapping effects; "
        "this does not estimate a separately optimized no-panel-calibration selector.\n\n"
        + markdown_table(table[["dataset", "system", "evaluation_n", "auroc", "average_precision", "brier_score", "log_loss"]]) +
        "\n\n`05_ABLATION_PAIRED_CONTRASTS.csv` reports B-A and D-C calibration effects, C-A and D-B family-switching effects, and D-A complete-framework "
        "versus simple fixed imputation. Effects/intervals are literal A-minus-B; positive improvement reverses loss metrics. "
        "2000 paired percentile bootstrap resamples preserve complete profile/patient clusters; PIDD/BRFSS use outcome-stratified individuals. "
        "Holm correction covers the five declared contrasts within each cohort and metric. Actual distributions are retained privately. "
        "Intervals are conditional on the fitted probabilities and reused internal-validation populations; negative and inconclusive results are retained.")
    print("Ablation reports complete", flush=True)


def run_panels(selected="all"):
    summaries, all_contrasts = [], []
    for dataset, directory, metadata in studies():
        if selected != "all" and selected != dataset:
            continue
        files = sorted((PRIVATE / "panel_tasks" / dataset).glob("repeat_*_fold_*/*/predictions.csv.gz"))
        wanted = (25 if dataset in {"pidd", "sylhet"} else 1) * len(panels()[dataset]["scenarios"])
        if len(files) != wanted:
            raise ValueError(f"Incomplete {dataset} panel tasks: {len(files)}/{wanted}")
        source = pd.concat([read_csv(f) for f in files], ignore_index=True)
        # Validate original arm against frozen all-system forced-panel records.
        baseline = read_csv(directory / "availability_routing/system_predictions.csv")
        baseline = baseline[baseline["system"] == "availability_router"].copy()
        if "repeat" not in baseline:
            baseline["repeat"] = 0
        for scenario, panel_frame in source.groupby("scenario", sort=True):
            print(f"Panel comparison {dataset} {scenario}", flush=True)
            old = baseline[baseline["scenario"] == scenario].sort_values(["repeat", "row_id"]).reset_index(drop=True)
            new = panel_frame.sort_values(["repeat", "row_id"]).reset_index(drop=True)
            if not np.array_equal(old["row_id"], new["row_id"]) or not np.array_equal(old["target"], new["target"]):
                raise ValueError("Masked comparison input identities mismatch")
            if not np.allclose(old["probability_calibrated"].to_numpy(float), new["probability_original"].to_numpy(float), rtol=0, atol=1e-12):
                raise ValueError("Matched masked probabilities differ from frozen source")
            original = panel_frame.copy()
            original["probability_calibrated"] = original["probability_original"].astype(float)
            expected_repeats = 5 if dataset in {"pidd", "sylhet"} else 1
            original = aggregate(original, ["scenario"], expected_repeats)
            retrained = aggregate(panel_frame, ["scenario"], expected_repeats)
            if len(original) != EXPECTED[dataset][0] or int(original["target"].sum()) != EXPECTED[dataset][1]:
                raise ValueError("Panel evaluation population mismatch")
            point, contrast = paired_bootstrap({"retrained": retrained, "masked": original}, [("retrained", "masked")],
                                              seed=42 + 2200000, name=f"panels_{dataset}_{scenario}")
            contrast["dataset"], contrast["panel"] = dataset, scenario
            contrast["endpoint"] = metadata["endpoint"]
            contrast["comparison_family"] = f"{dataset}:all_prespecified_panels_per_metric"
            all_contrasts.append(contrast)
            for strategy, frame in [("full_schema_masked", original), ("reduced_schema_retrained", retrained)]:
                system = "masked" if strategy == "full_schema_masked" else "retrained"
                estimates = metrics(frame)
                original_metrics = metrics(original)
                row = {"dataset": dataset, "endpoint": metadata["endpoint"], "panel": scenario,
                       "predictor_count": len(panels()[dataset]["scenarios"][scenario]["available_features"]),
                       "training_strategy": strategy if scenario != "full" else "full_schema_original_reused_control",
                       "comparison_arm": system, "model_family": "|".join(sorted(set(panel_frame["model"]))),
                       "calibration": "|".join(sorted(set(panel_frame["calibration_method"]))) if system == "retrained" else "original scenario-specific selected mapping",
                       "evaluation_n": len(frame), "new_tuning_trials": 0, **estimates}
                for m in METRICS:
                    ci = point[(point["system"] == system) & (point["metric"] == m)].iloc[0]
                    row[f"{m}_ci_lower"], row[f"{m}_ci_upper"] = ci.ci_lower, ci.ci_upper
                    row[f"{m}_difference_vs_masked"] = estimates[m] - original_metrics[m]
                summaries.append(row)
    contrasts = holm(pd.concat(all_contrasts, ignore_index=True), ["dataset", "metric"])
    contrasts.to_csv(REPORT / "04_PANEL_PAIRED_CONTRASTS.csv", index=False)
    summary = pd.DataFrame(summaries)
    save_table("04_RETRAINED_PANEL_COMPARISON", summary,
        "# Independently fitted panel comparison\n\nCOMPLETE for every panel under `experiment_plan.json`. All 22 full/reduced panels are evaluated on the original records and splits. "
        "234 reduced-schema tasks fit 1404 base models (five training-only OOF fits and one final fit each), plus training-only calibration selection/refitting. "
        "52 full-panel controls reuse their already fitted identical-schema model and scenario mapping. "
        "Every original-arm probability matches the saved frozen dynamic forced-panel comparator within 1e-12.\n\n"
        "The family is the original development-selected family for that panel and outer training partition. Both arms share the same frozen full-schema "
        "hyperparameters inherited from the original 75-trial search; neither receives new tuning. Only declared panel predictors enter reduced-schema training, "
        "including preprocessing. Original full-predictor profile groups are retained for Sylhet; Hospital130 patients remain separated. "
        "Calibration candidates, minimum samples and five-fold budgets match the original; mapping selection may differ. "
        "This estimates a controlled conditional effect of training schema, not the optimum independently tuned/family-selected panel model. "
        "The limitation is prespecified and not a silent tuning-budget reduction.\n\n"
        + markdown_table(summary[["dataset", "panel", "comparison_arm", "predictor_count", "evaluation_n", "auroc", "average_precision", "brier_score", "log_loss"]]) +
        "\n\nAll probability metrics and joint logistic calibration diagnostics are provided. `04_PANEL_PAIRED_CONTRASTS.csv` contains retrained-minus-masked "
        "effect sizes with 2000-resample paired percentile intervals. Bootstrap units: PIDD participants; Sylhet original identical-profile clusters; "
        "BRFSS individuals; Hospital130 patient clusters. Holm families include all panels within each cohort and metric. "
        "These are post-review internal-validation comparisons conditional on fitted predictions. Full-panel identity contrasts are zero by construction and "
        "are retained in the declared family. Models/predictions/OOF identity hashes, seeds, component timings and checkpoints stay private under outputs/journal_revision_v1.")
    print("Panel comparison reports complete", flush=True)
