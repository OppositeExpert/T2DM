# Final model analysis report

Overall status: PARTIAL. Mentor A4 computational reporting is COMPLETE; this does not complete historical replay. Declared successor experiments and their verification are COMPLETE; exact historical training replay is BLOCKED and historical component timing reconstruction is PARTIAL. See WORK_STATUS.csv.

## 1. Executive summary

All declared bounded post-review analyses executed: 22 panels, 286 panel/fold combinations, 1404 newly fitted base models, training-only panel calibration, a frozen-family 2x2 ablation, saved-output sensitivity/routing/selective analyses, statistical reconstruction and local cost benchmarking. The original frozen evidence is unchanged. The reduced-schema comparison is conditional on original development-selected families and full-schema hyperparameters; it is not independently retuned optimization. The framework remains a useful availability/endpoint/provenance implementation, but it does not consistently outperform simpler systems. Read metric-specific conditional effects and uncertainty rather than a pooled leaderboard.

## 2. Mentor requests addressed

A1 schema training/fixed imputation/calibration-switching; A2 routing; A3 repeat sensitivity; A4 cost; B7 distinct PIDD estimands; C8 selective reporting; C9 statistical verification. See MENTOR_RESPONSE_EVIDENCE.md for evidence and limitations.

## 3. Existing analyses reused

Original raw data, frozen split manifests, per-fold/participant/base/stress/runtime predictions, trained preprocessing/models, full/scenario calibrators, development-only choices, statistical records and historical tune/final-fit times. All 1304 release fingerprints verified before fitting; 1538 original input/evidence fingerprints are protected by a separate before/after baseline.

## 4. New experiments performed

234 reduced-schema tasks each use five original-boundary base OOF fits, one final fit and training-only calibration selection. 52 full-panel combinations reuse identical-schema fitted controls. No new hyperparameter trial, evaluation-driven choice, original protocol change or new final-run receipt was introduced. Source/configuration and seed fingerprints are recorded.

## 5. Reduced-schema retraining results

04_RETRAINED_PANEL_COMPARISON.csv supplies both arms for all 22 panels; 04_PANEL_PAIRED_CONTRASTS.csv supplies four probability metrics, paired intervals and Holm values. The following counts summarize each cohort separately; point-estimate advantages are not automatically inferential findings.

| dataset | metric | reduced_panels | retrained_point_estimate_better | retrained_holm_significant_better | masked_holm_significant_better |
| --- | --- | --- | --- | --- | --- |
| brfss | auroc | 5 | 5 | 5 | 0 |
| brfss | average_precision | 5 | 5 | 5 | 0 |
| brfss | brier_score | 5 | 5 | 5 | 0 |
| brfss | log_loss | 5 | 5 | 5 | 0 |
| hospital130 | auroc | 4 | 2 | 1 | 1 |
| hospital130 | average_precision | 4 | 2 | 1 | 2 |
| hospital130 | brier_score | 4 | 2 | 1 | 2 |
| hospital130 | log_loss | 4 | 2 | 2 | 1 |
| pidd | auroc | 5 | 5 | 0 | 0 |
| pidd | average_precision | 5 | 3 | 0 | 0 |
| pidd | brier_score | 5 | 4 | 0 | 0 |
| pidd | log_loss | 5 | 5 | 0 | 0 |
| sylhet | auroc | 4 | 2 | 0 | 0 |
| sylhet | average_precision | 4 | 2 | 0 | 0 |
| sylhet | brier_score | 4 | 3 | 0 | 0 |
| sylhet | log_loss | 4 | 3 | 0 | 0 |

## 6. Fixed-imputation comparator results

A uses the original robust family, training-fitted full-schema imputation and original full-schema calibrator. B adds scenario calibration, C uses frozen dynamic families with original full mappings, and D is the original framework. All systems share availability eligibility and records. Hospital130 A has higher AUROC/AP point estimates than D; loss metrics can favor D. Full metric-specific tests follow.

