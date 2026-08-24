# Availability-Aware Diabetes Screening Under Incomplete Predictor Panels: A Multi-Environment Development Study

**Document state:** Development manuscript; not final evidence and not authorized for submission  
**Evidence cutoff:** 24 August 2026  
**Target format:** Short applied machine-learning / health-informatics conference paper

## Abstract

**Background:** Diabetes-screening models are commonly evaluated with a fixed,
complete predictor set, although real users may provide only a clinically
meaningful subset. Models trained on public cohorts also represent different
endpoints and populations, making naïve cross-dataset fusion unsafe.

**Objective:** To evaluate how calibrated diabetes-status prediction changes
across prespecified feature-availability panels and whether an availability-aware
router preserves performance relative to strong fixed-model baselines while
abstaining outside evaluated routes.

**Methods:** PIDD, the Sylhet early-stage symptom cohort, and BRFSS 2015 are
treated as separate prediction environments. Logistic Regression, Random Forest,
XGBoost, LightGBM, and CatBoost are compared using leakage-controlled nested
cross-validation or a development holdout appropriate to each dataset. Model
selection occurs inside development data. Evaluation includes AUROC, average
precision, Brier score, log loss, calibration, threshold metrics, decision-curve
net benefit, paired uncertainty, reduced-panel degradation, selective prediction,
subgroups, missingness stress, and held-out SHAP explanations. The router chooses
only among models evaluated for a supported within-dataset panel and otherwise
abstains.

**Development results:** In the completed full-budget PIDD development study
(768 participants; 5 repeats x 5 outer folds), calibrated fixed-threshold AUROC
ranged from 0.835 to 0.841 and Brier score from 0.154 to 0.157 across the five
model families. CatBoost had the lowest mean Brier score (0.154), but model
differences were small. For the full panel, the availability router achieved
participant-level AUROC 0.843 and Brier score 0.152; the robust fixed-model
baseline achieved AUROC 0.843 and Brier score 0.152. No reduced-panel comparison
survived metric-wise Holm correction in the matched contrast family. At 70%
coverage, probability-certainty selection reduced full-panel router Brier score
from 0.152 to 0.110 but retained only 55.6% of positive events, demonstrating a
clinically important coverage trade-off. With 75% simulated feature dropout,
supported-panel coverage fell to approximately 4.8%-6.6%, while Brier score rose
to approximately 0.208-0.211 for Random Forest and XGBoost. In the grouped Sylhet
development study (520 participants; 5 x 5 outer folds), CatBoost achieved AUROC
0.968, average precision 0.982, and Brier score 0.066, but a calibration slope of
12.65 indicated instability. The full-panel router achieved AUROC 0.965 and Brier
0.068 versus 0.960 and 0.077 for the robust fixed baseline, without a corrected
significance claim. Across 32 Sylhet panel-specific-training contrasts, no
comparison survived Holm correction (minimum adjusted p=0.064). BRFSS scientific estimates remain pending because the next
full-sample holdout is the protected, one-time final evaluation and cannot be
accessed before protocol freeze and authorization.

**Conclusion:** The development evidence supports a reliability and applicability
paper, not a universal-model or algorithm-superiority claim. Availability-aware
routing is technically feasible and traceable, but its incremental predictive
gain over a robust fixed model is small. Missingness and selective acceptance can
materially change both probability accuracy and which positive cases remain
covered; these effects must be reported alongside headline discrimination.

**Keywords:** diabetes screening; missing predictors; model routing; calibration;
selective prediction; abstention; explainable machine learning

## 1. Introduction

Public diabetes datasets are often used for model leaderboards in which a fixed
feature vector is assumed to be available for every person. That assumption is
fragile in practical screening: laboratory measurements may be absent,
questionnaire fields may be skipped, and different environments may collect
non-overlapping predictors. A system that always returns a probability can
therefore appear convenient while silently extrapolating beyond its evaluated
input patterns.

Missing-predictor handling is not a new problem. Pattern submodels,
deployment-time imputation, and flexible feature acquisition have established
that prediction can be adapted to incomplete inputs. Likewise, calibration,
SHAP explanations, fairness reporting, and multi-model comparison are already
well represented in diabetes modelling. The unresolved applied question is
narrower: how much calibrated performance is retained under clinically
interpretable feature panels, whether routing between evaluated models improves
on a robust fixed-model baseline, and when the system should abstain.

