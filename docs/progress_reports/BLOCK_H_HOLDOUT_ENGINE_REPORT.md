# Block H Checkpoint: Development-Locked Holdout Engine

## Status

The separate holdout workflow for BRFSS and Hospital130 is implemented and
verified across Random Forest, XGBoost, LightGBM, and CatBoost. It is not a
modified form of the small-cohort nested-CV runner: model tuning, calibration,
threshold selection, and champion selection are completed from development
folds before test prediction begins.

The current studies use the smoke profile and therefore verify execution only.
They are not paper estimates.

## Evaluation contract

1. Generate one immutable 80/20 holdout split.
2. For Hospital130, keep all encounters from the same patient on one side of
   every split.
3. Use the five preassigned development folds for hyperparameter optimization
   and cross-fitted probabilities.
4. Select calibration by cross-fitted Brier score and log loss.
5. Select fixed, Youden, and sensitivity-constrained thresholds using only
   development predictions.
6. Select a development champion by Brier score, then log loss and average
   precision.
7. Only after those choices are locked, predict the held-out test rows once.
8. Use paired patient-level bootstrap comparisons for BRFSS and paired
   patient-cluster bootstrap comparisons for Hospital130, followed by Holm
   multiplicity adjustment.

An unlocked non-smoke experiment is rejected. The final test run remains
disabled until the protocol is frozen and `locked: true` is set deliberately.

## Hospital130 cohort correction

The Hospital130 endpoint is 30-day readmission among encounters involving
patients with diabetes; it is not diabetes detection. The [UCI data
dictionary](https://archive.ics.uci.edu/dataset/296/diabetes%2B130-us-hospitals%2Bfor-years%2B1999-2008)
describes `discharge_disposition_id` as a categorical identifier that includes
expired dispositions. Consistent with published readmission preprocessing,
death and hospice discharge codes 11, 13, 14, 19, 20, and 21 are excluded because
ordinary post-discharge readmission is not an applicable outcome for those
encounters ([Sattar et al., 2022](https://www.mdpi.com/2078-2489/13/9/436)).

The corrected cohort contains:

- 101,766 raw encounters.
- 2,423 death/hospice encounters excluded.
- 99,343 retained encounters.
- 69,990 patient groups.
- 11.39% positive 30-day readmission prevalence.

Admission type, discharge disposition, and admission source are now one-hot
encoded categorical identifiers instead of being treated as continuous values.

## Four-model smoke results

Each smoke study uses 10,000 development and 10,000 test rows, two tuning trials,
three development folds, and 50 bootstrap resamples. These values are deliberately
too small for final inference.

### BRFSS diagnosed-diabetes screening

Study: `brfss_smoke_holdout_1f1344dceb63`

| Model | AUROC | Average precision | Brier | Log loss |
|---|---:|---:|---:|---:|
| XGBoost | 0.8318 | 0.4221 | **0.0935** | 0.3044 |
| CatBoost | 0.8308 | 0.4199 | 0.0936 | **0.3039** |
| Random Forest | 0.8257 | 0.4148 | 0.0940 | 0.3073 |
| LightGBM | 0.8135 | 0.3936 | 0.0963 | 0.3142 |

CatBoost was selected from development data. XGBoost was marginally higher on
sampled-test AP, demonstrating why the test result must not retroactively select
the model. No pairwise difference was Holm-significant in the smoke run.

At the development-selected sensitivity thresholds, sampled-test sensitivity
ranged from 0.761 to 0.798 and specificity from 0.678 to 0.732. These operating
points are more informative than a universal 0.5 cutoff for this low-prevalence
screening endpoint.

### Hospital130 30-day readmission

Corrected study: `hospital130_smoke_holdout_6640beff7a08`

| Model | AUROC | Average precision | Brier | Log loss |
|---|---:|---:|---:|---:|
| XGBoost | **0.6589** | **0.2065** | **0.0973** | **0.3382** |
| Random Forest | 0.6584 | 0.2040 | 0.0973 | 0.3383 |
| CatBoost | 0.6516 | 0.2003 | 0.0976 | 0.3396 |
| LightGBM | 0.6334 | 0.1874 | 0.0984 | 0.3430 |

XGBoost was selected from development data and also narrowly led the sampled
test metrics. No pairwise difference was Holm-significant.

At 0.5, sensitivity was approximately zero because calibrated probabilities
reflect an 11.4% event prevalence. Development-selected Youden thresholds
produced sensitivity 0.566–0.671 and specificity 0.559–0.634; the 0.80-sensitivity
policy produced sensitivity 0.809–0.860 with specificity 0.273–0.378. This is a
useful empirical demonstration that probability quality and operating policy
must be reported separately.

## Held-out SHAP

The holdout explanation command uses development rows only for the background
sample and held-out test rows only for reported values. Every explanation passed
the `1e-4` additivity requirement.

- BRFSS: 500 test rows per model; leading original variables include general
  health, age, BMI, high blood pressure, and high cholesterol.
- Hospital130: 200 test encounters per model; previous inpatient utilization is
  consistently prominent, with discharge disposition and utilization/care
  variables also important.
- Transformed category levels and grouped source-variable importance are both
  retained; the grouped 46-variable table is the primary Hospital130 view.
- Fold-stability is marked unavailable for a single locked test rather than
  estimated from nonexistent repeated test folds.

## Verification

- 29 automated tests plus 5 model-adapter subtests pass.
- Saved BRFSS and Hospital130 bundles reproduce recorded calibrated
  probabilities to less than `1e-15` absolute error.
- Hospital130 confidence intervals and paired comparisons record `cluster` as
  the resampling unit.
- Unsafe category text in plot filenames is sanitized and covered by a
  regression test.
- BRFSS summary SHA-256:
  `e12f3b99f3bb409282d1b640d318959fb431e1ce7abcf1d65eebd114378632c1`.
- Corrected Hospital130 summary SHA-256:
  `debe1233c92bfbb62359f6ebbde8e75ac7fba42c3ce6611b712e00680809d2ab`.
- Corrected Hospital130 test-prediction SHA-256:
  `9599a2a1a9b8c7148873316008fc8a025faf2df8b2e5ba5a391621161b04c1da`.
- Source-tree SHA-256 after verification:
  `a259e84944a874e803661f7d1573d496db9b2de91ab2f040b4df6f35a9ef68cb`.

## Publication decision

The holdout architecture is ready, but neither smoke table is publishable.
Before the single locked final run, complete the feature-availability protocol,
subgroup/fairness analyses, final sample-size-aware compute plan, and manuscript
statistical-analysis section. Then freeze configuration and source hashes.
