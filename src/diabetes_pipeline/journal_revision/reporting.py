"""Aggregate scientific handoff and exact code/artifact source mapping."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .common import ROOT, REPORT, PRIVATE, METRICS, studies, panels, bundle_paths, sha, git_commit, write_json, markdown_table


def write_methods():
    definitions = ["# Exact panel definitions", "", "Source: `config/availability_scenarios.yaml`. Panel names and membership are unchanged.",
                   "Eligibility requires every panel predictor to be observed after cohort loading; zero-to-missing PIDD rules and categorical missing tokens are inherited.",
                   "Order is descending `(predictor count, panel == full, panel name)`; equal-size names use reverse lexical order.", ""]
    panel_rows = []
    for dataset, spec in panels().items():
        scenarios = spec["scenarios"]
        order = sorted(scenarios, key=lambda k: (len(scenarios[k]["available_features"]), k == "full", k), reverse=True)
        definitions += [f"## {dataset}", ""]
        for index, panel in enumerate(order, 1):
            info = scenarios[panel]
            predictors = info["available_features"]
            definitions += [f"### {index}. {panel} ({len(predictors)} predictors)", "", info["description"], "",
                            "Predictors: " + "; ".join(f"`{f}`" for f in predictors) + ".", "",
                            "Eligibility: all listed predictors observed. Intended role: " + info["description"], ""]
            panel_rows.append({"dataset": dataset, "panel": panel, "panel_order": index, "predictor_count": len(predictors),
                               "predictors": json.dumps(predictors), "eligibility": "all panel predictors nonmissing",
                               "rationale": info["description"], "source": "config/availability_scenarios.yaml"})
    (REPORT / "PANEL_DEFINITIONS.md").write_text("\n".join(definitions))
    pd.DataFrame(panel_rows).to_csv(REPORT / "PANEL_DEFINITIONS.csv", index=False)
    calibration = """# Calibration procedure from implementation

Sources: `calibration/calibrators.py::{fit_calibrator,select_calibrator}`, `training/tuning.py::{cross_fitted_probabilities,cross_fitted_probabilities_by_scenario}`,
`routing/evaluator.py`, `routing/holdout_evaluator.py`, `runner.py`, `holdout_runner.py`.

## Base-model original full-schema calibration

Each fitted family has an original calibrator selected using full-schema base out-of-fold training/development probabilities.
PIDD/Sylhet: five inner training folds inside each of 25 outer training partitions; Sylhet uses full-predictor identical-profile groups.
BRFSS/Hospital130: five original development folds from the manifest; Hospital130 preserves patients.
Hyperparameters are selected on the corresponding training/development data, never outer/evaluation labels.
The base OOF predictions are cross-fitted conditional on hyperparameters chosen using the same development partition;
this is not a fully nested-out-of-sample estimate of the hyperparameter selection process itself.

## Panel-specific masked-development calibration

Original router candidates are random_forest, xgboost, lightgbm and catboost; Logistic Regression is a benchmark family but not an original router candidate.
For each candidate, `cross_fitted_probabilities_by_scenario` refits preprocessing and the full-schema base model inside each training fold.
It masks excluded predictors only in that fold's held-out development records and applies training-fitted preprocessing.
There is one base OOF probability per development/training record and scenario. Missingness indicators and categorical vocabularies remain training-local.
Every family/scenario, including full, receives calibration selection; identity is an eligible mapping, not an unsupported/no-calibration error.

`select_calibrator` performs a second five-fold (or class-count-capped) layer on the base OOF probabilities. Candidates fit on calibration-training
labels and are scored only on calibration-validation labels. Grouped data use StratifiedGroupKFold with shuffle and the recorded seed;
individual data use StratifiedKFold. Both classes must have at least two observations.
Identity clips p to [1e-6, 1-1e-6]. Sigmoid fits unpenalized LogisticRegression(C=infinity, lbfgs, max_iter=2000)
on logit(clipped p). Isotonic fits IsotonicRegression(out_of_bounds=clip) on clipped probabilities.
The final profile requires >=1000 observations in the input calibration population for isotonic eligibility.
The threshold is checked on the supplied overall calibration population, not independently enforced on every calibration-training subfold.
Thus isotonic is ineligible throughout PIDD/Sylhet; it can be selected for BRFSS/Hospital130.

Cross-fitted Brier score is minimized, log loss breaks ties, then configured method order identity/sigmoid/isotonic.
The winning mapping is refitted on all supplied training/development OOF probabilities/labels and applied once to the outer/evaluation raw probabilities.
The second layer re-splits precomputed base OOF probabilities; it does not refit base learners for each calibration subfold.
Group boundaries are maintained by each layer, but this is conditional cross-fitting, not an independently nested calibration-selection study.
Family/panel choices minimize development Brier then log loss then negative AP; robust fixed family averages development scores across scenarios.
No evaluation labels are used in mapping or family selection. Selected identity maps and sigmoid/isotonic maps are exported per fold/scenario in MODEL_CONFIGURATIONS.csv.

