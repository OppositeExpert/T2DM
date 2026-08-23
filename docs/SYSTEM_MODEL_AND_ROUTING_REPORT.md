# Multi-Dataset Diabetes Prediction and Routing System

## 1. Purpose and current status

This pipeline accepts partially available patient attributes, identifies which dataset-specific prediction panels can use them, and returns a calibrated probability percentage from one eligible expert. It supports PIDD, Sylhet, BRFSS, and Hospital130 artifacts. PIDD, Sylhet, and BRFSS concern diabetes-related labels; Hospital130 predicts 30-day hospital readmission and is therefore kept as a separate endpoint.

The implementation is a research-validation system, not a diagnostic device. The current PIDD and Sylhet results are development pilots, while BRFSS and Hospital130 are smoke-test holdouts. No current result is marked publication-claim eligible or ready for clinical use.

## 2. Datasets, targets, and evidence level

| Dataset | Target represented by the percentage | Current evidence |
|---|---|---|
| PIDD | Positive diabetes label in the Pima cohort | Five-fold development pilot |
| Sylhet | Positive early-stage diabetes/symptom label | Five-fold grouped development pilot |
| BRFSS | Survey-recorded diabetes label | 10,000-row smoke holdout |
| Hospital130 | Readmission within 30 days | 10,000-row smoke holdout; separate task |

The percentage estimates the label defined by the selected dataset. It does **not** yet estimate future lifetime risk or the age at which diabetes will develop.

## 3. Models and their roles

The benchmark evaluates Logistic Regression, Random Forest, XGBoost, LightGBM, and CatBoost. Logistic Regression is the interpretable baseline. The four tree models form the availability-routing model bank because they can capture nonlinear effects and interactions. The system does not assume that one algorithm is universally best: each supported feature panel is assigned the model with the best inner-development Brier score, with log loss and average precision used as tie-breakers.

Probabilities are calibrated using training/development data only. Model fitting, preprocessing, calibration, threshold selection, and model choice are isolated from the corresponding evaluation fold or locked test set to reduce leakage.

## 4. Headline full-input results

AUROC measures ranking discrimination, average precision (AP) emphasizes positive-case retrieval, and Brier score and log loss assess probability quality; lower is better for the last two. Values below are calibrated fixed-threshold study summaries. They should not be compared directly across datasets because the cohorts, prevalence, and endpoints differ.

| Dataset | Model | AUROC | AP | Brier | Log loss |
|---|---|---:|---:|---:|---:|
| PIDD | CatBoost | **0.8404** | 0.7205 | **0.1541** | **0.4688** |
| PIDD | XGBoost | 0.8389 | **0.7275** | 0.1547 | 0.4693 |
| PIDD | Logistic Regression | 0.8375 | 0.7258 | 0.1563 | 0.4775 |
| PIDD | Random Forest | 0.8370 | 0.7086 | 0.1558 | 0.4736 |
| PIDD | LightGBM | 0.8352 | 0.7168 | 0.1553 | 0.4719 |
| Sylhet | CatBoost | **0.9709** | **0.9848** | **0.0642** | **0.2093** |
| Sylhet | LightGBM | 0.9642 | 0.9808 | 0.0701 | 0.2373 |
| Sylhet | XGBoost | 0.9621 | 0.9787 | 0.0800 | 0.2665 |
| Sylhet | Random Forest | 0.9614 | 0.9794 | 0.0759 | 0.2518 |
| Sylhet | Logistic Regression | 0.9576 | 0.9777 | 0.0871 | 0.3026 |
| BRFSS | XGBoost | **0.8318** | **0.4221** | **0.0935** | 0.3044 |
| BRFSS | CatBoost | 0.8308 | 0.4199 | 0.0936 | **0.3039** |
| BRFSS | Random Forest | 0.8257 | 0.4148 | 0.0940 | 0.3073 |
| BRFSS | LightGBM | 0.8135 | 0.3936 | 0.0963 | 0.3142 |
| Hospital130 | XGBoost | **0.6589** | **0.2065** | **0.0973** | **0.3382** |
| Hospital130 | Random Forest | 0.6584 | 0.2040 | 0.0973 | 0.3383 |
| Hospital130 | CatBoost | 0.6516 | 0.2003 | 0.0976 | 0.3396 |
| Hospital130 | LightGBM | 0.6334 | 0.1874 | 0.0984 | 0.3430 |

