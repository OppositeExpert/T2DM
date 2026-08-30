# Supplementary Appendix: Development Methods and Evidence

**State:** Development-only; accompanies the conference manuscript draft

## S1. Endpoint boundaries

| Environment | Target | Primary-paper role | Prohibited interpretation |
|---|---|---|---|
| PIDD | Configured diabetes-positive label | Primary, separate | Universal-population risk or future onset |
| Sylhet | Early-stage diabetes-positive label | Primary, separate | Incidence prediction or transport beyond symptom cohort |
| BRFSS 2015 | Self-reported diagnosed-diabetes status | Primary, separate | Clinical diagnosis or future incidence |
| Hospital130 | Readmission within 30 days | Secondary, separate endpoint | Diabetes-status prediction |
| Mixed router | No shared target | Software demonstration | Cross-cohort probability fusion |

## S2. Development protocol

The development profile uses seed 42, 30 hyperparameter trials, 500 bootstrap
resamples, average precision as the tuning objective, and identity, sigmoid, and
isotonic calibration candidates. Isotonic calibration requires at least 1,000
calibration observations. Threshold policies are fixed 0.5, development Youden,
and a sensitivity-constrained threshold targeting 0.80 sensitivity.

PIDD and Sylhet use repeated nested validation. PIDD uses five repeats, five
outer folds, and five inner folds. Sylhet additionally groups identical feature
profiles. Large datasets use concealed manifest-based holdouts. Final profile
execution is blocked in software until authorization metadata and a frozen
protocol are present.

## S3. Metric taxonomy

| Domain | Metrics | Interpretation rule |
|---|---|---|
| Probability accuracy | Brier, scaled Brier, log loss | Primary reliability evidence; lower is better |
| Discrimination | AUROC, average precision | AP is prevalence-sensitive and is always paired with prevalence |
| Calibration | Intercept, slope, O:E, ECE, curves | A percentage is not treated as reliable from AUROC alone |
| Classification | Sensitivity, specificity, PPV, NPV, F1, MCC, balanced accuracy | Secondary and threshold-dependent |
| Diagnostic | LR+, LR-, diagnostic odds ratio | Descriptive; undefined values handled explicitly |
| Clinical utility | Net benefit over threshold range | Compared with treat-all and treat-none |
| Applicability | Supported-panel coverage, abstention rate and reason | Reported with every incomplete-input analysis |
| Selective prediction | Risk-coverage, event coverage, accepted prevalence | Gains are invalid if achieved by hidden disproportionate rejection |

## S4. PIDD artifact-completeness audit

Experiment `pidd_development_072cd2104089` contains 25 outer split pairs for each
of five model families, 19,200 held-out fold predictions, 3,840 aggregated
participant-model rows, complete tuning records and saved models, 20 primary
summary rows, and no non-finite numeric values in the primary summary. Metadata
records the complete 25-split manifest, five inner folds, model list, raw-data
hash, dataset-configuration hash, source-tree hash, and participant-level
inference scope.

Dependent evidence directories include availability routing, matched panel
contrasts, artifact ablations, missing-indicator retraining, selective prediction,
subgroup analysis, missingness stress, explanations, and reporting ablations.
Panel-specific retraining is complete across all 25 outer splits for the
prespecified Random Forest and XGBoost reduced-panel comparisons.

## S5. Applicability and abstention contract

Prediction proceeds in this order:

1. Parse dataset-qualified feature names and reject unknown or conflicting keys.
2. Validate type, coding, plausible range, and required endpoint contract.
3. Identify supported panels within each dataset router.
4. If no route is eligible, abstain with a machine-readable reason.
5. If multiple incompatible environments remain eligible, require explicit
   dataset selection or abstain; do not fuse probabilities.
6. Load the saved bundle for the selected panel and fold ensemble.
7. Apply fitted preprocessing and calibration.
8. Return the label probability, uncertainty/provenance fields, selected dataset,
   panel, model family, calibration method, and threshold interpretation.

## S6. Ablation inventory