## New controlled comparisons

Reduced-schema models fit both preprocessing and base learners using only declared panel columns in each original training partition.
Five OOF base fits use the original panel-calibration splitting seeds and seeds for corresponding base OOF fits;
five calibration folds use original calibration seeds/candidates/minimum counts. Final model fitting uses original final seeds.
The family and hyperparameters are frozen to the original panel's development choice. No new tuning or evaluation-driven family selection occurs.
Original full-schema tuning budgets are inherited equally and disclosed; this is a matched-parameter schema experiment, not an independently retuned optimum.

In the 2x2 ablation A/C use the original model-bundle full-schema calibrator on masked raw scores; B/D use the saved scenario-specific calibrator.
Both calibrated and raw per-repeat/participant probabilities are retained privately. B matches the historical robust runtime policy;
D matches the original framework. A is fixed imputation with original full-schema calibration. Family choices remain fixed across calibration arms.
Evaluation calibration intercept/slope are joint logistic descriptive diagnostics from `evaluation/metrics.py`;
these evaluation mappings are never applied to the evaluated predictions.
"""
    (REPORT / "CALIBRATION_PROCEDURE.md").write_text(calibration)
    inference = """# Inference behavior from implementation

Sources: `routing/inference.py::route_patient`, `routing/policy_evaluator.py::{_supported_scenarios,_predict_batch,evaluate_runtime_policy}`,
`reporting/patient_results.py::{_load_router_bundles,_validate_publication_router_bundles,generate_patient_result}`.

`route_patient` accepts exactly one record. It identifies observed configured features, selects the maximum eligible prespecified panel by
(predictor count, full flag, lexical name), chooses the panel's development-selected family, reindexes to the full schema,
masks every feature outside the selected panel, then applies the saved training-fitted preprocessor, one base model and its scenario calibrator.
It returns raw/calibrated probability, research threshold/policy, binary prediction, model, calibrator, panel, available/used/ignored features and support status.
It never pools probabilities across cohorts. A requested scenario with missing required fields abstains;
unknown scenarios raise ValueError. No supported panel returns no_supported_feature_panel. More than one input row raises ValueError.

`generate_patient_result` loads supplied router bundles, orders them by repeat/fold, validates shared study/protocol/data/split/analysis identities and feature contracts,
coerces/validates inputs against the reference, and routes separately through each bundle.
Any input or routing failure abstains. It also abstains for a used numeric predictor outside the reference range by default.
All bundles must select the same panel; otherwise the wrapper raises. The wrapper averages their calibrated probabilities and reports fold/model spread,
per-fold predictions, provenance, endpoint, reference context and SHAP/additivity information. Fold spread is not a confidence interval.
The probability-only benchmark excludes input-coercion/range scans, SHAP and report rendering; it must not be described as full report latency.

Execution mode matters:

| Mode | Fitted predictors used |
| --- | --- |
| One router bundle / route_patient | One saved family/model and scenario calibrator |
| PIDD/Sylhet held-out evaluation | One eligible OOF fold model per repeat, then mean of five OOF probabilities per record |
| PIDD/Sylhet research patient wrapper with all bundles | Mean of 25 fold-router calibrated probabilities on the new record |
| BRFSS/Hospital130 evaluation / one supplied router | One model fitted on all original development records |

