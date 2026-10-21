# A4 publication-ready computational cost

A4 reporting: **COMPLETE**. Exact historical computational replay: **BLOCKED**; component reconstruction: **PARTIAL**. No training was performed for this completion task.

## Methodology

Historical tuning and final estimator fitting are reported from saved timers in the authoritative studies. PIDD/Sylhet metric rows were deduplicated by family/repeat/outer-fold (25 fitted models per family); holdout cohorts have one final model per family. Tuning comprises 75 Optuna trials per search, including objective validation, and excludes subsequent best-parameter OOF construction and final fitting. Separate historical OOF, preprocessing, calibration and inference times were not recorded. The completed matched-parameter reduced-schema successor supplies representative OOF, preprocessing, final-fit and calibration-selection timers; no new tuning occurred. Its OOF loop includes five preprocessing/fit/predict cycles and bookkeeping, while final fitting excludes preprocessing and calibration includes candidate cross-fitting, selection and final mapping. These are different workloads from the historical full-schema models and are never substituted for their missing timings.

Loaded CPU artifacts; perf_counter_ns elapsed wall time; three untimed warmups followed by 20 serial timed calls for each workload; median and linearly interpolated p05/p95 with observed minimum/maximum. Each call handles one record or one entire 256-record batch; batch latency is not per-record latency. OMP_NUM_THREADS=1, OPENBLAS_NUM_THREADS=1, VECLIB_MAXIMUM_THREADS=1, MKL_NUM_THREADS unset. Saved estimators retain their own thread settings (typically n_jobs/thread_count=4); this is not an all-single-thread estimator benchmark. No disk loading, serialization, SHAP, explanations or report generation is inside inference timers. No cold-start latency was measured. No concurrent agent training/tests ran during the supplement; OS background activity was uncontrolled. Earlier controlled inference ran after the earlier long-running jobs finished. Already recorded successor training timers sometimes overlapped other work and are representative elapsed component costs, not an isolated hardware speed leaderboard.

Earlier single-record and BRFSS/Hospital130 batch benchmarks use the first supported records in the first frozen evaluation partition. Prior PIDD/Sylhet batches were only 154/104 records and remain labeled with their actual sizes. The A4 supplement times the first 256 supported PIDD/Sylhet predictor rows in frozen raw order; some were training records for that router. Outcomes do not select the timing inputs, no performance metrics are computed, and no scientific predictions are saved. This is a representative throughput workload, not a new validation population. Only the missing 256-record components/end-to-end calls and calibration application were timed anew. Calibration-only timings use the first input's selected panel on precomputed raw scores. Existing preprocessing/model components use that panel for the whole batch, whereas routed end-to-end calls select each record's panel. Component medians cannot be summed to reconstruct mixed-panel end-to-end latency.

## Main-text-ready table

Final-fit and calibration columns below are SUMS over the completed reduced-schema successor tasks (125 PIDD, 100 Sylhet, five BRFSS, four Hospital130), not fitting times for the original router exemplars. Inference is original fitted-artifact D with one router. Storage is the first-router runtime-panel example, with compressed files saved for byte/hash verification. Model and calibrator columns are independent serializations; prediction triple also contains preprocessing. Values derive from A4_MAIN_TEXT_TABLE.csv / 06_COMPUTATIONAL_COST.csv / A4_COMPONENT_STORAGE_VERIFICATION.csv.

| Cohort | Final fit sum (s) | Calibration sum (s) | Single (ms) | Batch 256 (ms) | Model (MiB) | Calibrator (MiB) | Prediction triple (MiB) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PIDD | 13.0258 | 0.889598 | 2.13562 | 6.27158 | 0.0554867 | 0.000576019 | 0.0569286 |
| Sylhet | 19.0643 | 3.79167 | 28.0335 | 52.9328 | 0.81616 | 0.000576973 | 0.817732 |
| BRFSS | 51.4581 | 3.80137 | 2.14658 | 11.2605 | 0.759795 | 8.86917e-05 | 0.761136 |
| Hospital130 | 14.6965 | 67.0703 | 30.6046 | 45.9091 | 27.1382 | 0.000575066 | 27.1416 |

Suggested accompanying text: Computational costs were separated into hyperparameter search, OOF generation, final preprocessing/model fitting, calibration selection/fitting and warmed prediction. Historical search/final-fit timers were retained; representative component costs and loaded-artifact inference were measured locally. Historical component gaps and execution-environment limits are disclosed. The reported latencies exclude loading and explanations.

## Supplement: historical costs and runner intervals

Training/calibration units are seconds. Historical family rows are sums and per-task distribution summaries; 25 tasks/family in repeated cohorts and one in each holdout. All five simpler/full-model alternatives use the same cohort's recorded workflow and tuning budget; unknown resource contention precludes a controlled hardware speed ranking. Compare within cohort, without assigning current hardware to history.