This study evaluates that question across three separately analysed
diabetes-status environments. Its contributions are: (1) endpoint-safe feature
and routing contracts; (2) matched evaluation of full and reduced panels on the
same held-out participants; (3) calibration, paired uncertainty, clinical
utility, selective prediction, subgroup coverage, and missingness stress beyond
headline accuracy; and (4) reloadable prediction bundles with explicit
provenance and fail-closed abstention. It does not claim future diabetes onset,
age of onset, causal risk factors, cross-cohort probability fusion, or clinical
deployment readiness.

## 2. Materials and methods

### 2.1 Prediction environments and endpoints

PIDD uses the configured binary diabetes-positive label in a high-risk Pima
population. Sylhet uses the early-stage diabetes-positive label from a
symptom-questionnaire cohort. BRFSS 2015 uses the configured self-reported
diagnosed-diabetes status. These are parallel environments, not exchangeable
samples of one universal population. Hospital130 predicts 30-day readmission and
is retained only as a separate secondary engineering analysis.

For mixed namespaced input, the software validates features against each dataset
contract, identifies eligible routers, and either invokes one explicitly
selected compatible expert or abstains. It never averages probabilities across
endpoints or cohorts.

### 2.2 Feature panels and preprocessing

Panels are prespecified in dataset configuration. PIDD includes the full
eight-feature panel and reduced panels representing core metabolic,
glucose-plus-age, non-laboratory, routine-clinic, and no-insulin-or-skinfold
availability. Dataset-specific preprocessing is fitted inside each training
partition. PIDD physiologically implausible zeros are treated according to the
configured missingness contract; indicator-on and indicator-off variants are
evaluated in a separate retraining ablation.

The pipeline rejects unknown features, invalid values, unsupported panels, and
ambiguous multi-environment requests. The returned percentage is the calibrated
estimated probability of the configured recorded label in the selected
environment. It is not a diagnosis or a forecast of age at diabetes onset.

### 2.3 Models and validation

Candidate models are Logistic Regression, Random Forest, XGBoost, LightGBM, and
CatBoost. PIDD uses repeated stratified nested cross-validation with five repeats,
five outer folds, five inner folds, and 30 tuning trials per model-fold. Sylhet
uses grouped splitting so identical feature profiles do not cross partitions.
Large holdout datasets use outcome-blind split manifests and dataset-appropriate
participant or patient grouping. Hyperparameter optimization targets average
precision.

Calibration candidates are identity, sigmoid, and isotonic calibration, selected
without access to outer evaluation outcomes. Isotonic calibration is disabled
below the configured minimum calibration sample size. Threshold reports include
0.5, development Youden, and sensitivity-constrained policies; probability
metrics remain primary.

### 2.4 Availability routing

For each supported panel and outer training partition, candidate model families
are ranked using inner-development Brier score, with log loss and average
precision as tie-breakers. The selected bundle stores the dataset, endpoint,
panel, preprocessing contract, calibration method, threshold policy, training
split identity, software provenance, and supported applicability range.

The primary routing comparison is against a prespecified robust fixed model
evaluated on the identical participants and panel. A full-panel champion-family
baseline is also evaluated after masking unavailable inputs. Model-family
switching is considered superior only if the paired Brier improvement is at
least 0.005, its 95% interval excludes zero, and its Holm-adjusted two-sided
p-value is below 0.05. Otherwise switching is reported as negative or
inconclusive.

### 2.5 Outcomes and statistical analysis

Brier score is the primary probability metric. AUROC and average precision are
primary discrimination metrics. Supporting estimates include log loss,
calibration intercept and slope, observed-to-expected ratio, expected
calibration error, sensitivity, specificity, PPV, NPV, F1, MCC, likelihood
ratios, and decision-curve net benefit.

Repeated held-out predictions are averaged per unique participant before primary
inference. Sylhet uncertainty resamples complete identical-profile clusters.
Panel and model comparisons are paired on the same participants. Percentile
bootstrap confidence intervals and metric-wise Holm correction are used for
comparison families. Reduced-panel degradation is oriented so positive values
always mean worse performance.

Selective prediction ranks cases using the outcome-blind score
`2 x |probability - 0.5|` at 100%, 95%, 90%, 80%, and 70% target coverage. We
report actual coverage, retained positive-event coverage, accepted prevalence,
probability performance, and supported subgroup coverage. This score is an
evaluated baseline, not an assumed optimal deferral policy.

### 2.6 Explainability, stress tests, and reproducibility

