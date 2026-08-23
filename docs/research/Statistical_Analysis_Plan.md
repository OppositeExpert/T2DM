# Statistical Analysis Plan

**Study:** Availability-aware calibrated prediction across separate diabetes-screening environments

**SAP version:** 0.1, 23 August 2026

**Status:** Draft and unlocked

**Authorization:** Development analysis only. This SAP does not authorize creation, inspection, or evaluation of a new final holdout.

## 1. Purpose and governance

This SAP prespecifies the study populations, endpoints, estimands, validation
designs, performance measures, comparisons, uncertainty methods, multiplicity
control, failure handling, and reporting rules. It must be finalized after the
structured novelty review and development ablations but before final evaluation.

All changes must be recorded in `Decision_Log.md`. After freeze, changes are
permitted only for a demonstrable implementation error. The error, affected
outputs, correction, and rerun authorization must be documented before any rerun.

The existing seed-42 BRFSS and Hospital130 holdouts are development-only. They
were used in smoke evaluation and their outcomes were summarized during audits.
They are not eligible as untouched final evidence.

## 2. Objectives

### 2.1 Primary objective

Estimate how proper probability performance changes across prespecified feature-
availability panels and determine whether the calibrated availability router
preserves Brier performance relative to a robust fixed-model baseline.

### 2.2 Secondary objectives

1. Quantify discrimination, calibration, and decision utility for every panel.
2. Test whether dynamic model-family selection provides a meaningful advantage
   over fixed-model strategies.
3. Quantify risk/loss versus coverage under explicit abstention.
4. Assess performance and abstention coverage in prespecified supported subgroups.
5. Evaluate component ablations using identical folds, patients, and budgets.

### 2.3 Out-of-scope objectives

- Cross-dataset probability pooling or automatic selection of a cohort expert.
- Causal inference or risk-factor discovery.
- Future diabetes incidence, time to event, or age at onset.
- Clinical deployment or treatment recommendations.

## 3. Study populations and endpoints

| Dataset | Analysis population | Endpoint | Primary-study role |
|---|---|---|---|
| PIDD | All 768 configured rows after contract validation | Binary diabetes-positive label | Primary, separate environment |
| Sylhet | All 520 configured rows; identical predictor profiles grouped | Binary early-stage diabetes-positive label | Primary, separate environment |
| BRFSS 2015 | Target-valid responses after prespecified exclusions | Self-reported diagnosed diabetes: response 1 versus response 3 | Primary, separate environment |
| Hospital130 | Eligible encounters after prespecified death/hospice and feature exclusions | Readmission within 30 days | Secondary and endpoint-separated, if retained |

The expected retained counts at the Phase 0 baseline are 768 PIDD rows, 520
Sylhet rows, 429,360 BRFSS rows, and 99,343 Hospital130 encounters. Final cohort
flow will be regenerated and compared with raw/configuration hashes. Unexplained
count changes stop the run.

## 4. Predictor panels and systems

The named panels in `config/availability_scenarios.yaml` are the prespecified
feature-availability environments. The full panel is the reference. Practical
reduced panels and severe-degradation stress panels will be labelled before
freeze; two-feature panels are stress tests by default.

Candidate model families are Logistic Regression, Random Forest, XGBoost,
LightGBM, and CatBoost for benchmark studies. Availability routing selects among
the four tree families currently listed by contract. The following systems are
compared on identical held-out patients within each panel:

1. Availability router: model family selected by cross-fitted development Brier
   score, with log loss and negative AP as deterministic tie-breakers.
2. Robust single model: one prespecified model-family strategy used across panels.
3. Full-panel champion family: the model family selected on the full panel and
   evaluated under each available panel.
4. Logistic Regression: interpretable benchmark where supported.

The exact construction of baselines 2 and 3 must be verified in code and frozen
in an ablation protocol. Training information, preprocessing, calibration, and
threshold learning must remain inside the corresponding development partition.

## 5. Validation design

### 5.1 PIDD

- Five repeats of five-fold stratified nested cross-validation.
- Five inner folds for tuning within each outer development partition.
- Final profile: 75 tuning trials per model/fold and 2,000 bootstrap resamples.
- Preprocessing, imputation, tuning, calibration selection, and thresholds fit
  within each outer development partition only.
- Each participant receives one held-out prediction per repeat.

### 5.2 Sylhet

