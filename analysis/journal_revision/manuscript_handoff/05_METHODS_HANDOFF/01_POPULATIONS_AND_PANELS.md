# Endpoints, populations and availability panels

Authoritative definitions are config/authoritative_studies.yaml, results/final_publication/provenance/frozen_protocol.yaml, loaders/settings and config/availability_scenarios.yaml. PANEL_DEFINITIONS.csv/.md beside this folder export every predictor literally and in configured order; the supplementary PANEL_DEFINITIONS.csv is an exact copy. Use that list in the manuscript rather than inventing broader clinical panel names or cross-cohort mappings.

| Cohort | Endpoint | Source eligible population | Evaluation population/events | Validation and resampling |
| --- | --- | --- | --- | --- |
| PIDD | diabetes_positive_label | 768 records / 268 positives | 768 / 268 | Five repeats × five outer stratified folds; five inner folds; participant bootstrap |
| Sylhet | early_stage_diabetes_positive_label | 520 records / 320 positives | 520 / 320 | Five repeats × five outer grouped folds; identical full-predictor-profile groups; group-preserving inner folds/bootstrap |
| BRFSS 2015 | self_reported_diagnosed_diabetes | 429,360 target-valid respondents / 57,256 positives | Historical 20% partition: 85,872 / 11,451; runtime supported 84,632 / 11,316 | Seed-42 80/20 internal partition with five development folds; individual bootstrap |
| Hospital130 | readmission_within_30_days | 99,343 eligible encounters / 11,314 positives after prespecified exclusions | Historical patient-separated evaluation partition: 19,868 / 2,262 | Seed-42 grouped 80/20 internal partition with five development folds; patient-cluster bootstrap |

Population sources: frozen_dataset_characteristics.csv, frozen_routing_fallback_performance.csv and 02_ROUTING_DISTRIBUTION.csv in the supplement; frozen protocol defines splits and exclusions. PIDD/Sylhet evaluation contains one held-out score per repeat/record, not 25 independently held-out scores per record. Outcomes and historical partitions were accessed during development; these are internal-validation results, not untouched independent tests.

The 22 prespecified panels comprise PIDD 6, Sylhet 5, BRFSS 6 and Hospital130 5. Runtime requires every declared panel predictor to be observed after loading. PIDD implausible zeros become missing under retained rules. Forced-panel stress masks excluded predictors and permits training-fitted imputation; runtime instead requires a fully supported panel. Equal-size panels follow descending (predictor count, full flag, lexical name), as implemented in routing/inference.py and routing/policy_evaluator.py. No new panel or grouping definition was selected using evaluation outcomes.

Hospital130 is 30-day readmission among eligible diabetes-related hospital encounters. It is not diabetes detection. Cohort endpoints, predictions and uncertainties are never pooled. The historical frozen protocol still names the earlier journal/title; submission metadata is an author decision and no protocol edit was made.
