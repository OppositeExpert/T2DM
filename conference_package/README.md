# Conference Package

**Working title:** Availability-Aware Diabetes Screening Under Incomplete Predictor Panels: A Multi-Environment Development Study

**Package state:** Near-complete development package; not authorized for submission

**Evidence cutoff:** 24 August 2026

This directory assembles the engineering, analysis, and reporting material for a
conference submission. It is intentionally labelled as development evidence.
The protocol is not frozen, final execution is not authorized, and no result in
this package should be relabelled as a locked final result.

## Contents

- `Conference_Manuscript_Development_Draft.md`: concise conference-paper draft.
- `Supplementary_Appendix_Development_Draft.md`: extended methods, metrics,
  ablations, applicability rules, and artifact map.
- `Submission_Readiness_and_Handoff.md`: exact completion state, human gates,
  final-run sequence, and submission checklist.
- `generated/`: submission-style DOCX files generated from the reviewed source.
- `qa/`: internal render and accessibility checks; not submission material.

## Scientific scope

PIDD, Sylhet, and BRFSS are analysed as separate diabetes-status environments.
Their probabilities are never pooled. Hospital130 predicts 30-day readmission
and is therefore excluded from the primary diabetes-screening efficacy claim.
Mixed namespaced input is a software demonstration that selects an eligible
cohort expert or abstains; it is not a learned universal diabetes model.

The primary contribution is the evaluation of calibrated performance under
prespecified feature availability, with explicit applicability checks,
abstention, paired uncertainty, and full routing provenance. Algorithm switching
is a secondary negative or inconclusive result unless locked evidence later
satisfies the prespecified superiority rule.

## Current evidence state

| Component | State | Submission use |
|---|---|---|
| PIDD 5 x 5 nested development benchmark | Complete | Development decision evidence only |
| PIDD routing, panels, ablations, selective prediction, subgroups, missingness stress, SHAP | Complete or executing as recorded in the handoff | Development decision evidence only |
| Sylhet grouped development benchmark and dependent analyses | Pending full-budget refresh | Pilot evidence only until refreshed |
| BRFSS full development holdout and dependent analyses | Pending compute-reviewed run | Smoke/engineering evidence only |
| Hospital130 | Engineering complete; separate endpoint | Supplementary methodological analysis only |
| Mixed-input router | Engineering complete | Software demonstration only |
| Protocol/sign-off/final run | Not authorized | Required before submission |

## Non-negotiable release rule

Submission requires signed protocol freeze, completed novelty and reporting
reviews, a concealed and authorized final run, independent artifact review, and
replacement of every development-only result with the locked result or an
explicitly labelled development analysis. Until then, the package is close to
submission form but is not a finished scientific submission.
