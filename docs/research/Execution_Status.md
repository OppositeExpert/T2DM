# Publication Roadmap Execution Status

**Updated:** 24 August 2026, conference-development completion checkpoint

**Overall state:** Machine-executable development work complete; human review,
protocol freeze, and final execution remain prohibited until authorized

| Phase | State | Completed evidence | Next gate |
|---:|---|---|---|
| 0. Baseline and governance | Complete for current development checkpoint | Reproducibility records plus local Git baseline commit `750bcff`; raw data and outputs excluded | Define immutable off-device/final-artifact backup before freeze |
| 1. Scientific protocol | Draft in progress | Endpoint/claim hierarchy, SAP v0.1, threshold/utility policy v0.1, machine-readable final lockout | Complete margin/threshold evidence review and formal sign-off later |
| 2. Literature and novelty | In progress, substantially expanded | Search protocol, 24-record matrix, closest-work comparison, novelty assessment v0.1 | Complete two-database search, extraction, and independent novelty review |
| 3. Data/split/leakage audit | Engineering and development verification complete; locked evidence review pending | Reproducible audit plus current-code BRFSS weighted performance and stratified PSU-bootstrap smoke sensitivity with 200 replicates | Review controls; repeat only on the authorized final study |
| 4. Engineering hardening | Complete for development | Outcome-blind manifest, fail-closed authorization, participant/cluster inference, resumable retraining checkpoints, paired decision-curve uncertainty, matched panels, selective prediction, subgroups, stress and leakage engines | Human review and final preflight after freeze |
| 5. Development full runs and ablations | Complete; scientific review pending | Full 5 x 5 PIDD and grouped Sylhet studies plus artifact, retraining, random-dropout, applicability, heuristic, explanation, and leakage-warning ablations | Review and record frozen decisions; do not change flags automatically |
| 6. Selective prediction/subgroups | Complete for development; review pending | Full PIDD/Sylhet development evidence and current-code BRFSS smoke evidence include risk-coverage, event coverage, subgroup uncertainty, and suppression artifacts | Human review before setting completion flags |
| 7. Protocol freeze | Locked out | `protocol_frozen=false`, `locked=false` | Requires all pre-final gates and immutable source identifier |
| 8. Final experiments | Prohibited | None | One authorized run after Phase 7 only |
| 9–13. Final analysis, reporting, submission, extension | Development conference package prepared; final substitution pending | Manuscript, supplement, crosswalks, risk-of-bias draft, handoff, generated tables/figures, and reproducibility manifest | Depend on valid locked final evidence and author/venue inputs |

## Current safety decisions

- Seed-42 BRFSS and Hospital130 holdouts are development-only forever.
- No current output is eligible for a final manuscript primary-results table.
- PIDD, Sylhet, and BRFSS are analyzed separately.
- Hospital130 remains a separate readmission endpoint.
- Mixed-input routing is a software demonstration; probabilities are not fused.
- Age-of-onset prediction remains future work requiring longitudinal data.
- Publication-readiness completion flags remain false until reviewed evidence exists.

## Immediate human and governance queue

1. Complete the independent structured-database novelty review.
2. Review margins, threshold ranges, panels, model bank, subgroup suppression,
   TRIPOD+AI, PROBAST+AI, and the claim-to-evidence crosswalk.
3. Provide author, affiliation, declaration, repository, archive, and venue inputs.
4. Approve and sign the protocol, immutable source identifier, backup/recovery
   location, and final authorization record.
5. Only then create the concealed final manifests and run each final profile once.

Final-run commands must not be added to the active queue until the Phase 7 gate is
signed and the readiness audit has no pre-final protocol blocker.