- Five repeats of five-fold stratified grouped nested cross-validation.
- Identical feature profiles remain in the same outer and applicable inner group.
- Other budgets and fold isolation match PIDD.
- The identical-profile group is the resampling unit for primary uncertainty.

### 5.3 BRFSS

- A new, prespecified concealed 20% stratified final partition is required.
- The split seed and manifest will be generated and escrowed only after all
  protocol/code choices are frozen; seed 42 is prohibited for final evidence.
- Model selection, preprocessing, calibration, thresholding, and routing are
  completed within the 80% development partition.
- The concealed 20% partition is evaluated exactly once.
- Survey-weight, stratum, and primary-sampling-unit availability must be audited.
  If unavailable, results are cohort-level and not population-representative.

### 5.4 Hospital130

- Include only if approved as a separate secondary analysis.
- Use a new patient-grouped final split if a final claim is planned.
- All encounters from one patient remain in one partition.
- Use patient-cluster bootstrap and never present this endpoint as diabetes detection.

### 5.5 Final split concealment control

The final-split implementation must support a label-blind manifest creation path.
Before authorization, routine audit output must not print final outcome counts,
prevalence, metrics, or patient predictions. A designated manifest hash may be
visible; test labels and derived summaries may not be read by development code.
The final command must fail closed unless the protocol is frozen, the final
profile is locked, all required hashes match, and a one-time authorization record
exists.

## 6. Model development

- Primary tuning metric: average precision.
- Hyperparameter space: frozen model-adapter spaces after development ablation.
- Randomness: every fold/model/tuning seed is deterministically derived and saved.
- Parallelism: fixed and recorded; changing it must not change seeded results.
- Imputation and encoding: fit inside training folds only.
- PIDD physiological zero values are converted to missing according to the
  dataset contract before fold-fitted imputation.
- No oversampling, synthetic sampling, class balancing, or test-prevalence
  modification is permitted unless separately prespecified as development-only.

## 7. Calibration

Identity, sigmoid, and eligible isotonic calibration are compared using cross-
fitted development predictions. Isotonic requires at least 1,000 calibration
observations. Selection uses Brier score, then log loss as a deterministic
tie-breaker. The selected calibrator is fitted without outer/final labels and
applied unchanged to evaluation predictions.

Raw and calibrated performance will both be retained. Calibration method,
candidate scores, sample size, convergence, coefficients where applicable, and
failure reason are saved for every model/fold/panel.

## 8. Thresholds and clinical utility

The detailed rules are in `Threshold_and_Clinical_Utility_Policy.md`.
Sensitivity-constrained thresholding at a provisional target of 0.80 is the draft
primary operating rule; Youden is secondary and 0.5 descriptive. All learned
thresholds come from cross-fitted development predictions.

Decision curves use dataset-specific frozen ranges and compare the model with
treat-all and treat-none. Final net-benefit uncertainty uses the same paired
individual/profile/patient bootstrap as the corresponding endpoint.

## 9. Outcomes and estimands

### 9.1 Primary probability outcome

Calibrated Brier score is the primary performance outcome. Core paired estimands:

- `Brier_router - Brier_robust_fixed` within each panel;
- `Brier_reduced_panel - Brier_full_panel` within each system;
- `Brier_calibrated - Brier_raw` for calibration ablation.

Lower values favor the first-named proposed system only when expressed as an
explicit reduction; all tables will state direction.

### 9.2 Discrimination outcomes

- AUROC.
- Average precision, interpreted with cohort prevalence.

### 9.3 Calibration and probability outcomes

- Brier and scaled Brier score.
- Log loss.
- Calibration intercept and slope.
- Observed/expected ratio.
- Equal-frequency calibration curves and counts.
- Expected calibration error as secondary because it depends on binning.

### 9.4 Threshold-dependent outcomes

- Sensitivity, specificity, PPV, NPV.
- False-positive and false-negative rates.
- Balanced accuracy, F1, MCC, likelihood ratios, and confusion matrix.
- Accuracy is descriptive and never the sole primary result.

### 9.5 Clinical utility and selective prediction

- Net benefit and paired net-benefit difference over frozen threshold ranges.
- Coverage and abstention rate.
- Accepted-case Brier, log loss, AUROC, and AP.
- Contract-failure counts by reason.
- Subgroup coverage and outcome performance.

## 10. Primary inference units and repeated predictions