SHAP values are computed only for held-out observations and are grouped back to
original clinical features before primary reporting. Encoded-column explanations
remain diagnostic. Missingness stress applies shared MCAR-like and structured
block masks to Random Forest and XGBoost at 0%, 25%, 50%, and 75% severity over
five replicates. Deliberately invalid global-preprocessing and naïve-split runs
are isolated as leakage demonstrations and prohibited from efficacy tables.

Every run records raw-data, configuration, split-manifest, and source-tree
hashes. Saved models, calibrators, predictions, tuning records, thresholds,
uncertainty tables, routing bundles, and explanations are linked by experiment
identifier. Final profiles fail closed until a signed protocol and authorization
record exist.

## 3. Development results

### 3.1 PIDD full-panel model performance

The full-budget PIDD development run contained 25 outer evaluations for each of
five models and complete participant aggregation for all 768 individuals. Table
1 reports calibrated probabilities with the fixed 0.5 descriptive threshold.
Differences were modest: the absolute Brier range was 0.0026 and the AUROC range
was 0.0059.

**Table 1. PIDD calibrated development performance, mean across 25 outer evaluations**

| Model | AUROC | Average precision | Brier | Log loss | Calibration slope | ECE |
|---|---:|---:|---:|---:|---:|---:|
| CatBoost | 0.841 | 0.719 | 0.154 | 0.468 | 1.028 | 0.078 |
| Random Forest | 0.838 | 0.721 | 0.156 | 0.473 | 1.046 | 0.076 |
| LightGBM | 0.836 | 0.717 | 0.156 | 0.473 | 1.007 | 0.075 |
| Logistic Regression | 0.836 | 0.723 | 0.156 | 0.477 | 1.055 | 0.074 |
| XGBoost | 0.835 | 0.715 | 0.157 | 0.476 | 1.017 | 0.078 |

These results do not support a claim that a complex model clearly dominates the
interpretable baseline.

![PIDD calibrated development performance across five model families. Error bars show 95% participant-bootstrap confidence intervals for participant-level estimates.](generated/figures/pidd_model_performance.png)

**Figure 1.** PIDD calibrated development performance across five model
families. Error bars show 95% participant-bootstrap confidence intervals for
participant-level estimates.

### 3.2 Feature availability and routing

At participant level, the full-panel availability router achieved AUROC 0.843,
average precision 0.706, Brier 0.152, and log loss 0.464. The robust fixed-model
baseline achieved AUROC 0.843, average precision 0.709, Brier 0.152, and log loss
0.463. The practically sized core-metabolic router achieved AUROC 0.839 and
Brier 0.154; the two-feature glucose-plus-age router achieved AUROC 0.809 and
Brier 0.166; the non-laboratory router achieved AUROC 0.756 and Brier 0.186.

Matched full-versus-reduced contrasts were estimated within model family on the
same participants. None of the 80 metric-panel-model comparisons had a
Holm-adjusted p-value below 0.05. The smallest adjusted value was approximately
0.080 for CatBoost AUROC degradation on the glucose-plus-age panel. This is
evidence of limited precision and multiplicity, not evidence of equivalence.

Separately training Random Forest and XGBoost for each reduced panel rather than
masking unavailable inputs in a full-panel model produced several nominal
improvements, including a 0.009 AUROC gain for XGBoost on glucose-plus-age and a
0.034 average-precision gain for Random Forest on the non-laboratory panel.
However, none of the 40 paired comparisons survived Holm correction; the minimum
adjusted p-value was 0.120. Panel-specific fitting is therefore not supported as
a superiority claim.

### 3.3 Selective prediction and subgroup coverage

For the full-panel router, lowering coverage from 100% to 70% improved Brier
score from 0.152 to 0.110 and AUROC from 0.843 to 0.882. However, only 149 of 268
positive events were retained (55.6%), compared with 389 of 500 negative cases
(77.8%). The apparent performance improvement therefore came with asymmetric
case retention and cannot be presented without event coverage.

Age-group analysis showed heterogeneous acceptance at 70% overall coverage:
81.3% of participants younger than 30 were accepted, compared with 60.3% aged
30-44, 55.4% aged 45-59, and 50.0% aged 60 or older. The oldest group contained
only 32 participants and was suppressed for performance estimation. These
findings make probability certainty unsuitable as an unqualified clinical
abstention rule.

![Full-panel PIDD availability-router performance and positive-event retention across selective-prediction coverage levels.](generated/figures/pidd_risk_coverage.png)