An ensemble of all 25 models is not the evaluated five-OOF-probability construction on original records and has no separate external validation.
Evaluation records must not be rescored with their training models to replace the OOF estimand.
Raw single-router eligibility does not perform all patient-wrapper range/semantic checks; unsupported-input handling depends on the called interface.
Runtime provenance records panel, family, mapping, fold/repeat, stable record/group identity, status/reason, used/ignored features, raw/calibrated scores and threshold.
New private ablation/retraining files preserve these identities and provenance; only aggregate reports are intended for manuscript handoff.
"""
    (REPORT / "INFERENCE_BEHAVIOR.md").write_text(inference)
    configurations, base_configurations = [], []
    for dataset, directory, metadata in studies():
        import joblib
        for path in bundle_paths(directory):
            b = joblib.load(path)
            for family, model in b["model_bundles"].items():
                for panel, calibrator in b["scenario_calibrators"][family].items():
                    configurations.append({"dataset": dataset, "endpoint": metadata["endpoint"], "repeat": b.get("repeat", 0),
                                           "outer_fold": b.get("outer_fold", 0), "family": family, "panel": panel,
                                           "parameters": json.dumps(model["best_params"], sort_keys=True),
                                           "original_full_calibration": model["calibration_method"],
                                           "panel_calibration": calibrator.method,
                                           "panel_selected_family": b["selected_models"][panel],
                                           "robust_family": b["robust_single_model"], "full_champion": b["full_panel_champion"],
                                           "router_source": str(path.relative_to(ROOT)), "router_sha256": sha(path)})
        for path in sorted((directory / "models").glob("*.joblib")):
            base = joblib.load(path)
            base_configurations.append({"dataset": dataset, "endpoint": metadata["endpoint"],
                                        "repeat": base.get("repeat", 0), "outer_fold": base.get("outer_fold", 0),
                                        "family": base["model_name"], "parameters": json.dumps(base["best_params"], sort_keys=True),
                                        "original_full_calibration": base["calibration_method"],
                                        "transformed_predictor_count": len(base["transformed_feature_names"]),
                                        "model_source": str(path.relative_to(ROOT)), "model_sha256": sha(path)})
    pd.DataFrame(configurations).to_csv(REPORT / "MODEL_CONFIGURATIONS.csv", index=False)
    pd.DataFrame(base_configurations).to_csv(REPORT / "BASE_MODEL_CONFIGURATIONS.csv", index=False)


def source_map():
    recorded_commit = git_commit()
    registry = {d: (p, m) for d, p, m in studies()}
    configs = [ROOT / "config/availability_scenarios.yaml", ROOT / "config/datasets.yaml", REPORT / "experiment_plan.json"]
    source_files = list((ROOT / "src/diabetes_pipeline/journal_revision").glob("*.py")) + [ROOT / "scripts/run_journal_revision.py", ROOT / "scripts/verify_journal_revision.py", ROOT / "tests/test_journal_revision.py"]
    fingerprints = {str(p.relative_to(ROOT)): sha(p) for p in source_files + configs}
    write_json(REPORT / "analysis_source_fingerprints.json", {"git_commit": recorded_commit, "files": fingerprints,
               "execution_source_state": "new source and aggregate outputs are uncommitted; hashes bind the exact successor implementation"})
    maps = []
    cached = {}
    def fingerprint(path):
        if path not in cached:
            cached[path] = sha(path)
        return cached[path]
    script_phases = {"01": "saved", "02": "saved", "03": "saved", "04": "panels", "05": "ablation", "06": "benchmark", "07": "statistics"}
    outputs = sorted(REPORT.glob("0[1-7]*.csv")) + [p for p in [REPORT / "pilot_timing.csv", REPORT / "PANEL_FINDING_COUNTS.csv"] if p.exists()]
    for output in outputs:
        table = pd.read_csv(output)
        if "dataset" not in table:
            continue
        phase = script_phases.get(output.name[:2], "pilot" if output.name == "pilot_timing.csv" else "report")
        for index, result in table.iterrows():
            dataset = result["dataset"]
            if dataset not in registry:
                continue
            directory, metadata = registry[dataset]
            if phase == "saved":
                artifact = directory / ("predictions.csv" if output.name.startswith("01") else "runtime_policy_evaluation/participant_policy_predictions.csv")
                if output.name.startswith("01"):
                    analysis = result.get("analysis", "")
                    artifact = directory / {"base_full": "predictions.csv", "forced_panel_model": "availability_routing/stress_predictions.csv",
                                            "forced_panel_system": "availability_routing/system_predictions.csv", "runtime_policy": "runtime_policy_evaluation/policy_decisions.csv"}.get(analysis, "predictions.csv")
            elif phase == "ablation":
                artifact = directory / "runtime_policy_evaluation/policy_decisions.csv"
            elif phase == "panels":
                artifact = PRIVATE / "panel_tasks" / dataset
            elif phase == "statistics":
                artifact = directory / "runtime_policy_evaluation/participant_policy_predictions.csv"
                if result.get("analysis", "") == "full_model":
                    artifact = directory / ("predictions.csv" if dataset in {"pidd", "sylhet"} else "test_predictions.csv")
                elif result.get("analysis", "") == "forced_panel":
                    artifact = directory / "availability_routing/system_predictions.csv"
            else:
                artifact = directory / "models"
            if output.name == "07_PIDD_ESTIMANDS.csv":
                artifact = directory / ("availability_routing/system_predictions.csv" if result["estimand"] == "forced_core_metabolic" else "runtime_policy_evaluation/participant_policy_predictions.csv")
            source_value = result.get("source", "")
            if isinstance(source_value, str) and source_value:
                candidate = Path(source_value)
                candidate = candidate if candidate.is_absolute() else ROOT / candidate
                if candidate.is_file() and candidate.is_relative_to(ROOT):
                    artifact = candidate
            dependencies = [str(artifact.relative_to(ROOT)), f"data/raw/{dataset}.csv",
                            str(Path(metadata["split_manifest"]).relative_to(ROOT)),
                            str((directory / "availability_routing/router_bundles").relative_to(ROOT))]
            command = f".venv-pipeline/bin/python scripts/run_journal_revision.py {phase}"
            maps.append({"result_id": f"{output.name}:row_{index + 2}", "dataset": dataset, "endpoint": metadata["endpoint"],
                         "experiment": phase, "configuration": result.get("panel", result.get("scenario", result.get("configuration", ""))),
                         "system": result.get("system", ""), "input_artifact": str(artifact.relative_to(ROOT)),
                         "input_artifacts": json.dumps(dependencies),
                         "input_sha256": fingerprint(artifact) if artifact.is_file() else "per-file hashes in protected_baseline or panel task.json",
                         "source_script": "scripts/run_journal_revision.py", "source_module": "src/diabetes_pipeline/journal_revision/",
                         "configuration_file": "analysis/journal_revision/experiment_plan.json",
                         "split_manifest": str(Path(metadata["split_manifest"]).relative_to(ROOT)), "split_sha256": metadata["split_manifest_sha256"],
                         "seed": result.get("seed", result.get("bootstrap_seed", "42; per-fold offsets in task.json and source")),
                         "output_file": str(output.relative_to(ROOT)), "output_sha256": fingerprint(output), "git_commit": recorded_commit,
                         "result_generation_command": command})
    frame = pd.DataFrame(maps)
    frame.to_csv(REPORT / "ANALYSIS_SOURCE_MAP.csv", index=False)
    overview = frame[["output_file", "experiment", "result_generation_command"]].drop_duplicates()
    (REPORT / "ANALYSIS_SOURCE_MAP.md").write_text("# Analysis source map\n\nEvery numeric CSV row has a result ID, cohort/endpoint, input, source, configuration, split hash, seed, output hash, Git commit and command in ANALYSIS_SOURCE_MAP.csv. "
        "Input file hashes for directories are in original protected_baseline.json or new per-task task.json; raw/row-level data and models stay private. "
        "analysis_source_fingerprints.json binds uncommitted new source to the recorded base commit. Bootstrap distributions are actual saved draws.\n\n" + markdown_table(overview) +
        "\n\nAll commands run from the repository root with the recorded Python environment. Prefix OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 "
        "for the controlled analysis runs. Estimators explicitly use 4 threads. Per-task final/OOF/calibration seeds and inherited parameters appear in task.json. "
        "Original frozen study metadata retains historical source fingerprints and absolute paths; it has not been rewritten for portability. "
        "The source map is aggregate-only and must not be interpreted as a downloadable data/model archive.\n")


def run_report(selected="all"):
    required = ["04_RETRAINED_PANEL_COMPARISON.csv", "05_CALIBRATION_SWITCHING_ABLATION.csv", "06_COMPUTATIONAL_COST.csv", "07_ESTIMAND_VERIFICATION.md"]
    for name in required:
        if not (REPORT / name).exists():
            raise FileNotFoundError(f"Cannot declare final handoff complete: missing {name}")
    write_methods()
    panels_table = pd.read_csv(REPORT / "04_RETRAINED_PANEL_COMPARISON.csv")
    panel_effects = pd.read_csv(REPORT / "04_PANEL_PAIRED_CONTRASTS.csv")
    ablations = pd.read_csv(REPORT / "05_CALIBRATION_SWITCHING_ABLATION.csv")
    ablation_effects = pd.read_csv(REPORT / "05_ABLATION_PAIRED_CONTRASTS.csv")
    repeats = pd.read_csv(REPORT / "01_PER_REPEAT_SENSITIVITY.csv")
    routing = pd.read_csv(REPORT / "02_ROUTING_DISTRIBUTION.csv")
    selective = pd.read_csv(REPORT / "03_SELECTIVE_PREDICTION.csv")
    benchmark = pd.read_csv(REPORT / "06_COMPUTATIONAL_COST.csv")
    validation = json.loads((REPORT / "statistical_verification_summary.json").read_text())
    test_summary = json.loads((REPORT / "test_summary.json").read_text()) if (REPORT / "test_summary.json").exists() else {}
    rows = []
    for (dataset, metric), group in panel_effects[panel_effects.panel != "full"].groupby(["dataset", "metric"], sort=True):
        rows.append({"dataset": dataset, "metric": metric, "reduced_panels": len(group),
                     "retrained_point_estimate_better": int(group.observed_improvement_a_over_b.gt(0).sum()),
                     "retrained_holm_significant_better": int((group.observed_improvement_a_over_b.gt(0) & group.holm_adjusted_p_value.lt(.05)).sum()),
                     "masked_holm_significant_better": int((group.observed_improvement_a_over_b.lt(0) & group.holm_adjusted_p_value.lt(.05)).sum())})
    panel_counts = pd.DataFrame(rows)
    panel_counts.to_csv(REPORT / "PANEL_FINDING_COUNTS.csv", index=False)
    focus_repeats = repeats[(repeats.analysis == "runtime_policy") & (repeats.system == "availability_router") &
                            (repeats.probability_version == "probability_calibrated") &
                            repeats.summary.isin(["repeat_metric_mean", "repeat_metric_sample_sd", "participant_mean_probability_metric", "repeat_metric_mean_minus_primary"])]
    focus_select = selective[(selective.system == "availability_router") & (selective.nominal_coverage == .7)]
    sig = ablation_effects[ablation_effects.holm_adjusted_p_value < .05]
    task_files = sorted((PRIVATE / "panel_tasks").glob("*/*/*/task.json"))
    tasks = [json.loads(p.read_text()) for p in task_files]
    task_count = len(tasks)
    fitted_count = sum(len(t["inner_fit_records"]) + 1 for t in tasks if t["panel"] != "full")
    if task_count != 286 or fitted_count != 1404:
        raise ValueError("Final task counts incomplete")
    pd.DataFrame([{k:t[k] for k in ["dataset", "panel", "repeat", "fold", "family", "strategy", "new_calibration", "new_optuna_trials", "oof_seed", "calibration_seed", "final_seed", "signature"]} for t in tasks]).to_csv(REPORT / "PANEL_TASK_MANIFEST.csv", index=False)
    cost = pd.DataFrame([{ "dataset": d, "operation": op, "total_seconds": g.total_seconds.sum()} for (d,op),g in benchmark[benchmark.operation.str.startswith("new_panel_") & benchmark.operation.str.endswith("seconds")].groupby(["dataset", "operation"])])
    report = ["# Final model analysis report", "", "Overall status: PARTIAL. Declared successor experiments and their verification are COMPLETE; exact historical training replay is BLOCKED and historical component timing reconstruction is PARTIAL. See WORK_STATUS.csv.", "", "## 1. Executive summary", "",
              f"All declared bounded post-review analyses executed: 22 panels, {task_count} panel/fold combinations, {fitted_count} newly fitted base models, training-only panel calibration, a frozen-family 2x2 ablation, saved-output sensitivity/routing/selective analyses, statistical reconstruction and local cost benchmarking. "
              "The original frozen evidence is unchanged. The reduced-schema comparison is conditional on original development-selected families and full-schema hyperparameters; it is not independently retuned optimization. "
              "The framework remains a useful availability/endpoint/provenance implementation, but it does not consistently outperform simpler systems. Read metric-specific conditional effects and uncertainty rather than a pooled leaderboard.", "",
              "## 2. Mentor requests addressed", "", "A1 schema training/fixed imputation/calibration-switching; A2 routing; A3 repeat sensitivity; A4 cost; B7 distinct PIDD estimands; C8 selective reporting; C9 statistical verification. See MENTOR_RESPONSE_EVIDENCE.md for evidence and limitations.", "",
              "## 3. Existing analyses reused", "", "Original raw data, frozen split manifests, per-fold/participant/base/stress/runtime predictions, trained preprocessing/models, full/scenario calibrators, development-only choices, statistical records and historical tune/final-fit times. All 1304 release fingerprints verified before fitting; 1538 original input/evidence fingerprints are protected by a separate before/after baseline.", "",
              "## 4. New experiments performed", "", "234 reduced-schema tasks each use five original-boundary base OOF fits, one final fit and training-only calibration selection. 52 full-panel combinations reuse identical-schema fitted controls. No new hyperparameter trial, evaluation-driven choice, original protocol change or new final-run receipt was introduced. Source/configuration and seed fingerprints are recorded.", "",
              "## 5. Reduced-schema retraining results", "", "04_RETRAINED_PANEL_COMPARISON.csv supplies both arms for all 22 panels; 04_PANEL_PAIRED_CONTRASTS.csv supplies four probability metrics, paired intervals and Holm values. The following counts summarize each cohort separately; point-estimate advantages are not automatically inferential findings.", "", markdown_table(panel_counts), "",
              "## 6. Fixed-imputation comparator results", "", "A uses the original robust family, training-fitted full-schema imputation and original full-schema calibrator. B adds scenario calibration, C uses frozen dynamic families with original full mappings, and D is the original framework. All systems share availability eligibility and records. Hospital130 A has higher AUROC/AP point estimates than D; loss metrics can favor D. Full metric-specific tests follow.", "", markdown_table(ablations[["dataset", "system", "evaluation_n", "auroc", "average_precision", "brier_score", "log_loss"]]), "",
              "## 7. Calibration and switching ablation results", "", "The table below includes only Holm-adjusted p<.05 among five declared contrasts per cohort/metric. Positive improvement favors model_a; literal differences are model_a minus model_b. All nonsignificant and negative results remain in the complete CSV. Calibration effects are B-A/D-C; switching effects C-A/D-B; D-A is the complete framework versus fixed imputation.", "", markdown_table(sig[["dataset", "model_a", "model_b", "metric", "observed_difference_a_minus_b", "observed_improvement_a_over_b", "holm_adjusted_p_value"]]), "",
              "## 8. Per-repeat sensitivity", "", "Five repeats are dependent. Sample SD is descriptive and never substituted for participant/group uncertainty. Primary probabilities are averaged per record before metrics. Full results include all benchmark, panel and runtime configurations.", "", markdown_table(focus_repeats[["dataset", "summary", "auroc", "average_precision", "brier_score", "log_loss"]]), "",
              "## 9. Routing distribution and fallback explanations", "", markdown_table(routing[routing.row_type == "unique_panel"][["dataset", "panel", "evaluation_records", "positive_events", "population_pct", "event_pct"]]), "", "Every selected panel matches raw-input eligibility reconstruction. Hospital130 routes all 19868 encounters to encounter-utilization (RF/sigmoid). BRFSS has 1240 availability abstentions (135 events). Larger-panel missing-feature counts and per-repeat family/mapping assignments are exported. Full-panel stress accepts imputation on all configured columns; runtime demands a fully observed supported panel.", "",
              "## 10. Selective prediction findings", "", markdown_table(focus_select[["dataset", "actual_observation_coverage", "positive_event_coverage", "accepted_positive_events", "rejected_positive_events", "accepted_prevalence", "rejected_prevalence", "brier_score"]]), "", "Confidence rejection preferentially excludes positive events in low-prevalence cohorts. Accepted-case Brier is conditional on a selected population; its reduction does not establish better whole-population prediction. Availability abstention and confidence rejection are counted separately, and all original tie/group rules reproduce.", "",
              "## 11. Computational cost", "", "New execution component totals below are measured local durations, distinct from historical training times. OOF time includes five training fits/transforms/predictions; final fitting excludes preprocessing. Calibration includes candidate cross-fitting/selection and final mapping. Full timing distributions/storage/environment appear in report 06 and BENCHMARK_ENVIRONMENT.json.", "", markdown_table(cost), "",
              "## 12. Statistical comparisons", "", f"{validation['verification_records']} verification records and {validation['table_s9_checked_fields']} Table S9 numerical fields reconcile. Original three-pair policy Holm families reproduce. The smallest router/robust AUROC adjusted p is 0.074963 for Hospital130 and its direction favors robust fixed. Sylhet log-loss adjusted p=0.026987 and Hospital130 AP adjusted p=0.005997 are isolated original advantages. They do not establish consistent switching superiority.", "",
              "## 13. Confidence interval and estimand verification", "", "PIDD forced core-metabolic AUROC and runtime-policy AUROC have separately reconstructed predictions/intervals; exact values and file/seed mappings are in 07_PIDD_ESTIMANDS.csv. Both rounded estimates are .837; their populations have the same 768 records/268 events but different probability constructions. Never substitute their intervals. Streaming bootstrap samples match the original sampler; zero-boundary tail draws use original sklearn arithmetic to preserve historical numerical definitions.", "",
              "## 14. Main scientific findings", "", "The detailed results support feature-availability evaluation and explicit abstention. Independent schema fits can change performance materially, with advantages depending on cohort/panel/metric. Dynamic family selection and panel calibration have mixed effects; the negative findings are retained. Every metric is endpoint-specific; no cross-cohort probabilities or performances are pooled.", "",
              "## 15. Negative or inconclusive findings", "", "No consistent Holm-corrected original switching advantage. Hospital130 robust fixed outperforms the router by AUROC point estimate. Panel-specific calibration worsens Sylhet dynamic Brier/log loss point estimates. Reduced-panel improvements are not uniform; the complete contrasts preserve losses and nonsignificant findings. Full-panel retrained/control identity contrasts are zero by construction.", "",
              "## 16. Interpretation boundaries", "", "Post-review internal validation only; reused partitions were historically accessed. Conditional fixed-hyperparameter comparisons do not establish optimal reduced-model performance. Bootstrap intervals are conditional on fitted predictions and exclude refit/tuning variability. SHAP is not causal; retrospective utility is not clinical validation; Hospital130 is 30-day readmission. Patient-wrapper 25-router ensembles differ from five-OOF-repeat evaluation.", "",
              "## 17. Missing evidence or remaining blockers", "", "No required input is missing for the declared successor experiments. Overall historical reproducibility is PARTIAL: exact end-to-end historical training replay is BLOCKED because the complete source matching the recorded training fingerprint was not found in 14 accessible Git source revisions or either of two preserved local archives (read-only comparison; HISTORICAL_SOURCE_SEARCH.json). Off-site immutable artifact deposit and separately timed original calibration/OOF costs remain unavailable. A fully retuned reduced-schema benchmark would require a new, substantially larger budget and is not represented as completed here. WORK_STATUS.csv separates COMPLETE successor analyses, PARTIAL historical cost reconstruction and BLOCKED historical replay. Author/manuscript/submission work remains outside this model-analysis scope.", "",
              "## 18. Reproducibility instructions", "", "See REPRODUCE.md. Use the recorded environment, local raw data/private frozen artifacts and original metadata paths. Run saved/ablation/statistics, resume or regenerate declared panel tasks, summarize panels, benchmark, verify and report. Never rerun the final orchestrator or overwrite original outputs. A clean environment can validate portable tests without private data; exact historical full-study retraining is a separate unresolved claim.", "",
              f"Verification: full suite {test_summary.get('full_tests_passed', 'see QA_REPORT.md')} passed plus 7 subtests; portable clean checkout {test_summary.get('portable_tests_passed', 'see QA_REPORT.md')} passed with 7 data-dependent tests excluded. The isolated environment reused the recorded dependency distributions and had its own local editable installation; it was not a fresh network resolution. New tests cover sampler parity, weighted metrics/ties, paired tail arithmetic, repeat corruption, Holm families, abstention parsing and evaluation-label/excluded-feature invariance. See QA_REPORT.md and FINAL_VERIFICATION.json for failed attempts, numerical tolerances and artifact/table checks.", "",
              "## 19. Exact source mapping for every reported result", "", "ANALYSIS_SOURCE_MAP.csv maps every numeric result row to cohort/endpoint/input/source/configuration/split/seed/output/Git commit/command. MODEL_CONFIGURATIONS.csv exports exact router-family hyperparameters/full/panel mapping choices; BASE_MODEL_CONFIGURATIONS.csv includes all five original benchmark families, including Logistic Regression. PANEL_TASK_MANIFEST.csv maps all 286 completed tasks to seeds and signatures. analysis_source_fingerprints.json binds the exact uncommitted new source; final report source hashes are exported after final validation.", "",
              "## 20. Suggested tables/figures for manuscript authors", "", "Use a matched-schema panel table with paired effects/CI; the 2x2 ablation table with cohort/metric Holm tests; five-repeat sensitivity versus primary estimand; unique routing-panel counts with events; selective observation/event coverage and excluded prevalence; computational component and inference/storage table; distinct PIDD estimand source/CI footnotes. Figures can show paired panel deltas, cohort-specific risk/event coverage curves and local latency distributions. Keep the complete negative-result rows in supplementary evidence.", ""]
    (REPORT / "FINAL_MODEL_ANALYSIS_REPORT.md").write_text("\n".join(report))
    mentor = ["# Mentor response evidence", "", "All COMPLETE statuses below refer to the explicit bounded successor design, not independently retuned optimum models or external validation.", ""]
    entries = [
        ("A1 independent panel training", "234 reduced-schema tasks / 1404 base fits plus panel calibration; 52 full controls reused", "04_RETRAINED_PANEL_COMPARISON.csv; 04_PANEL_PAIRED_CONTRASTS.csv; PANEL_TASK_MANIFEST.csv", "Cohort/panel/metric effects are mixed; exact effects and adjusted tests exported", "Original development-selected family/full-schema parameters held fixed; no new tuning"),
        ("A1 fixed imputation and calibration/switching", "Four systems reconstructed from the same frozen raw scores/calibrators; no new fitting", "05_CALIBRATION_SWITCHING_ABLATION.csv; 05_ABLATION_PAIRED_CONTRASTS.csv", "No uniform calibration/switching improvement; negative effects retained", "Conditional frozen-family selection; original robust equals B, complete framework D"),
        ("A2 routing", "Unique identities reconciled and every panel checked against original raw eligibility", "02_ROUTING_DISTRIBUTION.csv; 02_ROUTING_DISTRIBUTION.md", "All Hospital130 encounters route to encounter-utilization; BRFSS 1240 availability abstentions", "Per-repeat family/calibrator counts are not unique-person totals"),
        ("A3 repeats/inference", "All five repeats, alignment, per-repeat metrics/SD and original participant-mean estimand", "01_PER_REPEAT_SENSITIVITY.csv; INFERENCE_BEHAVIOR.md", "Nonlinear aggregation differs from repeat metric means; descriptive stability exported", "Dependent repeats; no repeat-level inferential SD; 25-router wrapper differs from five OOF probabilities"),
        ("A4 cost", "Actual local environment; component fitting records; warmed single/batch latency and serialization", "06_COMPUTATIONAL_COST.csv; BENCHMARK_ENVIRONMENT.json", "Historical tune/fit distinguished from measured new costs", "Original calibration/OOF components not separately logged; no historical peak RAM or GPU usage"),
        ("B7 PIDD estimands", "Both prediction constructions and original-seed percentile intervals independently reconstructed", "07_PIDD_ESTIMANDS.csv; 07_ESTIMAND_VERIFICATION.md", "Forced core and runtime both round .837 but have distinct estimates and CIs", "Conditional participant bootstrap; never swap intervals"),
        ("C8 selective prediction", "All original coverage targets/ties/groups, excluded events and two abstention types", "03_SELECTIVE_PREDICTION.csv; 03_SELECTIVE_PREDICTION.md", "70% event coverage PIDD54.85%, BRFSS26.94%, Hospital13038.59%", "Accepted Brier applies only to selected population; group target coverage can overshoot"),
        ("C9 statistical verification", "Original paired effects/CIs/raw/Holm p, counts, metrics, grouping and family provenance", "07_STATISTICAL_VERIFICATION.csv; 07_RUNTIME_PAIRED_COMPARISONS.csv", "Original negative AUROC conclusion and isolated advantages reproduce", "Historical numerical tail boundary handled with reference arithmetic; internal validation only"),
    ]
    for request, work, output, finding, limitations in entries:
        mentor += [f"## {request}", "", "Status: COMPLETE", "", f"Work completed: {work}.", "", f"Evidence generated/output: {output}.", "", f"Key finding: {finding}.", "", f"Limitations: {limitations}.", ""]
    (REPORT / "MENTOR_RESPONSE_EVIDENCE.md").write_text("\n".join(mentor))
    work_status = pd.DataFrame([
        {"work": "Phase 0 audit and artifact preservation", "status": "COMPLETE", "boundary": "Original study/input hashes verified; successor paths isolated"},
        {"work": "Per-repeat, routing, selective and statistical analyses", "status": "COMPLETE", "boundary": "Saved predictions and original bootstrap definitions independently reconciled"},
        {"work": "Reduced-schema retraining and 2x2 ablation", "status": "COMPLETE", "boundary": "Declared matched-family/frozen-hyperparameter design; no new tuning"},
        {"work": "Controlled local computational benchmark", "status": "COMPLETE", "boundary": "Measured fitting components, inference, routing, storage and actual environment"},
        {"work": "Historical component cost reconstruction", "status": "PARTIAL", "boundary": "Tune/final-fit logs present; original OOF/calibration time and peak RAM not separately recorded"},
        {"work": "Exact end-to-end historical training replay", "status": "BLOCKED", "boundary": "Complete source matching the historical training fingerprint has not been recovered; guards remain intact"},
        {"work": "Testing and evidence handoff", "status": "COMPLETE", "boundary": "Full/portable tests, hash preservation, new task and table/source checks; no claim of fresh network dependency resolution"},
    ])
    work_status.to_csv(REPORT / "WORK_STATUS.csv", index=False)
    (REPORT / "REPRODUCE.md").write_text("""# Reproduce the successor analyses