| Ablation | Scientific question | Evaluation control |
|---|---|---|
| Calibration selected vs raw | Does calibration improve probability accuracy? | Same outer predictions and participants |
| Router vs robust fixed model | Does model switching add value? | Same panels and participants |
| Brier vs AP/log-loss routing | Is routing objective consequential? | Same candidate model bank |
| Tree models vs Logistic Regression | Is complexity justified? | Paired held-out participants |
| Missing indicators on vs off | Do indicator features add value? | Separate tuning; same splits, models, budgets, seeds |
| Panel-specific fit vs masked full model | Does training for a panel outperform masking? | Same split, panel, family, budget, participant |
| Named panels vs size-only heuristic | Is panel composition more informative than count? | Regression on held-out panel results |
| Grouped vs encoded SHAP | Does clinical grouping change interpretation? | Same held-out SHAP values |
| Leakage demonstrations | How optimistic are invalid designs? | Explicitly prohibited from efficacy selection |

## S7. PIDD development robustness summary

The five full-panel models occupied a narrow performance range. The full-panel
availability router and robust fixed baseline were effectively tied at the
reported precision. No matched reduced-panel comparison survived Holm correction.
The core-metabolic panel retained most probability performance, while the
non-laboratory and glucose-plus-age panels showed larger descriptive loss.

The full missing-indicator retraining study found no corrected benefit for
indicator-on Logistic Regression or Random Forest across AUROC, average
precision, Brier score, or log loss. Adjusted p-values ranged from 0.200 to 1.000,
and all paired intervals crossed no improvement.

Panel-specific Random Forest and XGBoost fitting was evaluated for five reduced
panels over all 25 outer folds, producing 76,800 prediction rows and 40 paired
metric contrasts. Several unadjusted intervals favoured panel-specific fitting,
but no comparison survived Holm correction; the minimum adjusted p-value was
0.120. The evidence does not justify a claim that retraining a specialist model
is generally superior to masked full-panel inference.

Selective probability-certainty acceptance improved retained-case Brier score as
coverage decreased, but retained positive events less often than negative cases.
Age-group coverage was heterogeneous and the oldest group was too small for
stable performance estimation. Severe simulated missingness raised probability
loss and left fewer than 7% of participants compatible with a named panel. These
results favour explicit abstention over extrapolation.

## S8. Reporting and risk-of-bias controls

The full grouped Sylhet benchmark (`sylhet_development_b52477910fe6`) contains
25 grouped outer splits per model, complete aggregation for all 520 participants,
cluster-bootstrap intervals, 20 primary summary rows, and no non-finite primary
metrics. The full router achieved participant-level AUROC 0.965 and Brier 0.068,
but no routing, model-family, calibration, selector-metric, or matched-panel
comparison survived Holm correction. Extreme calibration slopes, suppressed
subgroups, and severe-dropout applicability collapse are retained as limitations
rather than hidden behind the cohort's high discrimination.

Full Sylhet panel-specific retraining covered four reduced panels, two model
families, and all 25 grouped outer splits. It produced 41,600 held-out prediction
rows and 32 paired metric contrasts. No contrast survived Holm correction; the
minimum adjusted p-value was 0.064. The full missing-indicator retraining family
also produced no corrected benefit: Random Forest was numerically equivalent,
and all Logistic Regression adjusted p-values were 1.000. Neither component
supports a model-superiority claim.

The final package must include a completed TRIPOD+AI checklist and a reviewed
PROBAST+AI assessment. Key safeguards already implemented are fold-local
preprocessing, nested selection, participant-level repeated-CV aggregation,
profile-cluster resampling for Sylhet, patient grouping for Hospital130,
outcome-blind manifests, calibration evaluated on held-out data, paired
comparisons, multiplicity correction, complete artifact provenance, and
fail-closed final authorization.

Residual concerns are public-benchmark reuse, small cohorts, self-reported BRFSS
status, limited transportability, missingness-mechanism uncertainty, subgroup
sample size, and absence of external or temporal validation. These limitations
must remain visible even if final internal metrics are strong.

## S9. BRFSS full-development evidence