**Figure 2.** Full-panel PIDD availability-router probability loss and
positive-event retention across selective-prediction coverage levels.

### 3.4 Missingness stress and explanations

Under 75% MCAR-like feature dropout, supported-panel coverage was 6.6%, Random
Forest Brier score increased from 0.156 to 0.208, and XGBoost Brier score
increased from 0.157 to 0.210. Under 75% structured-block dropout, supported-panel
coverage fell to 4.8%, with Brier scores of 0.208 and 0.211, respectively. The
results support fail-closed applicability checks rather than unconditional
prediction under arbitrary missingness.

![PIDD Brier score and supported-panel coverage under MCAR-like and structured-block feature dropout.](generated/figures/pidd_missingness_stress.png)

**Figure 3.** PIDD probability loss and supported-panel coverage under
simulated feature dropout. Points summarize five-replicate stress evidence;
mechanisms are sensitivity analyses rather than real-world MNAR validation.

Held-out SHAP artifacts were produced for every completed model-fold and grouped
to original features. The reporting ablation retains original-feature grouping
as primary because it avoids splitting clinical concepts into preprocessing and
missing-indicator fragments.

In the full 25-fold retraining ablation, enabling missingness indicators did not
produce a Holm-corrected improvement for Logistic Regression or Random Forest
on AUROC, average precision, Brier score, or log loss; all adjusted p-values were
at least 0.200. Indicator handling therefore remains an implementation choice,
not a supported performance contribution.

### 3.5 Grouped Sylhet development results

The full-budget Sylhet study contained 25 outer evaluations for each model and
cluster-bootstrap uncertainty over identical symptom profiles. CatBoost had the
lowest fold-mean Brier score (0.066) and highest AUROC (0.968), followed by Random
Forest (Brier 0.072; AUROC 0.966). However, calibrated slopes were unstable,
including 12.65 for CatBoost and 2.20 for Random Forest, so the high
discrimination does not justify an unqualified claim that individual
probabilities are well calibrated.

**Table 2. Sylhet calibrated grouped-development performance, mean across 25 outer evaluations**

| Model | AUROC | Average precision | Brier | Log loss | Calibration slope | ECE |
|---|---:|---:|---:|---:|---:|---:|
| CatBoost | 0.968 | 0.982 | 0.066 | 0.235 | 12.652 | 0.074 |
| Random Forest | 0.966 | 0.981 | 0.072 | 0.246 | 2.200 | 0.087 |
| LightGBM | 0.953 | 0.973 | 0.080 | 0.290 | 1.354 | 0.085 |
| XGBoost | 0.957 | 0.976 | 0.080 | 0.266 | 2.244 | 0.085 |
| Logistic Regression | 0.957 | 0.976 | 0.086 | 0.285 | 1.431 | 0.091 |

![Sylhet participant-level model discrimination and probability loss across feature-availability panels under grouped development validation.](generated/figures/sylhet_performance_and_panels.png)

**Figure 4.** Sylhet participant-level model discrimination and panel-specific
probability loss under grouped development validation. Intervals use identical-
profile cluster resampling.

At participant level, the full-panel router achieved AUROC 0.965 and Brier 0.068,
whereas the robust fixed model achieved AUROC 0.960 and Brier 0.077. The paired
router-versus-fixed interval crossed no improvement after cluster resampling, and
no routing ablation survived Holm correction. Reduced panels showed descriptive
loss: the 10-feature core questionnaire router had AUROC 0.945 and Brier 0.095,
while the two-feature polyuria-polydipsia router had AUROC 0.905 and Brier 0.113.
None of 64 matched full-versus-reduced contrasts survived Holm correction; the
minimum adjusted p-value was 0.064.

Separately tuned panel-specific Random Forest and XGBoost pipelines were also
compared with masked full-panel inference across all four reduced panels and all
25 grouped outer splits. The analysis produced 41,600 held-out prediction rows
and 32 participant-paired, profile-cluster-resampled metric contrasts. No
contrast survived metric-wise Holm correction (minimum adjusted p=0.064). The
largest descriptive Brier improvement was 0.006 for XGBoost on the 10-feature
core questionnaire panel, with its interval crossing zero. Panel-specific
training therefore remains an inconclusive engineering option rather than a
supported superiority result.

The full missing-indicator retraining comparison likewise found no
Holm-corrected benefit. Random Forest predictions were numerically equivalent
with indicators on and off, while Logistic Regression differences were small
and all adjusted p-values were 1.000. This is expected because the Sylhet
questionnaire does not contain applicable numeric missingness for the indicator
transformer.

