# Conference Package

**Working title:** Availability-Aware Diabetes Screening Under Incomplete Predictor Panels: A Multi-Environment Development Study

**Package state:** Near-complete development package; not authorized for submission

**Evidence cutoff:** 30 August 2026

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
- `Conference_Cover_Letter_Draft.md`: venue-neutral cover letter requiring final
  author approval.
- `Author_and_Venue_Inputs.md`: author, declaration, and formatting fields that
  cannot be inferred from the project.
- `Claim_to_Evidence_Development_Crosswalk.md`: claim-level traceability and
  wording constraints.
- `TRIPOD_AI_Development_Crosswalk.md`: main-item reporting crosswalk and final
  sign-off procedure.
- `PROBAST_AI_Development_Assessment.md`: conservative preliminary quality,
  bias, and applicability assessment.
- `Reproducibility_and_Final_Run_Handoff.md`: regeneration commands, protected
  final-run procedure, and recovery rule.
- `Final_Authorization_Record_Template.md`: blank, non-authorizing record for
  supervisor/statistical sign-off and immutable final-run identifiers.
- `generated/`: submission-style DOCX files generated from the reviewed source.
  It also contains a machine-generated development performance table and
  provenance hashes tied to immutable study identifiers.
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
| PIDD routing, panels, ablations, selective prediction, subgroups, missingness stress, SHAP | Complete | Development decision evidence only |
| Sylhet grouped development benchmark | Complete | Development decision evidence only |
| Sylhet routing, robustness, and panel-specific retraining | Complete | Development decision evidence only |
| BRFSS full-sample development holdout | Complete (`brfss_development_holdout_56407ef53bba`) | Full development decision evidence only; seed-42 test already inspected |
| Historical BRFSS smoke verification | Preserved (`brfss_smoke_holdout_b3a6ad2aa89e`) | Engineering history only |
| BRFSS new concealed final holdout | Protected until protocol freeze and authorization | Required locked evidence |
| Hospital130 full-cohort development holdout | Complete (`hospital130_development_holdout_c3aa5fb84a7a`); separate 30-day readmission endpoint | Supporting development analysis only; never diabetes-detection or final evidence |
| Mixed-input router | Engineering complete | Software demonstration only |
| Protocol/sign-off/final run | Not authorized | Required before submission |

## Non-negotiable release rule

Submission requires signed protocol freeze, completed novelty and reporting
reviews, a concealed and authorized final run, independent artifact review, and
replacement of every development-only result with the locked result or an
explicitly labelled development analysis. Until then, the package is close to
submission form but is not a finished scientific submission.
