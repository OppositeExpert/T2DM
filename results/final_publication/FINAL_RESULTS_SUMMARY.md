# Final Results Summary

**Protocol:** `t2dm-final-internal-validation-v1`

**Evidence:** finalized prespecified internal validation. No dataset is described as an untouched independent final test.

PIDD, Sylhet, and BRFSS are separate diabetes screening/status cohorts. Hospital130 is a separate 30-day-readmission endpoint. Probabilities and rankings are not pooled across cohorts.

## Dataset-specific fallback-policy results

| Dataset | Endpoint | Coverage | AUROC | AP | Brier |
|---|---|---:|---:|---:|---:|
| pidd | diabetes_positive_label | 1.0000 | 0.8369 | 0.7072 | 0.1549 |
| sylhet | early_stage_diabetes_positive_label | 1.0000 | 0.9726 | 0.9841 | 0.0603 |
| brfss | self_reported_diagnosed_diabetes | 0.9856 | 0.8359 | 0.4297 | 0.0931 |
| hospital130 | readmission_within_30_days | 1.0000 | 0.6271 | 0.1874 | 0.0983 |

## Model-family switching

Dynamic model-family switching did not establish multiplicity-corrected superiority over the robust fixed comparators. Numerical rankings are reported separately from statistical support.

SHAP summaries are associational explanations of model output, not causal effects. Decision-curve estimates are retrospective and do not establish clinical utility.
