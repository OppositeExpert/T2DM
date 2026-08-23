# Publication Roadmap Execution Status

**Updated:** 23 August 2026, Phase 2–4 checkpoint

**Overall state:** In progress; final execution prohibited

| Phase | State | Completed evidence | Next gate |
|---:|---|---|---|
| 0. Baseline and governance | Complete for current development checkpoint | Reproducibility records plus local Git baseline commit `750bcff`; raw data and outputs excluded | Define immutable off-device/final-artifact backup before freeze |
| 1. Scientific protocol | Draft in progress | Endpoint/claim hierarchy, SAP v0.1, threshold/utility policy v0.1, machine-readable final lockout | Complete margin/threshold evidence review and formal sign-off later |
| 2. Literature and novelty | In progress, substantially expanded | Search protocol, 24-record matrix, closest-work comparison, novelty assessment v0.1 | Complete two-database search, extraction, and independent novelty review |
| 3. Data/split/leakage audit | Engineering complete; full evidence review pending | Reproducible audit plus BRFSS weighted performance and stratified PSU-bootstrap sensitivity path, smoke-validated with 200 replicates | Run/review the survey sensitivity on the later full development study; retain all dataset controls |
| 4. Engineering hardening | In progress | Outcome-blind manifest format, fail-closed final authorization, participant-level repeated-CV inference, Sylhet cluster bootstrap, paired decision-curve uncertainty | Matched panel contrasts, ablations, selective prediction, subgroup engine, final preflight |
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

1. Complete the structured database searches, extraction, and independent novelty review.
2. Review Phase 1 margins and threshold ranges against the resulting evidence.
3. Review the BRFSS survey sensitivity on the later full development study.
4. Implement reduced-panel/full-panel contrasts on matched patients and folds.
5. Implement ablations, selective prediction, subgroup analysis, and final preflight.
6. Define the immutable final-artifact backup and recovery procedure.

Final-run commands must not be added to the active queue until the Phase 7 gate is
signed and the readiness audit has no pre-final protocol blocker.