| dataset | system | evaluation_n | auroc | average_precision | brier_score | log_loss |
| --- | --- | --- | --- | --- | --- | --- |
| pidd | A | 768 | 0.834933 | 0.702955 | 0.155736 | 0.472273 |
| pidd | B | 768 | 0.83541 | 0.706029 | 0.155632 | 0.471483 |
| pidd | C | 768 | 0.836552 | 0.704993 | 0.154946 | 0.470365 |
| pidd | D | 768 | 0.836866 | 0.70722 | 0.154868 | 0.469674 |
| sylhet | A | 520 | 0.969141 | 0.981579 | 0.0680246 | 0.224178 |
| sylhet | B | 520 | 0.966844 | 0.980246 | 0.0687497 | 0.230793 |
| sylhet | C | 520 | 0.972125 | 0.98384 | 0.0599277 | 0.203317 |
| sylhet | D | 520 | 0.972641 | 0.984068 | 0.0602788 | 0.203911 |
| brfss | A | 84632 | 0.832677 | 0.424636 | 0.0939934 | 0.303948 |
| brfss | B | 84632 | 0.835658 | 0.429394 | 0.093151 | 0.301284 |
| brfss | C | 84632 | 0.832822 | 0.425572 | 0.0938552 | 0.3036 |
| brfss | D | 84632 | 0.835889 | 0.429731 | 0.0930934 | 0.301178 |
| hospital130 | A | 19868 | 0.634262 | 0.188885 | 0.0988425 | 0.345959 |
| hospital130 | B | 19868 | 0.633512 | 0.180837 | 0.0983538 | 0.343124 |
| hospital130 | C | 19868 | 0.62714 | 0.187402 | 0.0989353 | 0.34599 |
| hospital130 | D | 19868 | 0.62714 | 0.187402 | 0.0983152 | 0.343259 |

## 7. Calibration and switching ablation results

The table below includes only Holm-adjusted p<.05 among five declared contrasts per cohort/metric. Positive improvement favors model_a; literal differences are model_a minus model_b. All nonsignificant and negative results remain in the complete CSV. Calibration effects are B-A/D-C; switching effects C-A/D-B; D-A is the complete framework versus fixed imputation.

| dataset | model_a | model_b | metric | observed_difference_a_minus_b | observed_improvement_a_over_b | holm_adjusted_p_value |
| --- | --- | --- | --- | --- | --- | --- |
| sylhet | B | A | log_loss | 0.00661509 | -0.00661509 | 0.01999 |
| sylhet | D | B | log_loss | -0.0268817 | 0.0268817 | 0.031984 |
| brfss | B | A | auroc | 0.00298143 | 0.00298143 | 0.0049975 |
| brfss | B | A | average_precision | 0.00475831 | 0.00475831 | 0.0049975 |
| brfss | B | A | brier_score | -0.000842436 | 0.000842436 | 0.0049975 |
| brfss | B | A | log_loss | -0.00266371 | 0.00266371 | 0.0049975 |
| brfss | D | C | auroc | 0.00306742 | 0.00306742 | 0.0049975 |
| brfss | D | C | average_precision | 0.00415898 | 0.00415898 | 0.0049975 |
| brfss | D | C | brier_score | -0.000761764 | 0.000761764 | 0.0049975 |
| brfss | D | C | log_loss | -0.00242171 | 0.00242171 | 0.0049975 |
| brfss | C | A | brier_score | -0.000138198 | 0.000138198 | 0.0049975 |
| brfss | C | A | log_loss | -0.000347974 | 0.000347974 | 0.007996 |
| brfss | D | A | auroc | 0.00321238 | 0.00321238 | 0.0049975 |
| brfss | D | A | average_precision | 0.00509563 | 0.00509563 | 0.0049975 |
| brfss | D | A | brier_score | -0.000899962 | 0.000899962 | 0.0049975 |
| brfss | D | A | log_loss | -0.00276968 | 0.00276968 | 0.0049975 |
| hospital130 | B | A | average_precision | -0.00804798 | -0.00804798 | 0.0049975 |
| hospital130 | B | A | brier_score | -0.000488682 | 0.000488682 | 0.0049975 |
| hospital130 | B | A | log_loss | -0.00283488 | 0.00283488 | 0.0049975 |
| hospital130 | D | C | brier_score | -0.000620089 | 0.000620089 | 0.0049975 |
| hospital130 | D | C | log_loss | -0.00273106 | 0.00273106 | 0.0049975 |
| hospital130 | D | B | average_precision | 0.00656517 | 0.00656517 | 0.015992 |
| hospital130 | D | A | brier_score | -0.000527354 | 0.000527354 | 0.0049975 |
| hospital130 | D | A | log_loss | -0.00269962 | 0.00269962 | 0.0049975 |

## 8. Per-repeat sensitivity

Five repeats are dependent. Sample SD is descriptive and never substituted for participant/group uncertainty. Primary probabilities are averaged per record before metrics. Full results include all benchmark, panel and runtime configurations.

| dataset | summary | auroc | average_precision | brier_score | log_loss |
| --- | --- | --- | --- | --- | --- |
| pidd | repeat_metric_mean | 0.832639 | 0.699255 | 0.157324 | 0.476492 |
| pidd | repeat_metric_sample_sd | 0.00569258 | 0.0158828 | 0.00332862 | 0.00726042 |
| pidd | participant_mean_probability_metric | 0.836866 | 0.70722 | 0.154868 | 0.469674 |
| pidd | repeat_metric_mean_minus_primary | -0.00422687 | -0.00796405 | 0.00245565 | 0.00681834 |
| sylhet | repeat_metric_mean | 0.962944 | 0.9784 | 0.0665965 | 0.241065 |
| sylhet | repeat_metric_sample_sd | 0.00766712 | 0.00545379 | 0.00415086 | 0.0304336 |
| sylhet | participant_mean_probability_metric | 0.972641 | 0.984068 | 0.0602788 | 0.203911 |
| sylhet | repeat_metric_mean_minus_primary | -0.00969687 | -0.0056684 | 0.00631772 | 0.0371534 |