Study `brfss_development_holdout_56407ef53bba` used the full 429,360-row retained
cohort with the existing seed-42 development contract: 343,488 rows across five
development folds and 85,872 rows in the development test role. The latter
contained 11,451 recorded positives. Because seed-42 outcomes were inspected in
prior development work, this evidence is not eligible for final claims.

All five model families completed 30 development tuning trials, cross-fitted
calibration selection, three threshold policies, 500 participant-bootstrap
intervals, paired comparisons, paired decision-curve inference, bundle export,
and exact reload verification. Development OOF selection chose LightGBM. On the
development test, XGBoost had calibrated AUROC 0.8430, average precision 0.4436,
Brier 0.09150, and log loss 0.29581; CatBoost and LightGBM differed by less than
0.0002 AUROC and 0.00005 Brier. No top-three pairwise metric difference survived
Holm correction.

The availability router used LightGBM for the 21-feature panel and XGBoost for
all five reduced panels. Full-panel Brier was 0.09154; the two-feature panel had
Brier 0.10198. None of 80 matched full-versus-reduced contrasts survived
metric-wise Holm correction (minimum adjusted p=0.0798), although every
pointwise degradation interval excluded zero. Matched-panel contrasts, artifact ablations, certainty-based
selective prediction, subgroup analysis, survey sensitivity, and held-out SHAP
were executed using the supported holdout paths. Retraining-only missing-
indicator, panel-training, simulated-missingness, and reporting-ablation engines
currently apply to repeated nested-CV studies and were not misrepresented as
BRFSS holdout analyses.

Survey weighting yielded 10.95% prevalence, compared with 13.34% unweighted.
For XGBoost, weighted AUROC was 0.8707 and Brier 0.07517. The 500-replicate
stratified PSU bootstrap produced pointwise intervals, but the random respondent
holdout was not designed as an official survey partition; this remains a
secondary sensitivity analysis.

At 70% full-panel selective coverage, Brier score improved to 0.0430, but
positive-event coverage collapsed to 25.0%, accepted prevalence to 4.76%, AUROC
to 0.784, and average precision to 0.128. These values demonstrate selective
case-mix change rather than clinical utility and must be presented together.

The BRFSS subgroup analysis estimated 30 age-group and sex cells across five
coverage targets, with no small-cell suppressions under the configured minimums
of 50 accepted observations and 10 positive and 10 negative events. At the 70%
target, observed subgroup coverage ranged from 69.7% to 70.3%; accepted
prevalence ranged from 4.59% to 4.75% and average precision from 0.125 to 0.133.
These are within-cohort descriptive estimates, not evidence of population
representativeness or causal fairness.

In the BRFSS model-family ablation, each tree model improved over Logistic
Regression on AUROC, average precision, Brier score, and log loss after
metric-family Holm correction (adjusted p=0.016). Calibration improved CatBoost
Brier score by 0.07762 and log loss by 0.19890 relative to its uncalibrated raw
score; LightGBM selected identity calibration and showed no change. Router
selection by average precision or log loss did not yield corrected improvements
over the prespecified Brier selector, and routing did not outperform the robust
single-model comparator after correction. These are development ablations.

Held-out SHAP explanations used 1,000 test-role respondents per model and a
100-row development-only background. Original-feature aggregation placed
general health, high blood pressure, age, BMI, and high cholesterol in the top
five for four models; CatBoost contained the same features in a different order.
Maximum additive reconstruction error ranged from 2.2e-15 for Logistic
Regression to 5.6e-6 for XGBoost. The holdout design supplies one explanation
sample rather than fold-pair stability estimates, and SHAP values are not causal
effects.

## S10. Hospital130 full-development readmission evidence

Study `hospital130_development_holdout_c3aa5fb84a7a` retained 99,343 encounters
from 69,990 patients after excluding death and hospice discharge dispositions.
The binary endpoint was readmission within 30 days; 11,314 encounters were
positive. Patient-grouped splitting placed 79,475 encounters from 55,987
patients in five development folds and 19,868 encounters from 14,003 patients
in the development test role. No patient crossed the holdout boundary or a
development fold. Identifiers and the outcome were excluded from all 46
predictors.