For PIDD, held-out probabilities from the five repeats will be averaged per
unique participant before primary pooled metrics and paired bootstrap inference.
For Sylhet, predictions are likewise aggregated per row across repeats, but
complete identical-profile groups are resampled. This prevents treating the same
person's repeated held-out predictions as independent observations.

Repeat/fold metrics and paired Wilcoxon comparisons remain useful stability
analyses. Their t-based confidence intervals are descriptive and will not be the
sole primary inferential evidence because training folds overlap.

BRFSS uses unique held-out individuals. Hospital130 uses complete patient
clusters. All compared systems must share identical ordered row IDs, labels, and
bootstrap indexes.

This participant-aggregated repeated-CV inference is not yet implemented in the
current runner and is a pre-freeze engineering requirement.

## 11. Confidence intervals

- Confidence level: 95%, two-sided.
- Final resamples: 2,000.
- PIDD and BRFSS: outcome-stratified individual bootstrap.
- Sylhet: complete identical-profile cluster bootstrap, rejecting degenerate
  one-class replicates.
- Hospital130: complete patient-cluster bootstrap.
- Percentile intervals are the current implementation. Development analysis must
  compare percentile coverage with BCa or another justified alternative for key
  estimands, especially calibration slope in small cohorts.
- Point estimates, lower/upper bounds, resampling unit, valid replicate count,
  failed replicate count, seed, and method are stored.

## 12. Comparisons, margins, and multiplicity

### 12.1 Router preservation

Non-inferiority on Brier score is concluded within a panel when the upper 95% CI
for `Brier_router - Brier_robust_fixed` is below 0.010. If it crosses 0.010, no
preservation claim is made. This draft margin must be literature-reviewed before
freeze.

### 12.2 Router superiority

Superiority requires all of:

1. observed Brier reduction at least 0.005;
2. paired 95% CI excludes zero in the beneficial direction;
3. Holm-adjusted two-sided p-value below 0.05 within the dataset's primary family.

AUROC, AP, and log loss must not show a clinically material contradiction.

### 12.3 Reduced-panel degradation

For practical reduced panels, draft graceful-degradation margins are a Brier
increase no greater than 0.020 and AUROC decrease no greater than 0.050 versus
the full panel. Severe two-feature stress panels are reported but excluded from
the practical-panel success requirement.

### 12.4 Multiplicity families

Within each dataset:

- Primary family: router-versus-robust-fixed Brier comparisons across all named panels.
- Key secondary family: reduced-versus-full Brier comparisons across practical panels.
- Secondary discrimination family: paired AUROC and AP comparisons.
- Exploratory family: model-family pairwise comparisons, individual thresholds,
  subgroups, explanations, and severe stress panels.

Holm correction is applied within each confirmatory family. Raw and adjusted
p-values and the number of hypotheses are reported. No global p-value combines
different datasets or endpoints.

## 13. Missing data and applicability

- Missing values are retained and imputed within training folds; no complete-case
  restriction is introduced post hoc.
- Missingness prevalence is reported by predictor, endpoint, dataset, and
  supported subgroup.
- Named panel availability is distinct from sporadic within-panel missingness.
- Out-of-range, invalid category, unsupported panel, endpoint mismatch, ambiguous
  environment, and missing artifact are explicit abstention reasons.
- Random feature-dropout stress tests are secondary and do not replace the named
  availability-panel analysis.

## 14. Subgroup analysis

Candidate subgroups are prespecified only where represented and meaningful:

- age bands within each dataset using that dataset's encoding;
- sex/gender where available, with dataset-specific limitations stated;
- BRFSS general-health and socioeconomic strata if justified as applicability analyses;
- Hospital130 race and gender only if the secondary endpoint is retained and
  data quality supports interpretation.

An estimate is suppressed when a subgroup has fewer than 100 observations, 20
events, or 20 non-events. Suppression thresholds apply separately to accepted
cases in selective-prediction analyses. Report group size, event count,
prevalence, AUROC, AP, Brier, calibration, primary-threshold sensitivity and
specificity, coverage, and confidence intervals. Intersectional analyses are
exploratory and require the same minimum counts.

Subgroup results assess performance heterogeneity and coverage; they do not
establish biological or causal differences.

## 15. Selective prediction