## 9. Routing distribution and fallback explanations

| dataset | panel | evaluation_records | positive_events | population_pct | event_pct |
| --- | --- | --- | --- | --- | --- |
| pidd | full | 392 | 130 | 51.0417 | 48.5075 |
| pidd | minimal_glucose_age | 11 | 2 | 1.43229 | 0.746269 |
| pidd | no_insulin_or_skinfold | 332 | 119 | 43.2292 | 44.403 |
| pidd | non_laboratory | 33 | 17 | 4.29688 | 6.34328 |
| sylhet | full | 520 | 320 | 100 | 100 |
| brfss | UNSUPPORTED | 1240 | 135 | 1.44401 | 1.17894 |
| brfss | cardiometabolic_health | 11586 | 1769 | 13.4922 | 15.4484 |
| brfss | demographics_health | 5505 | 837 | 6.4107 | 7.30941 |
| brfss | full | 49403 | 7028 | 57.531 | 61.3746 |
| brfss | health_status | 10500 | 460 | 12.2275 | 4.01712 |
| brfss | minimal_general_health_age | 3879 | 569 | 4.51719 | 4.969 |
| brfss | routine_survey | 3759 | 653 | 4.37745 | 5.70256 |
| hospital130 | encounter_utilization | 19868 | 2262 | 100 | 100 |

Every selected panel matches raw-input eligibility reconstruction. Hospital130 routes all 19868 encounters to encounter-utilization (RF/sigmoid). BRFSS has 1240 availability abstentions (135 events). Larger-panel missing-feature counts and per-repeat family/mapping assignments are exported. Full-panel stress accepts imputation on all configured columns; runtime demands a fully observed supported panel.

## 10. Selective prediction findings

| dataset | actual_observation_coverage | positive_event_coverage | accepted_positive_events | rejected_positive_events | accepted_prevalence | rejected_prevalence | brier_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pidd | 0.700521 | 0.548507 | 147 | 121 | 0.273234 | 0.526087 | 0.113902 |
| sylhet | 0.7 | 0.76875 | 246 | 74 | 0.675824 | 0.474359 | 0.0247082 |
| brfss | 0.700007 | 0.269409 | 3085 | 8366 | 0.0513217 | 0.324754 | 0.0461962 |
| hospital130 | 0.700121 | 0.385942 | 873 | 1389 | 0.0627606 | 0.233132 | 0.0602787 |

Confidence rejection preferentially excludes positive events in low-prevalence cohorts. Accepted-case Brier is conditional on a selected population; its reduction does not establish better whole-population prediction. Availability abstention and confidence rejection are counted separately, and all original tie/group rules reproduce.

## 11. Computational cost

A4 reporting completeness: COMPLETE. Historical component reconstruction: PARTIAL; exact historical replay: BLOCKED. Existing historical tuning/final-fit timers and completed successor OOF/preprocessing/final-fit/calibration timers were reused. Only missing calibration-application latency, exact 256-record PIDD/Sylhet throughput and storage decomposition/unique-model collections were supplemented; no model or calibration fitting occurred.

| dataset | reduced_tasks | successor_final_fit_sum_s | successor_calibration_sum_s | D_single_median_ms | D_batch256_median_ms | exemplar_model_MiB | exemplar_calibrator_MiB | exemplar_prediction_triple_MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pidd | 125 | 13.0258 | 0.889598 | 2.13562 | 6.27158 | 0.0554867 | 0.000576019 | 0.0569286 |
| sylhet | 100 | 19.0643 | 3.79167 | 28.0335 | 52.9328 | 0.81616 | 0.000576973 | 0.817732 |
| brfss | 5 | 51.4581 | 3.80137 | 2.14658 | 11.2605 | 0.759795 | 8.86917e-05 | 0.761136 |
| hospital130 | 4 | 14.6965 | 67.0703 | 30.6046 | 45.9091 | 27.1382 | 0.000575066 | 27.1416 |

Training/calibration columns are successor SUMS in seconds; inference is milliseconds per loaded one-router call on original fitted artifacts. Storage is MiB (2^20 bytes), independent model/calibrator and combined prediction triple for the first original runtime-panel exemplar. See A4_PUBLICATION_READY_SUMMARY.md for historical family timings, preprocessing/OOF components, exact conditions, p05/p95/ranges, all storage configurations, source files and limitations. Current Apple M2 Pro/16 GB hardware is not attributed to historical training.