All five model families completed 30 development tuning trials, development-only
calibration and threshold selection, 500 patient-cluster bootstrap intervals,
paired model and decision-curve comparisons, model export, and exact reload
verification. LightGBM was the development-selected champion. Its calibrated
development-test estimates were AUROC 0.6792 (95% interval 0.6671-0.6913),
average precision 0.2288 (0.2134-0.2445), Brier score 0.09584
(0.09183-0.09921), log loss 0.33271 (0.32180-0.34185), and calibration slope
1.019 (0.957-1.094). The four tree families did not differ from each other after
metric-wise Holm correction. All four did outperform Logistic Regression across
AUROC, average precision, Brier score, and log loss in the prespecified
artifact-based family (adjusted p=0.0399); this remains development evidence.

Availability routing selected LightGBM for the full and admission-clinical
panels and Random Forest for encounter-utilization, prior-utilization, and
minimal-inpatient-history panels. Router Brier score was 0.09584 for all 46
features and 0.09820-0.09939 across reduced panels. Matched full-versus-reduced
degradation was estimated on identical test patients using cluster bootstrap.
The artifact ablation remains explicitly incomplete because retraining-only
missing-indicator, panel-specific-training, simulated-dropout, and leakage
demonstration engines apply to nested-CV studies and were not forced onto this
holdout contract.

At 80% full-panel selective coverage, 15,895 encounters from 12,256 patients
were accepted and 3,973 encounters from 1,747 patients were abstained. Accepted
prevalence was 7.62%, compared with 26.45% among rejected encounters. Age, sex,
and race subgroup estimates used the prespecified small-cell rules. Held-out
SHAP explained 1,000 test encounters per model with a 100-row development-only
background. For LightGBM, prior inpatient encounters and discharge disposition
were the two most influential original features; maximum additive reconstruction
error was 1.2e-14. Five exported model bundles reproduced all 19,868 test
probabilities with maximum absolute error below 1.4e-16.

The original run completed its scientific artifacts before a missing
`PROJECT_ROOT` import interrupted metadata writing. The receipt was regenerated
from the completed checkpoints without refitting any model, and this recovery is
recorded in `experiment_metadata.json`. The permanent import defect is fixed in
source. Hospital130 remains a development-only, retrospective readmission study;
it is neither diabetes-status evidence nor external or clinical validation.

## S11. Reproducibility artifact map

| Artifact | Location |
|---|---|
| Development configuration | `config/experiments/development.yaml` |
| Publication controls | `config/publication_protocol.yaml` |
| Statistical analysis plan | `docs/research/Statistical_Analysis_Plan.md` |
| Endpoint hierarchy | `docs/research/Endpoint_and_Claim_Hierarchy.md` |
| Leakage/applicability audit | `docs/research/Data_Leakage_and_Applicability_Audit.md` |
| Decision log | `docs/research/Decision_Log.md` |
| PIDD development study | `outputs/publication_pipeline/studies/pidd_development_072cd2104089` |
| Sylhet development study | `outputs/publication_pipeline/studies/sylhet_development_b52477910fe6` |
| BRFSS development study | `outputs/publication_pipeline/studies/brfss_development_holdout_56407ef53bba` |
| Hospital130 development study | `outputs/publication_pipeline/studies/hospital130_development_holdout_c3aa5fb84a7a` |
| Tracked study registry | `evidence/study_registry.json` |
| Data-source manifest | `config/data_sources.yaml` |
| Exact environment lock | `requirements.lock` |
| Command reference | `docs/RUNBOOK.md` |
| Automated tests | `tests/` |

## S12. Items reserved for locked evidence

- Final participant-flow counts, exclusions, and the protected authorized BRFSS
  decision table from a new concealed partition, not the seed-42 development test.
- Frozen model/panel choices and justified non-inferiority margins.
- Authorized concealed estimates with 2,000-resample intervals, decision curves,
  calibration plots, subgroup tables, and the claim-evidence map.
- Repository release tag, archive DOI, author list, affiliations, funding,
  conflicts, ethics wording, and venue-specific formatting.
