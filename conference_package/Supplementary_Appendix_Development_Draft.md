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
Panel-specific retraining is recorded in the package handoff until its active
full-budget run finishes.

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

Selective probability-certainty acceptance improved retained-case Brier score as
coverage decreased, but retained positive events less often than negative cases.
Age-group coverage was heterogeneous and the oldest group was too small for
stable performance estimation. Severe simulated missingness raised probability
loss and left fewer than 7% of participants compatible with a named panel. These
results favour explicit abstention over extrapolation.

## S8. Reporting and risk-of-bias controls

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

## S9. Reproducibility artifact map

| Artifact | Location |
|---|---|
| Development configuration | `config/experiments/development.yaml` |
| Publication controls | `config/publication_protocol.yaml` |
| Statistical analysis plan | `docs/research/Statistical_Analysis_Plan.md` |
| Endpoint hierarchy | `docs/research/Endpoint_and_Claim_Hierarchy.md` |
| Leakage/applicability audit | `docs/research/Data_Leakage_and_Applicability_Audit.md` |
| Decision log | `docs/research/Decision_Log.md` |
| PIDD development study | `outputs/publication_pipeline/studies/pidd_development_072cd2104089` |
| Command reference | `docs/RUNBOOK.md` |
| Automated tests | `tests/` |

## S10. Items reserved for locked evidence

- Final participant-flow counts and exclusions for every primary environment.
- Full-budget grouped Sylhet and BRFSS development decision tables.
- Frozen model/panel choices and justified non-inferiority margins.
- Authorized concealed final estimates and 2,000-resample intervals.
- Final decision curves, calibration plots, subgroup tables, and claim-evidence map.
- Repository release tag, archive DOI, author list, affiliations, funding,
  conflicts, ethics wording, and venue-specific formatting.