Contract-based abstentions are analyzed separately from any graded acceptance
rule. The graded score and direction must be defined from development data and
frozen. Report nominal and actual coverage at 100%, 90%, 80%, 70%, and 50% where
supported, accepted-case performance, uncertainty, subgroup coverage, and reason
counts. Do not interpret loss improvement without the coverage tradeoff.

## 16. Ablations

Required development-only ablations use identical folds/patients and, unless the
ablation explicitly removes a step, identical tuning budgets:

1. Raw versus selected calibration.
2. Availability router versus robust single model.
3. Router selection by Brier versus AP and log loss.
4. Full panel versus every named reduced panel.
5. Fold-safe imputation versus inappropriate global preprocessing as a leakage
   demonstration, clearly labelled non-deployable.
6. Sylhet grouped versus naive random splitting as a leakage demonstration.
7. With versus without applicability/abstention checks.
8. Tree families versus Logistic Regression benchmark.
9. Named panels versus prespecified random feature-dropout stress tests.

Leakage demonstrations are methodological warnings, never candidate final models.

## 17. Failure and missing-result handling

- Any outer/final prediction leak, row mismatch, split-hash mismatch, or outcome
  exposure stops the run and invalidates affected results.
- A model/calibrator failure is recorded with exception type, fold, panel, seed,
  and stage; it is not silently replaced.
- Degenerate calibration fits fall back only according to a frozen deterministic
  rule tested before final execution.
- Metrics requiring both classes are marked unavailable, not replaced with zero.
- Bootstrap replicates with invalid metrics are counted. If fewer than 95% of
  replicates are valid for a primary estimand, its interval is not reported and
  the reason is investigated before freeze or disclosed after final execution.
- A final rerun is permitted only for a documented implementation/infrastructure
  failure unrelated to observed effect direction.

## 18. Reproducibility and artifact requirements

Every final study must preserve:

- raw-data, row-flow, split-manifest, source-tree, configuration, ontology, and
  dependency hashes;
- operating system, Python/library versions, CPU architecture, seeds, parallelism,
  and start/end timestamps;
- raw/calibrated patient-level predictions with stable pseudonymous row IDs;
- fitted preprocessors, models, calibrators, thresholds, and routing bundles;
- all metric, interval, comparison, calibration, threshold, decision-curve,
  subgroup, selective-prediction, and explanation artifacts;
- the signed SAP, final protocol configuration, authorization record, and
  immutable backup manifest.

Patient input examples must be synthetic. Raw sensitive inputs are not placed in
shell history or committed to public artifacts.

## 19. Reporting

Results are reported separately by dataset and endpoint. Each primary table
contains sample size/events, panel, system, calibration method, Brier, log loss,
AUROC, AP, calibration intercept/slope, observed/expected ratio, 95% CIs, and
evidence tier. Threshold and utility tables are separate.

Negative, inconclusive, unstable, and failed results are reported. Explanations
use held-out data and are described as model behavior, not causal attribution.
The manuscript will follow the completed TRIPOD+AI crosswalk and disclose the
PROBAST+AI assessment.

## 20. Required implementation before freeze

- [ ] Participant-level aggregation across repeated PIDD/Sylhet held-out predictions.
- [ ] Identical-profile cluster bootstrap for Sylhet primary inference.
- [ ] Paired bootstrap CIs for reduced-panel versus full-panel degradation.
- [ ] Net-benefit uncertainty and paired decision-curve comparisons.
- [ ] Selective-prediction/risk-coverage engine and failure-reason tables.
- [ ] Subgroup metrics, suppression, coverage, and uncertainty engine.
- [ ] Prespecified ablation runner with matched folds and budgets.
- [ ] Label-concealed fresh-final split and one-time authorization guard.
- [ ] Final preflight for hashes, disk capacity, output emptiness, and backup target.
- [ ] Blank final tables and figures approved.

## 21. SAP sign-off gate

The SAP may be frozen only after:

1. the novelty review is complete;
2. the claims/margins and clinical threshold ranges are justified;
3. all development ablations, selective-prediction, and subgroup analyses are reviewed;
4. required inference and concealment code passes tests on development/synthetic data;
5. version control or an equivalent immutable source archive exists;
6. all blank result shells and failure rules are approved;
7. the decision log contains no unresolved final-result-dependent choice.

Only then may `protocol_frozen` and the final profile's `locked` field be changed
under a recorded authorization. Until that event, every generated estimate is
development evidence.
