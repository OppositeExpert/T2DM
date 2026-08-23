# Publication Blocker Register

**Baseline:** 23 August 2026

**Readiness verdict:** `NOT READY`

**Blocking checks:** 19

**Journal-strength warnings:** 1

This register is the operational owner map for `outputs/publication_readiness_audit.md`. A protocol flag may change only after the acceptance evidence below exists and has been reviewed.

The count increased from 16 to 19 when the gate was strengthened to require
participant-level repeated-CV artifacts and paired decision-curve uncertainty.
This records newly enforced evidence requirements; it is not a loss of model
performance or a failed final experiment.

| ID | Readiness check | Current evidence | Status | Owner phase | Required action | Acceptance evidence |
|---|---|---|---|---:|---|---|
| BLK-001 | `brfss_final_profile` | `profile=smoke` | Open | 8 | Run the full prespecified BRFSS final profile after freeze | Final metadata reports `profile=final` |
| BLK-002 | `brfss_profile_locked` | `locked=False` | Open | 7–8 | Approve the protocol and lock the exact final configuration | Signed authorization plus final metadata `locked=true` |
| BLK-003 | `brfss_full_sample` | `sample_limit_per_partition=10000` | Open | 8 | Remove smoke sample limits in final execution | Final metadata has no sample limit and row flow matches the full cohort |
| BLK-004 | `brfss_test_access` | Smoke test path already accessed | Open, critical | 3, 4, 7–8 | Implement a new prespecified concealed final partition and access it only once after freeze | Split-control record, concealed-test preflight, and `single_locked_final_evaluation` metadata |
| BLK-005 | `pidd_final_profile` | `profile=development_pilot` | Open | 8 | Run the full final repeated nested study | Final metadata reports `profile=final` and all 25 outer evaluations |
| BLK-006 | `pidd_profile_locked` | `locked=False` | Open | 7–8 | Freeze all PIDD analysis choices before the final run | Signed authorization and final metadata `locked=true` |
| BLK-007 | `sylhet_final_profile` | `profile=development_pilot` | Open | 8 | Run the full grouped final repeated nested study | Final metadata reports `profile=final` and all grouped outer evaluations |
| BLK-008 | `sylhet_profile_locked` | `locked=False` | Open | 7–8 | Freeze Sylhet grouping, panels, models, calibration, and analysis | Signed authorization and final metadata `locked=true` |
| BLK-009 | `protocol_frozen` | `false` | Open | 1, 7 | Complete and approve the statistical analysis plan and frozen configuration | Signed/versioned SAP, blank table shells, code/config tag, flag set true |
| BLK-010 | `novelty_review_complete` | `false` | Open | 2 | Complete structured literature matrix and narrow novelty claim | Reviewed matrix, contribution statement, and flag set true |
| BLK-011 | `claim_evidence_table_complete` | `false` | Open | 9, 11 | Link every abstract/conclusion claim to frozen evidence | Reviewed claim-to-evidence table and flag set true |
| BLK-012 | `tripod_ai_checklist_complete` | `false` | Open | 11 | Complete TRIPOD+AI manuscript crosswalk | Completed checklist with page/section references and flag set true |
| BLK-013 | `probast_ai_assessment_complete` | `false` | Open | 11 | Complete PROBAST+AI risk-of-bias/applicability assessment | Reviewed assessment with evidence and flag set true |
| BLK-014 | `ablation_study_complete` | `false` | Open | 5 | Run prespecified component ablations on identical folds/budgets | Ablation protocol, results, interpretation, and flag set true |
| BLK-015 | `selective_prediction_evaluation_complete` | `false` | Open | 6 | Implement risk-coverage and abstention analysis | Coverage curves/tables, failure-reason analysis, reviewed report, flag set true |
| BLK-016 | `subgroup_analysis_complete` | `false` | Open | 6 | Report supported subgroup performance and coverage with uncertainty | Prespecified subgroup report, suppression audit, and flag set true |
| WRN-001 | `external_or_temporal_validation` | `false` | Open warning; journal blocker | 13 | Apply a frozen model to an independent or later compatible cohort | External/temporal validation report and flag set true |

## Cross-cutting controls discovered during Phase 0

