# Publication Roadmap Execution Status

**Updated:** 23 August 2026

**Overall state:** In progress; final execution prohibited

| Phase | State | Completed evidence | Next gate |
|---:|---|---|---|
| 0. Baseline and governance | Complete for documentation | `Baseline_Reproducibility_Record.md`, `Decision_Log.md`, `Publication_Blocker_Register.md`, dependency snapshot, passing tests and audits | Version-control/archive, concealed-final-split, and backup controls must close before freeze |
| 1. Scientific protocol | Draft in progress | Endpoint/claim hierarchy, SAP v0.1, threshold/utility policy v0.1, draft machine-readable protocol pointers | Literature and clinical rationale review; implementation-gap tests; formal sign-off later |
| 2. Literature and novelty | In progress | Search protocol and initial 12-record seed matrix | Complete database searches, full-text extraction, closest-work comparison, and novelty sign-off |
| 3. Data/split/leakage audit | Phase 0 inventory complete; deeper audit pending | Raw hashes, row flow, deterministic seed-42 manifests | Missingness, survey design, leakage, and concealed-final-split design |
| 4. Engineering hardening | Pending | Existing 36 tests plus 5 subtests pass | Implement SAP-required inference, concealment, preflight, and artifact checks |
| 5. Development full runs and ablations | Pending | Pilot/smoke evidence only | Run only after Phase 1–4 development gates |
| 6. Selective prediction/subgroups | Pending | No signed-off artifacts | Implement and review on development evidence |
| 7. Protocol freeze | Locked out | `protocol_frozen=false`, `locked=false` | Requires all pre-final gates and immutable source identifier |
| 8. Final experiments | Prohibited | None | One authorized run after Phase 7 only |
| 9–13. Final analysis, reporting, submission, extension | Pending | Existing reports are development context | Depend on valid locked final evidence |

## Current safety decisions

- Seed-42 BRFSS and Hospital130 holdouts are development-only forever.
- No current output is eligible for a final manuscript primary-results table.
- PIDD, Sylhet, and BRFSS are analyzed separately.
- Hospital130 remains a separate readmission endpoint.
- Mixed-input routing is a software demonstration; probabilities are not fused.
- Age-of-onset prediction remains future work requiring longitudinal data.
- Publication-readiness completion flags remain false until reviewed evidence exists.

## Immediate execution queue

1. Complete the structured database searches and full-text extraction.
2. Review Phase 1 margins and threshold ranges against the resulting evidence.
3. Audit BRFSS survey-design variables and all dataset missingness/leakage risks.
4. Specify and test the fresh concealed-final-split control without accessing a final set.
5. Implement participant-aggregated repeated-CV inference and Sylhet cluster bootstrap.
6. Implement net-benefit uncertainty, ablations, selective prediction, and subgroup analysis.

Final-run commands must not be added to the active queue until the Phase 7 gate is
signed and the readiness audit has no pre-final protocol blocker.