The models are close on PIDD and BRFSS. CatBoost leads the current Sylhet pilot, but its extreme calibration estimates indicate instability in this small, symptom-driven cohort. Hospital130 discrimination is modest and belongs to a different clinical task. These results do not establish that dynamic model switching is superior; current routing gains are small or unstable and do not support a strong superiority claim.

## 5. Input and feature-availability behavior

Input is dataset-namespaced JSON so that similarly named fields retain their original definitions and encodings. Any number of attributes can be supplied from each supported dataset for the same patient, for example:

```json
{
  "pidd": {"Glucose": 142, "Age": 34},
  "sylhet": {"Polyuria": 1, "Polydipsia": 0},
  "brfss": {"GenHlth": 3, "Age": 5}
}
```

`Age` in PIDD is age in years, whereas BRFSS `Age` is a coded survey category; namespacing prevents the two from being treated as interchangeable. Every dataset defines predeclared feature panels, ranging from a minimal panel to the full input set. The router chooses the largest panel completely supported by the fields available for that dataset. Extra attributes that are not part of the selected panel are reported as unused rather than silently fused.

Availability has the expected performance cost. For example, PIDD AUROC changes from 0.8407 with all eight fields to 0.8107 with only glucose and age, and to 0.7484 for the four-field non-laboratory panel. Sylhet changes from 0.9650 with all 16 symptoms/demographics to 0.9052 using only polyuria and polydipsia. In the BRFSS smoke run, full-input AUROC is 0.8308 versus 0.7770 using only general health and age. These comparisons show why the output records exactly which panel was used.

## 6. Prediction and routing sequence

1. The schema validates dataset names, field names, numeric finiteness, categories, and reference ranges.
2. Each dataset expert independently determines its largest usable predeclared panel.
3. For that panel, the development-selected tree model and its fitted preprocessing and calibration objects are loaded.
4. Each fold model produces a calibrated probability. For five-fold development routers, the patient percentage is their mean; the minimum, maximum, and standard deviation are also returned as model-fold variation, not as a confidence interval.
5. The mean is compared with the predeclared research operating threshold, while remaining a continuous probability rather than only a yes/no label.
6. SHAP explanations, applicability notes, cohort comparisons, model/calibrator provenance, and evidence status are attached.
7. One dataset expert supplies the displayed percentage. Probabilities from different datasets are never averaged because no harmonized cross-dataset model has been trained on matched patients.

When more than one dataset expert is eligible, the default behavior is to abstain because automatic cross-dataset expert selection has not been validated. The caller may explicitly choose a dataset with `--prefer-dataset`. An experimental automatic-selection option exists only for demonstrations and is excluded from publication claims. Hospital130 cannot be selected as a diabetes-screening expert because its target is readmission.

## 7. Output

A successful result reports:

- calibrated probability and percentage;
- selected dataset, endpoint, feature panel, and fields used or ignored;
- model selected in each contributing fold and calibration provenance;
- operating threshold and number of folds above it;
- fold-level probability spread;
- SHAP-based contributing factors and additivity checks;
- reference-cohort context and out-of-range warnings;
- evidence tier, publication eligibility, and research-use disclaimer.

The stable target contract contains `diabetes_probability` and a separate `onset_age` slot. `onset_age.status` is currently `not_implemented`; a future time-to-event or age-at-onset model can populate it without changing the percentage interface.

## 8. When the system refuses to give a percentage

The system abstains rather than inventing a result when:

- the supplied fields do not complete any supported feature panel;
- a specifically requested panel is missing required fields;
- a value is invalid, non-finite, wrongly encoded, or outside its permitted/reference range unless explicitly allowed;
- multiple dataset experts are eligible but no validated or explicit selection exists;
- the requested dataset or endpoint is incompatible, especially mixing Hospital130 readmission with diabetes screening;
- a required model bundle or provenance check is unavailable.

The abstention output identifies the reason and the fields required to obtain a usable prediction.

## 9. Research conclusion and remaining work

The engineering pipeline now supports missing-feature routing, mixed namespaced inputs, calibrated percentages, explicit non-fusion across cohorts, provenance, explanations, and safe abstention. However, it is not yet research-paper-final. A defensible paper still requires full-scale preregistered runs, confidence intervals and repeated validation where planned, complete calibration and clinical-utility analysis, subgroup/fairness analysis, external or temporal validation, locked reproducible artifacts, and resolution of the publication-readiness audit blockers. The scientifically supportable present claim is that the system can produce traceable cohort-specific probabilities under varying feature availability—not that it is clinically deployable or that dynamic routing is conclusively better than a fixed model.