| Cohort | System | Operation | Tasks | Total (s) | Median (s) | Min (s) | Max (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PIDD | catboost | historical_tuning_seconds | 25 | 1917.82 | 70.9096 | 41.913 | 170.849 |
| PIDD | catboost | historical_fit_seconds | 25 | 6.31412 | 0.197521 | 0.0722435 | 0.762094 |
| PIDD | lightgbm | historical_tuning_seconds | 25 | 2065.69 | 77.4315 | 43.3821 | 154.388 |
| PIDD | lightgbm | historical_fit_seconds | 25 | 6.1893 | 0.23175 | 0.111663 | 0.417961 |
| PIDD | logistic_regression | historical_tuning_seconds | 25 | 35.3986 | 1.24559 | 0.973182 | 2.32185 |
| PIDD | logistic_regression | historical_fit_seconds | 25 | 0.0277399 | 0.00108421 | 0.000792166 | 0.00195687 |
| PIDD | random_forest | historical_tuning_seconds | 25 | 3572.78 | 135.756 | 73.4595 | 246.544 |
| PIDD | random_forest | historical_fit_seconds | 25 | 13.9249 | 0.493975 | 0.215026 | 1.16873 |
| PIDD | xgboost | historical_tuning_seconds | 25 | 1696.98 | 65.9447 | 39.9866 | 108.306 |
| PIDD | xgboost | historical_fit_seconds | 25 | 6.7303 | 0.230475 | 0.105898 | 0.558285 |
| Sylhet | catboost | historical_tuning_seconds | 25 | 5305.06 | 143.344 | 73.1843 | 501.525 |
| Sylhet | catboost | historical_fit_seconds | 25 | 20.376 | 0.427278 | 0.0642854 | 3.42103 |
| Sylhet | lightgbm | historical_tuning_seconds | 25 | 2360.74 | 84.0004 | 45.9474 | 159.192 |
| Sylhet | lightgbm | historical_fit_seconds | 25 | 11.2713 | 0.436052 | 0.17713 | 0.933001 |
| Sylhet | logistic_regression | historical_tuning_seconds | 25 | 36.3614 | 1.3589 | 1.07939 | 2.5434 |
| Sylhet | logistic_regression | historical_fit_seconds | 25 | 0.02643 | 0.00092075 | 0.00065925 | 0.0030265 |
| Sylhet | random_forest | historical_tuning_seconds | 25 | 3259.03 | 123.562 | 65.5287 | 206.555 |
| Sylhet | random_forest | historical_fit_seconds | 25 | 12.073 | 0.463956 | 0.136012 | 0.95276 |
| Sylhet | xgboost | historical_tuning_seconds | 25 | 1580.15 | 56.441 | 31.1179 | 127.881 |
| Sylhet | xgboost | historical_fit_seconds | 25 | 6.84181 | 0.227445 | 0.0821526 | 0.752114 |
| BRFSS | catboost | historical_tuning_seconds | 1 | 2691.6 | 2691.6 | 2691.6 | 2691.6 |
| BRFSS | catboost | historical_fit_seconds | 1 | 14.5375 | 14.5375 | 14.5375 | 14.5375 |
| BRFSS | lightgbm | historical_tuning_seconds | 1 | 3935.03 | 3935.03 | 3935.03 | 3935.03 |
| BRFSS | lightgbm | historical_fit_seconds | 1 | 13.9868 | 13.9868 | 13.9868 | 13.9868 |
| BRFSS | logistic_regression | historical_tuning_seconds | 1 | 459.932 | 459.932 | 459.932 | 459.932 |
| BRFSS | logistic_regression | historical_fit_seconds | 1 | 1.47249 | 1.47249 | 1.47249 | 1.47249 |
| BRFSS | random_forest | historical_tuning_seconds | 1 | 7448.02 | 7448.02 | 7448.02 | 7448.02 |
| BRFSS | random_forest | historical_fit_seconds | 1 | 33.7865 | 33.7865 | 33.7865 | 33.7865 |
| BRFSS | xgboost | historical_tuning_seconds | 1 | 1071.91 | 1071.91 | 1071.91 | 1071.91 |
| BRFSS | xgboost | historical_fit_seconds | 1 | 4.17113 | 4.17113 | 4.17113 | 4.17113 |
| Hospital130 | catboost | historical_tuning_seconds | 1 | 2010.14 | 2010.14 | 2010.14 | 2010.14 |
| Hospital130 | catboost | historical_fit_seconds | 1 | 8.81875 | 8.81875 | 8.81875 | 8.81875 |
| Hospital130 | lightgbm | historical_tuning_seconds | 1 | 1712.86 | 1712.86 | 1712.86 | 1712.86 |
| Hospital130 | lightgbm | historical_fit_seconds | 1 | 5.28229 | 5.28229 | 5.28229 | 5.28229 |
| Hospital130 | logistic_regression | historical_tuning_seconds | 1 | 2676.69 | 2676.69 | 2676.69 | 2676.69 |
| Hospital130 | logistic_regression | historical_fit_seconds | 1 | 13.3604 | 13.3604 | 13.3604 | 13.3604 |
| Hospital130 | random_forest | historical_tuning_seconds | 1 | 18068.2 | 18068.2 | 18068.2 | 18068.2 |
| Hospital130 | random_forest | historical_fit_seconds | 1 | 113.203 | 113.203 | 113.203 | 113.203 |
| Hospital130 | xgboost | historical_tuning_seconds | 1 | 873.964 | 873.964 | 873.964 | 873.964 |
| Hospital130 | xgboost | historical_fit_seconds | 1 | 2.26157 | 2.26157 | 2.26157 | 2.26157 |

| dataset | run_started_utc | run_completed_utc | runner_interval_seconds | classification |
| --- | --- | --- | --- | --- |
| pidd | 2026-09-10T12:57:15.444601+00:00 | 2026-09-10T15:58:04.015690+00:00 | 10848.6 | DERIVABLE FROM VALID RECORDED TIMESTAMPS |
| sylhet | 2026-09-10T13:00:18.849055+00:00 | 2026-09-10T16:57:00.599201+00:00 | 14201.8 | DERIVABLE FROM VALID RECORDED TIMESTAMPS |
| brfss | 2026-09-10T17:18:17.176412+00:00 | 2026-09-10T22:39:24.430312+00:00 | 19267.3 | DERIVABLE FROM VALID RECORDED TIMESTAMPS |
| hospital130 | 2026-09-10T12:58:37.222699+00:00 | 2026-09-10T20:34:46.551750+00:00 | 27369.3 | DERIVABLE FROM VALID RECORDED TIMESTAMPS |

A4_HISTORICAL_TRIAL_TIMING.csv contains every search's 75 trial-duration distributions and timestamp spans, with exact source hashes. These are not added to tuning totals.

## Supplement: completed successor component distributions

| Cohort | Component | Tasks | Total (s) | Median (s) | p05 (s) | p95 (s) | Min (s) | Max (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BRFSS | OOF generation | 5 | 226.896 | 54.0293 | 24.885 | 63.4991 | 24.167 | 65.5176 |
| BRFSS | Calibration selection + fit | 5 | 3.80137 | 0.864689 | 0.590631 | 0.869939 | 0.584321 | 0.871067 |
| BRFSS | Final model fit | 5 | 51.4581 | 12.5269 | 5.7174 | 13.8223 | 5.52069 | 14.0685 |
| BRFSS | Final preprocessing | 5 | 0.739842 | 0.164035 | 0.0706636 | 0.211769 | 0.0564164 | 0.222369 |
| BRFSS | Tuning (none) | 5 | 0 | 0 | 0 | 0 | 0 | 0 |
| Hospital130 | OOF generation | 4 | 67.4783 | 15.5655 | 12.2756 | 23.2893 | 12.0399 | 24.3074 |
| Hospital130 | Calibration selection + fit | 4 | 67.0703 | 18.0113 | 13.4565 | 18.3375 | 12.6716 | 18.3762 |
| Hospital130 | Final model fit | 4 | 14.6965 | 3.12557 | 2.64023 | 5.47601 | 2.58768 | 5.85769 |
| Hospital130 | Final preprocessing | 4 | 0.180575 | 0.0294466 | 0.0146216 | 0.097642 | 0.0123589 | 0.109323 |
| Hospital130 | Tuning (none) | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| PIDD | OOF generation | 125 | 61.3717 | 0.440177 | 0.0806185 | 1.26255 | 0.0611607 | 2.41435 |
| PIDD | Calibration selection + fit | 125 | 0.889598 | 0.00707079 | 0.00627542 | 0.0079534 | 0.00616425 | 0.0135181 |
| PIDD | Final model fit | 125 | 13.0258 | 0.0922327 | 0.0135667 | 0.274936 | 0.00982558 | 0.56584 |
| PIDD | Final preprocessing | 125 | 0.211418 | 0.00170013 | 0.00139682 | 0.00198823 | 0.00132154 | 0.00227704 |
| PIDD | Tuning (none) | 125 | 0 | 0 | 0 | 0 | 0 | 0 |
| Sylhet | OOF generation | 100 | 100.755 | 0.631236 | 0.0598843 | 3.20212 | 0.0452702 | 3.34405 |
| Sylhet | Calibration selection + fit | 100 | 3.79167 | 0.0378008 | 0.0361499 | 0.0402504 | 0.0356701 | 0.0413856 |
| Sylhet | Final model fit | 100 | 19.0643 | 0.133949 | 0.00952635 | 0.595945 | 0.00642108 | 0.619267 |
| Sylhet | Final preprocessing | 100 | 0.169352 | 0.00167813 | 0.00141255 | 0.00206049 | 0.00127992 | 0.002556 |
| Sylhet | Tuning (none) | 100 | 0 | 0 | 0 | 0 | 0 | 0 |

All per-task durations, including panel/family/fold and direct task.json sources, remain in 06_COMPUTATIONAL_COST.csv. Zero tuning is a design fact, not a stopwatch result. OOF and final/calibration component totals cannot reconstruct whole successor wall time because other work and concurrency are outside these timers.

## Supplement: latency distributions

| Cohort | System | Operation | Records | Median (ms) | p05 (ms) | p95 (ms) | Min (ms) | Max (ms) | Environment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PIDD | framework_one_router | routing_eligibility_only | 1 | 1.16846 | 1.14128 | 1.19769 | 1.13717 | 1.20767 | L_prior_local |
| PIDD | framework_first_record_panel | preprocessing_transform | 1 | 0.595688 | 0.57031 | 0.634009 | 0.5675 | 0.638125 | L_prior_local |
| PIDD | framework_first_record_panel | base_model_predict_only | 1 | 0.061354 | 0.0592479 | 0.0732503 | 0.059209 | 0.079583 | L_prior_local |
| PIDD | D_framework_one_router | end_to_end_prediction | 1 | 2.13562 | 2.09263 | 2.19597 | 2.07521 | 2.20404 | L_prior_local |
| PIDD | A_fixed_imputation_one_router | end_to_end_prediction | 1 | 2.12375 | 2.07064 | 2.16737 | 2.063 | 2.18162 | L_prior_local |
| PIDD | D_route_patient | single_record_public_router_API | 1 | 1.0904 | 1.05305 | 1.24447 | 1.04458 | 1.79333 | L_prior_local |
| PIDD | D_25_router_research_ensemble | probability_only_all_available_router_ensemble | 1 | 54.866 | 53.2432 | 55.6917 | 53.0951 | 55.8402 | L_prior_local |
| PIDD | framework_one_router | routing_eligibility_only | 154 | 1.1774 | 1.16102 | 1.23666 | 1.15671 | 1.24613 | L_prior_local |
| PIDD | framework_first_record_panel | preprocessing_transform | 154 | 0.613354 | 0.592937 | 0.650197 | 0.590166 | 0.711709 | L_prior_local |
| PIDD | framework_first_record_panel | base_model_predict_only | 154 | 0.130729 | 0.125785 | 0.175252 | 0.125667 | 0.176875 | L_prior_local |
| PIDD | D_framework_one_router | end_to_end_prediction | 154 | 5.82042 | 5.73631 | 5.97053 | 5.65979 | 6.00908 | L_prior_local |
| PIDD | A_fixed_imputation_one_router | end_to_end_prediction | 154 | 5.39352 | 5.285 | 5.52633 | 5.25654 | 5.82879 | L_prior_local |
| PIDD | retrained_routine_clinic_xgboost | end_to_end_reduced_panel_prediction | 1 | 0.731249 | 0.710746 | 0.801165 | 0.704333 | 0.811417 | L_prior_local |
| PIDD | retrained_routine_clinic_xgboost | end_to_end_reduced_panel_prediction | 154 | 0.982042 | 0.945101 | 1.06197 | 0.939125 | 1.06854 | L_prior_local |
| Sylhet | framework_one_router | routing_eligibility_only | 1 | 0.974271 | 0.949989 | 1.197 | 0.931583 | 1.25642 | L_prior_local |
| Sylhet | framework_first_record_panel | preprocessing_transform | 1 | 0.606813 | 0.592867 | 0.699302 | 0.592708 | 0.705042 | L_prior_local |
| Sylhet | framework_first_record_panel | base_model_predict_only | 1 | 25.5787 | 23.7908 | 26.2321 | 22.2613 | 26.3005 | L_prior_local |
| Sylhet | D_framework_one_router | end_to_end_prediction | 1 | 28.0335 | 26.2938 | 28.5205 | 25.063 | 28.557 | L_prior_local |
| Sylhet | A_fixed_imputation_one_router | end_to_end_prediction | 1 | 27.9805 | 25.0367 | 28.4301 | 24.8617 | 28.7345 | L_prior_local |
| Sylhet | D_route_patient | single_record_public_router_API | 1 | 25.9765 | 24.2232 | 27.4701 | 23.0451 | 27.6423 | L_prior_local |
| Sylhet | D_25_router_research_ensemble | probability_only_all_available_router_ensemble | 1 | 302.48 | 295.379 | 320.081 | 294.477 | 322.25 | L_prior_local |
| Sylhet | framework_one_router | routing_eligibility_only | 104 | 0.979333 | 0.952133 | 1.01224 | 0.950709 | 1.01446 | L_prior_local |
| Sylhet | framework_first_record_panel | preprocessing_transform | 104 | 0.607978 | 0.582721 | 0.635406 | 0.579 | 0.704875 | L_prior_local |
| Sylhet | framework_first_record_panel | base_model_predict_only | 104 | 38.1656 | 25.8777 | 39.1618 | 25.5697 | 39.4573 | L_prior_local |
| Sylhet | D_framework_one_router | end_to_end_prediction | 104 | 40.7209 | 28.4675 | 42.8518 | 27.8352 | 62.0294 | L_prior_local |
| Sylhet | A_fixed_imputation_one_router | end_to_end_prediction | 104 | 39.3849 | 27.894 | 41.3151 | 27.7862 | 41.4867 | L_prior_local |
| Sylhet | retrained_classic_symptoms_random_forest | end_to_end_reduced_panel_prediction | 1 | 25.6556 | 24.8814 | 27.0977 | 24.8575 | 27.318 | L_prior_local |
| Sylhet | retrained_classic_symptoms_random_forest | end_to_end_reduced_panel_prediction | 104 | 26.8016 | 24.599 | 27.0813 | 24.223 | 27.1166 | L_prior_local |
| BRFSS | framework_one_router | routing_eligibility_only | 1 | 1.16131 | 1.14604 | 1.24189 | 1.14433 | 1.56746 | L_prior_local |
| BRFSS | framework_first_record_panel | preprocessing_transform | 1 | 0.642167 | 0.621025 | 0.97315 | 0.617542 | 1.02904 | L_prior_local |
| BRFSS | framework_first_record_panel | base_model_predict_only | 1 | 0.0818335 | 0.0786042 | 0.0961712 | 0.078209 | 0.09625 | L_prior_local |
| BRFSS | D_framework_one_router | end_to_end_prediction | 1 | 2.14658 | 2.10151 | 2.21777 | 2.09688 | 2.23479 | L_prior_local |
| BRFSS | A_fixed_imputation_one_router | end_to_end_prediction | 1 | 2.10675 | 2.08224 | 2.20761 | 2.07737 | 2.21279 | L_prior_local |
| BRFSS | D_route_patient | single_record_public_router_API | 1 | 1.38138 | 1.34719 | 1.47318 | 1.33813 | 1.48533 | L_prior_local |
| BRFSS | D_1_router_research_ensemble | probability_only_all_available_router_ensemble | 1 | 1.41071 | 1.36887 | 1.63799 | 1.35938 | 1.66083 | L_prior_local |
| BRFSS | framework_one_router | routing_eligibility_only | 256 | 1.218 | 1.20338 | 1.27593 | 1.20271 | 1.2865 | L_prior_local |
| BRFSS | framework_first_record_panel | preprocessing_transform | 256 | 0.676084 | 0.654202 | 0.715589 | 0.654084 | 0.746584 | L_prior_local |
| BRFSS | framework_first_record_panel | base_model_predict_only | 256 | 0.3075 | 0.299081 | 0.334206 | 0.299042 | 0.338917 | L_prior_local |
| BRFSS | D_framework_one_router | end_to_end_prediction | 256 | 11.2605 | 10.9802 | 11.872 | 10.9618 | 12.427 | L_prior_local |
| BRFSS | A_fixed_imputation_one_router | end_to_end_prediction | 256 | 9.98885 | 9.78743 | 10.0842 | 9.77179 | 10.0918 | L_prior_local |
| BRFSS | retrained_demographics_health_xgboost | end_to_end_reduced_panel_prediction | 1 | 0.714646 | 0.701367 | 0.807098 | 0.696459 | 0.826375 | L_prior_local |
| BRFSS | retrained_demographics_health_xgboost | end_to_end_reduced_panel_prediction | 256 | 1.32542 | 1.29601 | 1.42592 | 1.29388 | 1.43712 | L_prior_local |
| Hospital130 | framework_one_router | routing_eligibility_only | 1 | 0.617396 | 0.611185 | 0.689512 | 0.61075 | 0.695292 | L_prior_local |
| Hospital130 | framework_first_record_panel | preprocessing_transform | 1 | 3.02358 | 2.97035 | 3.12337 | 2.96508 | 3.16521 | L_prior_local |
| Hospital130 | framework_first_record_panel | base_model_predict_only | 1 | 25.1118 | 24.1734 | 26.2594 | 22.6557 | 26.2877 | L_prior_local |
| Hospital130 | D_framework_one_router | end_to_end_prediction | 1 | 30.6046 | 27.4706 | 31.3642 | 26.7354 | 31.4101 | L_prior_local |
| Hospital130 | A_fixed_imputation_one_router | end_to_end_prediction | 1 | 4.90165 | 4.79642 | 5.2698 | 4.76958 | 5.68408 | L_prior_local |
| Hospital130 | D_route_patient | single_record_public_router_API | 1 | 31.4687 | 28.8332 | 42.8685 | 28.1488 | 44.6627 | L_prior_local |
| Hospital130 | D_1_router_research_ensemble | probability_only_all_available_router_ensemble | 1 | 31.3339 | 29.5003 | 31.6883 | 29.3308 | 31.9935 | L_prior_local |
| Hospital130 | framework_one_router | routing_eligibility_only | 256 | 0.841333 | 0.825021 | 0.894108 | 0.82225 | 0.934167 | L_prior_local |
| Hospital130 | framework_first_record_panel | preprocessing_transform | 256 | 4.81892 | 4.75341 | 4.8932 | 4.71296 | 5.07521 | L_prior_local |
| Hospital130 | framework_first_record_panel | base_model_predict_only | 256 | 38.5853 | 37.4619 | 38.775 | 36.3165 | 38.7764 | L_prior_local |
| Hospital130 | D_framework_one_router | end_to_end_prediction | 256 | 45.9091 | 43.2896 | 48.0144 | 43.1095 | 54.5765 | L_prior_local |
| Hospital130 | A_fixed_imputation_one_router | end_to_end_prediction | 256 | 8.95577 | 8.79611 | 9.75549 | 8.76575 | 9.84396 | L_prior_local |
| Hospital130 | retrained_prior_utilization_random_forest | end_to_end_reduced_panel_prediction | 1 | 26.2055 | 23.5999 | 27.3379 | 23.2051 | 27.4532 | L_prior_local |
| Hospital130 | retrained_prior_utilization_random_forest | end_to_end_reduced_panel_prediction | 256 | 39.7333 | 37.7567 | 40.8815 | 36.9066 | 51.8855 | L_prior_local |
| PIDD | framework_first_record_panel | calibration_application_only | 1 | 0.044708 | 0.0424979 | 0.0546271 | 0.042459 | 0.054667 | N_A4_supplement |
| PIDD | framework_first_record_panel | calibration_application_only | 256 | 0.0445 | 0.0435223 | 0.0502351 | 0.043167 | 0.053125 | N_A4_supplement |
| PIDD | framework_one_router | routing_eligibility_only | 256 | 1.196 | 1.15032 | 1.48538 | 1.14775 | 1.94542 | N_A4_supplement |
| PIDD | framework_first_record_panel | preprocessing_transform | 256 | 0.634542 | 0.575998 | 0.783488 | 0.573584 | 0.910708 | N_A4_supplement |
| PIDD | framework_first_record_panel | base_model_predict_only | 256 | 0.168042 | 0.159256 | 0.240196 | 0.158583 | 0.254208 | N_A4_supplement |
| PIDD | D_framework_one_router | end_to_end_prediction | 256 | 6.27158 | 5.81317 | 7.04918 | 5.81237 | 7.22529 | N_A4_supplement |
| PIDD | A_fixed_imputation_one_router | end_to_end_prediction | 256 | 5.98471 | 5.4348 | 6.58569 | 5.32892 | 6.78483 | N_A4_supplement |
| Sylhet | framework_first_record_panel | calibration_application_only | 1 | 0.0450625 | 0.0417899 | 0.0521869 | 0.04175 | 0.054959 | N_A4_supplement |
| Sylhet | framework_first_record_panel | calibration_application_only | 256 | 0.046687 | 0.0438952 | 0.0579399 | 0.0435 | 0.06075 | N_A4_supplement |
| Sylhet | framework_one_router | routing_eligibility_only | 256 | 1.01604 | 0.974998 | 1.28126 | 0.971791 | 1.62733 | N_A4_supplement |
| Sylhet | framework_first_record_panel | preprocessing_transform | 256 | 0.724854 | 0.608609 | 1.01218 | 0.6075 | 1.07571 | N_A4_supplement |
| Sylhet | framework_first_record_panel | base_model_predict_only | 256 | 48.7916 | 38.6099 | 51.3471 | 38.4074 | 51.6977 | N_A4_supplement |
| Sylhet | D_framework_one_router | end_to_end_prediction | 256 | 52.9328 | 41.7578 | 54.76 | 40.4603 | 54.8848 | N_A4_supplement |
| Sylhet | A_fixed_imputation_one_router | end_to_end_prediction | 256 | 53.373 | 50.2443 | 54.6744 | 41.1883 | 55.3503 | N_A4_supplement |
| BRFSS | framework_first_record_panel | calibration_application_only | 1 | 0.001542 | 0.001458 | 0.00184135 | 0.001458 | 0.002 | N_A4_supplement |
| BRFSS | framework_first_record_panel | calibration_application_only | 256 | 0.001688 | 0.00154195 | 0.0023351 | 0.001541 | 0.002375 | N_A4_supplement |
| Hospital130 | framework_first_record_panel | calibration_application_only | 1 | 0.043417 | 0.0421229 | 0.0502923 | 0.042083 | 0.056625 | N_A4_supplement |
| Hospital130 | framework_first_record_panel | calibration_application_only | 256 | 0.0496875 | 0.0458858 | 0.0792861 | 0.045292 | 0.10925 | N_A4_supplement |

The n=154/104 historical local benchmark rows remain alongside the new n=256 rows. The public single-record API and all-router research ensemble are separate workloads. Ensemble probability-only cost does not equal five OOF probabilities or a patient report with SHAP.

## Comparison with simpler alternatives

| Cohort | Records | A median (ms) | D median (ms) | D/A median ratio | Environment |
| --- | --- | --- | --- | --- | --- |
| PIDD | 1 | 2.12375 | 2.13562 | 1.00559 | L_prior_local |
| PIDD | 256 | 5.98471 | 6.27158 | 1.04793 | N_A4_supplement |
| Sylhet | 1 | 27.9805 | 28.0335 | 1.00189 | L_prior_local |
| Sylhet | 256 | 53.373 | 52.9328 | 0.991752 | N_A4_supplement |
| BRFSS | 1 | 2.10675 | 2.14658 | 1.01891 | L_prior_local |
| BRFSS | 256 | 9.98885 | 11.2605 | 1.12731 | L_prior_local |
| Hospital130 | 1 | 4.90165 | 30.6046 | 6.24374 | L_prior_local |
| Hospital130 | 256 | 8.95577 | 45.9091 | 5.1262 | L_prior_local |

A is the fixed-imputation robust-family/full-calibrator comparator; D includes scenario selection and panel mapping. Each ratio is a descriptive ratio of medians on matched inputs/environment, not a paired significance test. All five original families' training and storage are also available; Logistic Regression offers a simpler fitted alternative, but no new Logistic Regression latency or predictive comparison was run for A4.

## Storage requirements

All storage uses MiB = bytes/1,048,576 (not decimal MB). Original file sizes were verified by file stat; model, preprocessing, calibrator and prediction-triple sizes use controlled independent joblib compress=3 serialization. Compression is non-additive: the triple is serialized jointly, not obtained by summing compressed component sizes. A4_STORAGE_DETAILS.csv covers every selected original panel/fold configuration, all five full-model alternatives and every already fitted reduced panel. A selected-runtime payload stores one model/preprocessor per distinct fold-family and only the mappings needed by D; forced-panel prediction parity was verified for every panel (maximum probability difference 1.11e-16 from parallel arithmetic; decisions/metadata exact). These private storage-only payloads are saved with byte counts and SHA-256, excluding alternative systems, SHAP background/reference data and unused metadata; they do not replace preserved routers. All-router payload totals sum those saved payload files; distinct fitted fold-family keys are counted separately, with no shared model counted again per panel. The actual complete-router collection additionally retains four families/all mappings/metadata. The original archive sum includes all five benchmark families plus duplicated model objects in routers and is not a deployment requirement. The independent reduced collection excludes the reused full controls; a combined original-plus-reduced deployment would need both collections. Serialized bytes are not resident/peak RAM. Earlier in-memory whole-router and some component compressed sizes were not reproduced exactly in a fresh process; warming did not explain the whole-router differences. The cause is unestablished. Legacy observations remain in 06; A4_STORAGE_VERIFICATION.csv and A4_COMPONENT_STORAGE_VERIFICATION.csv disclose all differences. Publication example/component sizes and deployment totals use saved, hash-verified compressed files. Other configuration serializations describe their captured object state; no cross-process byte-stability claim is made for arbitrary reserialization.

| Cohort | Storage scope | Repeat | Fold | Distinct models | Combined (MiB) |
| --- | --- | --- | --- | --- | --- |
| PIDD | selected_runtime_one_router_payload | 0 | 0 | 2 | 0.113179 |
| PIDD | selected_runtime_all_routers_payload | NA | NA | 55 | 7.94754 |
| PIDD | actual_complete_router_collection | NA | NA | 100 | 83.3114 |
| PIDD | independently_retrained_reduced_collection_actual | NA | NA | 125 | 11.9831 |
| Sylhet | selected_runtime_one_router_payload | 0 | 0 | 1 | 0.886891 |
| Sylhet | selected_runtime_all_routers_payload | NA | NA | 62 | 19.5205 |
| Sylhet | actual_complete_router_collection | NA | NA | 100 | 117.06 |
| Sylhet | independently_retrained_reduced_collection_actual | NA | NA | 100 | 20.5263 |
| BRFSS | selected_runtime_one_router_payload | 0 | 0 | 3 | 3.49529 |
| BRFSS | selected_runtime_all_routers_payload | NA | NA | 3 | 3.49529 |
| BRFSS | actual_complete_router_collection | NA | NA | 4 | 592.202 |
| BRFSS | independently_retrained_reduced_collection_actual | NA | NA | 5 | 5.32166 |
| Hospital130 | selected_runtime_one_router_payload | 0 | 0 | 3 | 29.345 |
| Hospital130 | selected_runtime_all_routers_payload | NA | NA | 3 | 29.345 |
| Hospital130 | actual_complete_router_collection | NA | NA | 4 | 101.787 |
| Hospital130 | independently_retrained_reduced_collection_actual | NA | NA | 4 | 60.379 |

| dataset | legacy_recorded_bytes | current_loaded_bytes | current_warmed_bytes | actual_file_bytes | warmed_difference_bytes |
| --- | --- | --- | --- | --- | --- |
| pidd | 516304 | 516322 | 516322 | 1859395 | 18 |
| sylhet | 1099306 | 1093338 | 1093338 | 3615075 | -5968 |
| brfss | 173653809 | 173379060 | 173379060 | 620968419 | -274749 |
| hospital130 | 31677965 | 31172767 | 31172767 | 106731435 | -505198 |

| dataset | operation | legacy_recorded_bytes | current_saved_bytes | difference_bytes |
| --- | --- | --- | --- | --- |
| pidd | model_serialized_bytes | 58182 | 58182 | 0 |
| pidd | preprocessor_serialized_bytes | 1065 | 1065 | 0 |
| pidd | calibrator_serialized_bytes | 604 | 604 | 0 |
| pidd | model_preprocessor_calibrator_serialized_bytes | 59694 | 59694 | 0 |
| sylhet | model_serialized_bytes | 859666 | 855806 | -3860 |
| sylhet | preprocessor_serialized_bytes | 1121 | 1121 | 0 |
| sylhet | calibrator_serialized_bytes | 605 | 605 | 0 |
| sylhet | model_preprocessor_calibrator_serialized_bytes | 861305 | 857454 | -3851 |
| brfss | model_serialized_bytes | 796703 | 796703 | 0 |
| brfss | preprocessor_serialized_bytes | 1225 | 1225 | 0 |
| brfss | calibrator_serialized_bytes | 93 | 93 | 0 |
| brfss | model_preprocessor_calibrator_serialized_bytes | 798109 | 798109 | 0 |
| hospital130 | model_serialized_bytes | 29796693 | 28456485 | -1340208 |
| hospital130 | preprocessor_serialized_bytes | 3202 | 3202 | 0 |
| hospital130 | calibrator_serialized_bytes | 603 | 603 | 0 |
| hospital130 | model_preprocessor_calibrator_serialized_bytes | 29800282 | 28459981 | -1340301 |

Per-configuration preprocessing/model/calibrator/triple bytes and MiB conversions are supplied by A4_STORAGE_DETAILS.csv and 06_COMPUTATIONAL_COST.csv; actual full/reduced bundle bytes are separate columns. Panel-config triples must not be summed to estimate router storage because they repeat shared models.

## Hardware and software

Observed local benchmark hardware: Apple M2 Pro, Mac14,9 MacBook Pro, 10 logical CPUs (hardware processor descriptor proc 10:0:6:4), installed RAM 16 GB (17179869184 bytes); macOS-27.0-arm64-arm-64bit, arm64. CPU only. Python 3.12.0 (v3.12.0:0fb18b02c8, Oct  2 2023, 09:45:56) [Clang 13.0.0 (clang-1300.0.29.30)]. Installed dependency versions: catboost 1.2.10, joblib 1.5.3, lightgbm 4.7.0, numpy 2.5.2, optuna 4.9.0, pandas 3.0.5, scikit-learn 1.9.0, scipy 1.18.0, threadpoolctl 3.6.0, xgboost 3.4.1. BENCHMARK_ENVIRONMENT.json retains the earlier observed environment; A4_BENCHMARK_ENVIRONMENT.json separately captures this supplement. Historical metadata records model_n_jobs=4 and a requirements-lock hash matching the retained lock, which declares these core package versions. Historical CPU/RAM/OS/interpreter, installed-version snapshot, free RAM, peak process RAM, accelerator telemetry and concurrency are unavailable. Current hardware must not be attributed to historical training. No GPU timing claim is made for history.

## Limitations and status

A4 reporting completeness: COMPLETE. Historical component timing reconstruction: PARTIAL. Exact historical training replay: BLOCKED (original source fingerprint unavailable; HISTORICAL_SOURCE_SEARCH.json). Historical timers remain evidence of recorded costs, not a promise that durations can be reproduced. Metadata start/end differences recover only the recorded runner invocation interval, including other runner work; they do not cover separately invoked routing, explanation or publication stages and are not total pipeline time. No missing component was calculated by subtraction. Trial CSV timestamps are timezone-naive as saved; within-file durations were checked against their duration column without assuming a timezone conversion. Trial-objective sums are diagnostic subsets of tuning, not additional compute to add to tuning. Separate historical calibration/OOF/preprocessing/inference times, entire-pipeline runtime and peak RAM remain unavailable. The small-cohort 256 workloads and first-panel component examples have the limits stated above. Only 20 serial repetitions describe local variability; no independent-run uncertainty, deployment capacity, energy cost, optimized panel-model search or clinical validation is claimed. No further model training is needed for A4.

## Numerical provenance and reproduction

Every 06 row has result_key, source and source_sha256. Original timers point to authoritative historical CSVs; successor timers point to task.json; L timings point to benchmark_raw_samples.json; N timings point to a4_reporting_v2/supplement_raw_samples.json; storage points to A4_STORAGE_DETAILS.csv with fitted-object file hashes, and canonical example files to A4_COMPONENT_STORAGE_VERIFICATION.csv. A4_MAIN_TEXT_TABLE.csv, A4_TRAINING_SUMMARY.csv, A4_INFERENCE_SUMMARY.csv, A4_HISTORICAL_MODEL_COSTS.csv and A4_COMPARATOR_COSTS.csv are deterministic views of 06. Historical intervals/trial summaries point to metadata/trial CSVs. ANALYSIS_SOURCE_MAP.csv maps every cost and derived-table row to its command, source, split/protocol and output hash. See REPRODUCE.md for read-only table reconstruction, verification and optional separately versioned timing collection. Existing measurements are retained by default; re-timing is not needed to reproduce these tables.