| Control ID | Issue | Required before | Action |
|---|---|---|---|
| CTRL-001 | Local version-control baseline now exists at `750bcff`; frozen tag/archive absent | Protocol freeze | Create reviewed frozen commit/tag and immutable archive at sign-off |
| CTRL-002 | Outcome-blind manifest and authorization guard implemented on development partitions; fresh final split not created | Final holdout generation | Review control tests, then create a different prespecified final split only after freeze |
| CTRL-003 | Default Matplotlib cache is unwritable | Development full runs | Standardize `MPLCONFIGDIR=outputs/.matplotlib` in runbook/preflight |
| CTRL-004 | Final artifacts currently have no immutable backup policy | Final run | Define archive, checksum, and recovery procedure |
| CTRL-005 | Final profile is unlocked | Protocol freeze | Keep unlocked until every pre-final gate passes |

## Update rules

- `Open` means no reviewed acceptance evidence exists.
- `Implemented, awaiting review` means the artifact exists but has not been signed off.
- `Closed` requires the acceptance evidence and a passing readiness-gate result where applicable.
- Do not close a blocker solely because code exists or a pilot analysis ran.
- Record the closing artifact path and date in this file when status changes.

## 23 August 2026 implementation evidence

- CTRL-001 development baseline: Git commit `750bcff`.
- CTRL-002 control test: `python -m diabetes_pipeline.cli test-concealment`
  succeeded for BRFSS and Hospital130 seed-42 development partitions. Persisted
  manifests/metadata were outcome-blind and checksum-valid.
- Phase 4 decision-curve control: nested and holdout runners now write pointwise
  net-benefit confidence intervals and paired model contrasts using identical
  individual or complete-cluster resamples across models. Development smoke
  verification succeeded for PIDD and BRFSS; final evidence remains prohibited.
- Phase 3 BRFSS survey control: `brfss-survey-sensitivity` maps held-out row IDs
  back to `_LLCPWT`, `_STSTR`, and `_PSU`, reports weighted point estimates, and
  uses shared stratified PSU replicate weights. A 200-replicate development smoke
  run passed; full-study review is still required before any population wording.
- Phase 4 panel-degradation control: `matched-panel-contrasts` holds model family
  and participants fixed, averages repeated held-out probabilities per person,
  preserves Sylhet profile clusters, and applies metric-wise Holm correction.
  PIDD, Sylhet, and BRFSS development paths passed; final claims remain blocked.
- Phase 5 artifact ablations: paired calibration, router-baseline, selector-metric,
  and model-family evaluators passed for PIDD/Sylhet; BRFSS correctly records its
  missing Logistic Regression baseline. BLK-014 remains open for retraining,
  random-dropout, applicability, and leakage-demonstration components.
- Phase 5 missing-indicator retraining: indicator-on and indicator-off variants
  now use identical outer/inner folds, budgets, search spaces, model families,
  and seeds with separate tuning. PIDD individual and Sylhet cluster smoke and
  five-fold development-pilot paths passed. A numerical-equivalence guard
  prevents machine-precision noise from becoming false significance. BLK-014
  remains open until the remaining ablations are completed and reviewed.
- Phase 5 panel-specific retraining: Random Forest and XGBoost were separately
  tuned and calibrated for every reduced PIDD and Sylhet panel and compared with
  masked full-panel inference on identical participants. No Holm-corrected
  advantage remained. BLK-014 stays open for the remaining stress and warning
  ablations.
- Phase 6 selective prediction and subgroups: outcome-blind probability-certainty
  coverage analysis, positive-event retention, group-preserving acceptance,
  subgroup bootstrap uncertainty, and small-cell suppression are implemented.
  PIDD/Sylhet pilots and BRFSS smoke passed; BLK-015 and BLK-016 remain open until
  full-development evidence is reviewed.
- Phase 5 missingness stress: shared MCAR-like and structured-block masks at four
  severity levels passed on PIDD and Sylhet pilots. Severe dropout materially
  worsened Brier/AP and reduced named-panel coverage below 7%, supporting
  applicability guards. BLK-014 remains open for guard, heuristic, explanation,
  and leakage-warning components.
- Final access remains denied because protocol, final profile, final seed,
  authorization record, and final manifest fields are deliberately unset.