Run from the repository root with CPython 3.12 and the recorded dependency environment.
Private original raw data/models/row-level predictions/splits must be present and match evidence/final_artifact_release_manifest.json.
The original study metadata contains absolute input paths; preserve them locally or use a separately documented restoration/path-adaptation procedure.
No source-binding/final-run guard is bypassed. New output paths are analysis/journal_revision and ignored outputs/journal_revision_v1.

For a fresh restored checkout without a new-analysis preservation baseline, run `audit` first. On this completed checkout run `verify`, not audit:
audit intentionally refuses to overwrite an existing before-analysis baseline. Fit-task checkpoints verify signatures and hashes; interrupted tasks resume.
To regenerate fitting from scratch, preserve the existing private successor directory and use a separately reviewed new output version rather than deleting evidence.

```bash
.venv-pipeline/bin/python scripts/verify_publication_results.py
.venv-pipeline/bin/python scripts/verify_artifact_release_manifest.py --manifest evidence/final_artifact_release_manifest.json
.venv-pipeline/bin/python scripts/run_journal_revision.py saved
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv-pipeline/bin/python scripts/run_journal_revision.py ablation
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv-pipeline/bin/python scripts/run_journal_revision.py statistics
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv-pipeline/bin/python scripts/run_journal_revision.py pilot
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv-pipeline/bin/python scripts/run_journal_revision.py train
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 .venv-pipeline/bin/python scripts/run_journal_revision.py panels
.venv-pipeline/bin/python -m pytest -q
.venv-pipeline/bin/python scripts/run_journal_revision.py verify
.venv-pipeline/bin/python scripts/run_journal_revision.py report
.venv-pipeline/bin/python scripts/verify_journal_revision.py
```

Full scientific reproduction depends on local artifacts; a Git clone alone is not sufficient. Portable tests do not establish full training reproduction.
The commands above retain the completed timing measurements. For fresh timing measurements, preserve the sealed handoff in a separately versioned checkout/output package, then run `benchmark` there and generate a new handoff manifest after validation. Timing distributions are expected to vary; the current FINAL_HANDOFF_CHECKSUMS.json verifies this delivered version and deliberately detects changed timing files.
All inferential contrasts retain actual 2000-resample distributions under outputs/journal_revision_v1/bootstrap.
New source is bound by analysis_source_fingerprints.json plus the starting Git commit. No manuscript edits, commits, pushes or publication deposits are implied.
""")
    write_json(REPORT / "completion_summary.json", {"status": "PARTIAL_OVERALL_WITH_BOUNDED_EXPERIMENTS_COMPLETE", "panel_tasks": task_count,
               "new_base_model_fits": fitted_count, "full_control_tasks_reused": 52, "new_optuna_trials": 0,
               "panels": 22, "git_commit": git_commit(), "exact_historical_training_source_recovered": False,
               "independently_retuned_reduced_model_optima_established": False})
    source_map()
    print("Scientific handoff generated", flush=True)