## 12. Statistical comparisons

220 verification records and 80 Table S9 numerical fields reconcile. Original three-pair policy Holm families reproduce. The smallest router/robust AUROC adjusted p is 0.074963 for Hospital130 and its direction favors robust fixed. Sylhet log-loss adjusted p=0.026987 and Hospital130 AP adjusted p=0.005997 are isolated original advantages. They do not establish consistent switching superiority.

## 13. Confidence interval and estimand verification

PIDD forced core-metabolic AUROC and runtime-policy AUROC have separately reconstructed predictions/intervals; exact values and file/seed mappings are in 07_PIDD_ESTIMANDS.csv. Both rounded estimates are .837; their populations have the same 768 records/268 events but different probability constructions. Never substitute their intervals. Streaming bootstrap samples match the original sampler; zero-boundary tail draws use original sklearn arithmetic to preserve historical numerical definitions.

## 14. Main scientific findings

The detailed results support feature-availability evaluation and explicit abstention. Independent schema fits can change performance materially, with advantages depending on cohort/panel/metric. Dynamic family selection and panel calibration have mixed effects; the negative findings are retained. Every metric is endpoint-specific; no cross-cohort probabilities or performances are pooled.

## 15. Negative or inconclusive findings

No consistent Holm-corrected original switching advantage. Hospital130 robust fixed outperforms the router by AUROC point estimate. Panel-specific calibration worsens Sylhet dynamic Brier/log loss point estimates. Reduced-panel improvements are not uniform; the complete contrasts preserve losses and nonsignificant findings. Full-panel retrained/control identity contrasts are zero by construction.

## 16. Interpretation boundaries

Post-review internal validation only; reused partitions were historically accessed. Conditional fixed-hyperparameter comparisons do not establish optimal reduced-model performance. Bootstrap intervals are conditional on fitted predictions and exclude refit/tuning variability. SHAP is not causal; retrospective utility is not clinical validation; Hospital130 is 30-day readmission. Patient-wrapper 25-router ensembles differ from five-OOF-repeat evaluation.

## 17. Missing evidence or remaining blockers

No required input is missing for the declared successor experiments. Overall historical reproducibility is PARTIAL: exact end-to-end historical training replay is BLOCKED because the complete source matching the recorded training fingerprint was not found in 14 accessible Git source revisions or either of two preserved local archives (read-only comparison; HISTORICAL_SOURCE_SEARCH.json). Off-site immutable artifact deposit and separately timed original calibration/OOF costs remain unavailable. A fully retuned reduced-schema benchmark would require a new, substantially larger budget and is not represented as completed here. WORK_STATUS.csv separates COMPLETE successor analyses, PARTIAL historical cost reconstruction and BLOCKED historical replay. Author/manuscript/submission work remains outside this model-analysis scope.

## 18. Reproducibility instructions

See REPRODUCE.md. Use the recorded environment, local raw data/private frozen artifacts and original metadata paths. Run saved/ablation/statistics, resume or regenerate declared panel tasks, summarize panels, benchmark, verify and report. Never rerun the final orchestrator or overwrite original outputs. A clean environment can validate portable tests without private data; exact historical full-study retraining is a separate unresolved claim.

Verification: full suite 147 passed plus 7 subtests; portable clean checkout 140 passed with 7 data-dependent tests excluded. The isolated environment reused the recorded dependency distributions and had its own local editable installation; it was not a fresh network resolution. New tests cover sampler parity, weighted metrics/ties, paired tail arithmetic, repeat corruption, Holm families, abstention parsing and evaluation-label/excluded-feature invariance. See QA_REPORT.md and FINAL_VERIFICATION.json for failed attempts, numerical tolerances and artifact/table checks.

## 19. Exact source mapping for every reported result

ANALYSIS_SOURCE_MAP.csv maps every numeric result row to cohort/endpoint/input/source/configuration/split/seed/output/Git commit/command. MODEL_CONFIGURATIONS.csv exports exact router-family hyperparameters/full/panel mapping choices; BASE_MODEL_CONFIGURATIONS.csv includes all five original benchmark families, including Logistic Regression. PANEL_TASK_MANIFEST.csv maps all 286 completed tasks to seeds and signatures. analysis_source_fingerprints.json binds the exact uncommitted new source; final report source hashes are exported after final validation.

## 20. Suggested tables/figures for manuscript authors

Use a matched-schema panel table with paired effects/CI; the 2x2 ablation table with cohort/metric Holm tests; five-repeat sensitivity versus primary estimand; unique routing-panel counts with events; selective observation/event coverage and excluded prevalence; computational component and inference/storage table; distinct PIDD estimand source/CI footnotes. Figures can show paired panel deltas, cohort-specific risk/event coverage curves and local latency distributions. Keep the complete negative-result rows in supplementary evidence.
