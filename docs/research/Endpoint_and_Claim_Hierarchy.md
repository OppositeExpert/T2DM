# Endpoint and Claim Hierarchy

**Status:** Draft, development-only

**Version:** 0.1, 23 August 2026

**Freeze state:** Unlocked; this document does not authorize final evaluation

## 1. Study question

For separately defined diabetes-screening/status cohorts, how much discrimination,
probability accuracy, calibration, and decision utility are retained when only a
prespecified subset of predictors is available, and can an availability-aware,
calibrated, abstaining system perform at least as well as practical fixed-model
baselines without crossing endpoint boundaries?

The study is an evaluation of prediction under feature-availability environments.
It is not a study of causal risk factors, future diabetes incidence, age of onset,
or automatic fusion of probabilities from unrelated cohorts.

## 2. Endpoint hierarchy

| Tier | Dataset or component | Prediction target | Evaluation role | Permitted wording |
|---|---|---|---|---|
| Primary | PIDD | Configured diabetes-positive label | Separate primary environment | Probability of the recorded PIDD label in a compatible PIDD-like population |
| Primary | Sylhet | Early-stage diabetes-positive label | Separate primary environment | Probability of the recorded symptom-cohort label in a compatible Sylhet-like setting |
| Primary | BRFSS 2015 | Self-reported diagnosed diabetes; raw response 1 positive, response 3 negative | Separate primary environment | Probability of the configured self-reported diagnosed-diabetes status |
| Secondary, separate endpoint | Hospital130 | Readmission within 30 days | Methodological/secondary analysis only | Probability of 30-day readmission for an eligible diabetes-related hospital encounter |
| Software demonstration | Mixed namespaced input router | No shared statistical endpoint | Demonstrates validation, environment selection, provenance, and abstention | The system identifies eligible cohort experts or abstains; it does not fuse their probabilities |
| Future work only | Not currently available | Time to diabetes onset or age at onset | Out of scope | Requires longitudinal follow-up, a time origin, censoring, and survival or competing-risk modelling |

PIDD, Sylhet, and BRFSS results will be reported in parallel, never pooled into a
single probability or efficacy estimate. Hospital130 will not be included in a
diabetes-detection summary score.

## 3. Claim hierarchy

### 3.1 Primary claim

The proposed system quantifies the change in calibrated predictive performance
across prespecified feature-availability panels, preserves dataset and endpoint
boundaries, and abstains when the supplied input cannot support an evaluated
prediction route.

This claim succeeds only if the locked analysis reports complete availability
degradation, calibration, uncertainty, applicability, and abstention evidence.
It does not require dynamic model-family switching to be statistically superior.

### 3.2 Key secondary claims

1. Selected clinically plausible reduced panels retain acceptable probability
   performance and discrimination relative to their dataset's full panel.
2. The availability router is non-inferior to the prespecified robust fixed-model
   baseline on Brier score within evaluated panels.
3. Abstention or selective acceptance improves retained-case probability loss as
   coverage decreases, without hiding disproportionate subgroup rejection.

### 3.3 Secondary or negative-result claim

Dynamic model-family selection is not assumed to outperform a strong fixed model.
Any superiority statement requires a prespecified effect size, a 95% confidence
interval excluding no benefit, and a Holm-adjusted two-sided p-value below 0.05.
Otherwise the manuscript will report the switching result as inconclusive or
negative.

### 3.4 Demonstration-only claims

- Mixed namespaced attributes can be parsed and matched to one or more evaluated
  dataset-specific panels.
- If exactly one eligible environment is identified or selected, its saved
  ensemble can return a calibrated research probability with provenance.
- If no panel is supported, values are invalid/out of applicability range, or
  several incompatible experts remain eligible, the system abstains.

No mixed-input experiment may be described as learned multi-cohort fusion,
cross-dataset model selection, or a universal diabetes-risk model.

## 4. Claim-to-estimand map

| Claim | Unit | Comparison | Primary estimand | Supporting estimands | Success rule |
|---|---|---|---|---|---|
| Availability degradation | Patient; profile cluster for Sylhet | Each named reduced panel versus the full panel within the same dataset/system | Change in Brier score | Change in AUROC, AP, log loss, calibration, and net benefit | Report estimate and 95% CI for every panel; interpret against the margins below |
| Router preservation | Same evaluation patients under both systems | Availability router versus robust single-model baseline within each panel | Paired Brier-score difference | Paired log-loss, AUROC, and AP differences | Non-inferior if upper 95% CI for `Brier_router - Brier_baseline` is below 0.010 |
| Router superiority | Same evaluation patients under both systems | Availability router versus robust single-model and full-panel-champion-family baselines | Paired Brier-score reduction | AP/AUROC gain and log-loss reduction | Brier reduction at least 0.005, 95% CI excludes 0, and Holm-adjusted p < 0.05; otherwise no superiority claim |
| Graceful reduced-panel performance | Same population under reduced versus full panel | Prespecified practical reduced panels versus full panel | Brier increase | AUROC/AP decrease | Brier increase no greater than 0.020 and AUROC decrease no greater than 0.050; both assessed with 95% CIs |
| Selective prediction | Eligible evaluation patients ordered by a frozen applicability/acceptance score | Accepted subset at each coverage versus 100% coverage | Change in Brier score | Log loss, AUROC, AP, subgroup coverage, and failure reasons | Direction and uncertainty reported at prespecified coverage points; no success claim if gains arise with unsupported subgroup rejection |

The 0.010 non-inferiority margin, 0.005 superiority effect, 0.020 Brier
degradation margin, and 0.050 AUROC degradation margin are development-stage
design choices. Phase 2 must compare them with the closest methodological and
clinical-prediction literature. Any revision must occur before protocol freeze,
be justified in the decision log, and never use a new final test result.

The severe two-feature panels are stress tests. They must be reported but are not
required to satisfy the practical-panel graceful-degradation criterion.

## 5. Interpretation rules

- A probability is the estimated chance of the configured recorded label in the
  relevant reference environment, not a diagnosis or guaranteed future event.
- A high AUROC with poor calibration does not justify reporting an individual
  percentage as reliable.
- Accuracy, F1, and a 0.5 cutoff are descriptive secondary results.
- Overlapping confidence intervals are not themselves a model-comparison test;
  paired differences are required.
- Failure to show superiority is not evidence that systems are equal. A bounded
  non-inferiority analysis is required for a preservation claim.
- Public benchmark results do not establish transportability or deployment
  readiness.
- Explanations describe model contributions, not causal effects.

## 6. Manuscript positioning

The conference manuscript will be framed as a multi-environment evaluation of
availability-aware calibrated prediction with explicit abstention. It will not be
framed as a universal diabetes model or another leaderboard comparison.

A journal-strength extension requires independent or temporal validation and a
reassessment of calibration, utility, subgroup coverage, and applicability in
that external setting. Claims about future onset additionally require a separate
longitudinal study design.

## 7. Freeze checklist

- [ ] Phase 2 novelty review supports or revises the primary contribution.
- [ ] Every margin has a documented scientific or decision-analytic rationale.
- [ ] Practical and severe-degradation panels are explicitly classified.
- [ ] Hospital130 inclusion/exclusion in the conference manuscript is decided.
- [ ] Mixed-router language is checked against demonstration-only boundaries.
- [ ] Every planned table and figure maps to one claim above.
- [ ] The signed protocol records the final version and immutable source/config identifier.