At 70% selective coverage, the full-panel router Brier score improved from 0.062
to 0.025 while retaining 76.9% of positive events. Subgroup support remained a
major caveat: the accepted female cell contained no negative events and was
suppressed, as were the youngest and oldest age groups. Under 75% simulated
dropout, supported-panel coverage fell to 4.0%-6.2% and Brier score rose to
0.278-0.289 across Random Forest and XGBoost.

### 3.6 Pending locked BRFSS estimate

Existing BRFSS smoke studies remain engineering evidence and are not promoted
into the main result table. The next full-sample BRFSS holdout is deliberately
reserved for a new concealed manifest and one authorized final execution after
protocol freeze. Hospital130 remains outside the diabetes-screening result family
because its endpoint is 30-day readmission.

## 4. Discussion

The development study changes the likely paper narrative. The strongest result
is not algorithm superiority: five model families produced very similar PIDD
probability performance, and the availability router was nearly indistinguishable
from a robust fixed model on the full panel. The contribution is instead an
evaluation framework that quantifies what is lost under specific availability
patterns and refuses unsupported prediction.

The reduced-panel results are clinically interpretable. Core metabolic features
retained most full-panel performance, whereas a non-laboratory panel and an
extreme two-feature panel showed larger losses. Yet multiplicity-adjusted matched
comparisons were imprecise in this small dataset. The correct conclusion is that
panel degradation can be measured and may be operationally modest for selected
panels, not that the panels are statistically equivalent.

Selective prediction illustrates why coverage must accompany accuracy. A simple
probability-certainty rule produced better retained-case metrics but discarded a
large fraction of positive cases and accepted age groups at different rates.
Likewise, missingness stress showed rapid collapse in supported-panel coverage at
high severity. A safe system needs an applicability layer and explicit
abstention reason, not only a calibrated score.

The study has important limitations. All primary datasets are public and mostly
cross-sectional; they do not measure future incidence or age of onset. PIDD and
Sylhet are small, and public benchmark reuse limits transportability. BRFSS uses
self-reported status and requires careful survey-design interpretation. The
current selective score is a baseline rather than an optimized clinical deferral
policy. No matched cohort contains all PIDD, Sylhet, and BRFSS attributes for the
same individuals, so mixed-input routing is not efficacy-validated fusion.
External or temporal validation remains necessary for clinical-generalization
claims.

## 5. Conclusion

An availability-aware, calibrated diabetes-screening pipeline can provide
traceable within-environment probabilities from prespecified feature panels and
abstain when no evaluated route is supported. In PIDD development evidence, the
router did not materially outperform a robust fixed model, while reduced panels,
selective acceptance, and simulated missingness changed both probability quality
and population coverage. The conference contribution should therefore be framed
around reliability under incomplete inputs, endpoint safety, and transparent
negative findings. Locked multi-environment evaluation and independent review
are required before submission.

## Declarations

**Ethics:** The study uses de-identified public datasets; dataset-specific terms
and institutional requirements must be confirmed by the authors before
submission.  
**Funding:** To be completed by the authors.  
**Conflicts of interest:** To be completed by the authors.  
**Data and code availability:** Repository URL, release tag, and archived DOI to
be inserted after protocol freeze and artifact review.  
**Author contributions:** To be completed using the venue's required taxonomy.

## References requiring final bibliographic formatting

1. TRIPOD+AI statement. BMJ. 2024;385:e078378.
2. PROBAST+AI. BMJ. 2025;388:e082505.
3. Evaluation of clinical prediction models, part 2. BMJ. 2024;384:e074820.
4. Vickers AJ, Elkin EB. Decision curve analysis. Med Decis Making. 2006.
5. UCI Machine Learning Repository. Early Stage Diabetes Risk Prediction dataset.
6. Handling missing predictor values when validating and applying a prediction model. BMC Med Res Methodol. 2020.
7. Missing data and prediction: the pattern submodel. Biostat Epidemiol. 2021.
8. Real-time imputation of missing predictor values in clinical practice. J Clin Epidemiol. 2022.
9. Building type 2 diabetes prediction models using the 2014 BRFSS. Prev Chronic Dis. 2019.
10. Original PIDD/ADAP study and dataset provenance record.

The reference list is a development placeholder. Titles, authors, volume,
pages, DOI, and venue style must be verified against full text before submission.
