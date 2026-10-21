# Reduced-schema versus masked-input models

Matched family and frozen full-schema hyperparameters; preprocessing/model/calibration refitted only in original training partitions. Full controls and all paired effects remain in the supplement.

Display values use six significant figures; the adjacent CSV retains the exact source strings.

| dataset | panel | comparison_arm | evaluation_n | auroc | average_precision | brier_score | log_loss |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pidd | core_metabolic | masked | 768 | 0.837396 | 0.719008 | 0.154206 | 0.468551 |
| pidd | core_metabolic | retrained | 768 | 0.843052 | 0.727394 | 0.151766 | 0.462554 |
| pidd | minimal_glucose_age | masked | 768 | 0.808806 | 0.675465 | 0.165547 | 0.500371 |
| pidd | minimal_glucose_age | retrained | 768 | 0.815925 | 0.687615 | 0.162489 | 0.493198 |
| pidd | no_insulin_or_skinfold | masked | 768 | 0.839672 | 0.724067 | 0.153187 | 0.465729 |
| pidd | no_insulin_or_skinfold | retrained | 768 | 0.840179 | 0.718387 | 0.152927 | 0.465244 |
| pidd | non_laboratory | masked | 768 | 0.759806 | 0.597113 | 0.185211 | 0.545001 |
| pidd | non_laboratory | retrained | 768 | 0.763 | 0.607668 | 0.183864 | 0.538941 |
| pidd | routine_clinic | masked | 768 | 0.836239 | 0.708952 | 0.154882 | 0.471572 |
| pidd | routine_clinic | retrained | 768 | 0.837284 | 0.704025 | 0.154944 | 0.47129 |
| sylhet | classic_symptoms | masked | 520 | 0.893672 | 0.945265 | 0.111703 | 0.36098 |
| sylhet | classic_symptoms | retrained | 520 | 0.888797 | 0.943486 | 0.12163 | 0.380008 |
| sylhet | core_questionnaire | masked | 520 | 0.941844 | 0.965925 | 0.0920591 | 0.29756 |
| sylhet | core_questionnaire | retrained | 520 | 0.950047 | 0.971611 | 0.0832441 | 0.273905 |
| sylhet | core_symptoms | masked | 520 | 0.901 | 0.947693 | 0.112168 | 0.364079 |
| sylhet | core_symptoms | retrained | 520 | 0.906625 | 0.952416 | 0.111184 | 0.350835 |
| sylhet | minimal_polyuria_polydipsia | masked | 520 | 0.881531 | 0.939315 | 0.11126 | 0.359728 |
| sylhet | minimal_polyuria_polydipsia | retrained | 520 | 0.875281 | 0.935382 | 0.111002 | 0.347172 |
| brfss | cardiometabolic_health | masked | 85872 | 0.8372 | 0.427679 | 0.0925628 | 0.299714 |
| brfss | cardiometabolic_health | retrained | 85872 | 0.838183 | 0.434573 | 0.0923953 | 0.299004 |
| brfss | demographics_health | masked | 85872 | 0.78492 | 0.315756 | 0.101611 | 0.329213 |
| brfss | demographics_health | retrained | 85872 | 0.79099 | 0.331789 | 0.100669 | 0.326261 |
| brfss | health_status | masked | 85872 | 0.828762 | 0.412074 | 0.094312 | 0.305413 |
| brfss | health_status | retrained | 85872 | 0.830067 | 0.415108 | 0.0940272 | 0.304449 |
| brfss | minimal_general_health_age | masked | 85872 | 0.782089 | 0.310589 | 0.101876 | 0.331092 |
| brfss | minimal_general_health_age | retrained | 85872 | 0.784476 | 0.315078 | 0.101382 | 0.329172 |
| brfss | routine_survey | masked | 85872 | 0.839062 | 0.435128 | 0.0923321 | 0.298758 |
| brfss | routine_survey | retrained | 85872 | 0.839939 | 0.437278 | 0.0921235 | 0.297883 |
| hospital130 | admission_clinical | masked | 19868 | 0.592593 | 0.167011 | 0.0991863 | 0.348617 |
| hospital130 | admission_clinical | retrained | 19868 | 0.62153 | 0.183953 | 0.0985085 | 0.344164 |
| hospital130 | encounter_utilization | masked | 19868 | 0.62714 | 0.187402 | 0.0983152 | 0.343259 |
| hospital130 | encounter_utilization | retrained | 19868 | 0.623222 | 0.175915 | 0.098707 | 0.344465 |
| hospital130 | minimal_inpatient_history | masked | 19868 | 0.622256 | 0.174378 | 0.0986079 | 0.344514 |
| hospital130 | minimal_inpatient_history | retrained | 19868 | 0.624729 | 0.176143 | 0.0983887 | 0.343481 |
| hospital130 | prior_utilization | masked | 19868 | 0.629223 | 0.185896 | 0.0983094 | 0.343114 |
| hospital130 | prior_utilization | retrained | 19868 | 0.613188 | 0.172381 | 0.0988301 | 0.3455 |
