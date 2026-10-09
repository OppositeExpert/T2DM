# Publication Roadmap Execution Status

> **Superseded 11 September 2026:** this file records the earlier development
> roadmap. Final full-budget internal validation is now complete under
> `config/final_publication_protocol.yaml`; current status is summarized in
> `PUBLICATION_READINESS.md` and `results/final_publication/FINAL_RESULTS.json`.
> The historical false flags and concealed-holdout plan below are retained only
> for provenance and must not be used as the current experimental status.

**Updated:** 30 August 2026, full Hospital130 development and release-hardening checkpoint

**Overall state:** Machine-executable development work complete; human review,
protocol freeze, and final execution remain prohibited until authorized

| Phase | State | Completed evidence | Next gate |
|---:|---|---|---|
| 0. Baseline and governance | Complete for current development checkpoint | Base revision `99ff8fa`; data-source manifest, exact environment lock, tracked study registry, and ignored-artifact policy | Upload the verified artifact manifest to an approved immutable archive before freeze |
| 1. Scientific protocol | Draft in progress | Endpoint/claim hierarchy, SAP v0.1, threshold/utility policy v0.1, machine-readable final lockout | Complete margin/threshold evidence review and formal sign-off later |
| 2. Literature and novelty | In progress, substantially expanded | Search protocol, 24-record matrix, closest-work comparison, novelty assessment v0.1 | Complete two-database search, extraction, and independent novelty review |
| 3. Data/split/leakage audit | Engineering and development verification complete; locked evidence review pending | Reproducible audits plus full BRFSS survey-weighted performance and 500-replicate stratified PSU-bootstrap sensitivity | Review controls; repeat only on the authorized final study |
| 4. Engineering hardening | Complete for development and final preflight | Outcome-blind manifests, separate split-creation authorization, data/manifest/config/record hash binding, one-way access receipt, resumable checkpoints, paired inference, routing and abstention | Human review and read-only final preflight after freeze |
| 5. Development full runs and ablations | Complete; scientific review pending | Full PIDD, grouped Sylhet, 429,360-row BRFSS, and patient-grouped Hospital130 studies; all supported endpoint-appropriate secondary paths | Review and record frozen decisions; do not change flags automatically |
| 6. Selective prediction/subgroups | Complete for development; review pending | Full PIDD/Sylhet/BRFSS/Hospital130 development evidence includes risk-coverage, event coverage, subgroup uncertainty, and suppression artifacts | Human review before setting completion flags |
| 7. Protocol freeze | Locked out | `protocol_frozen=false`, `locked=false` | Requires all pre-final gates and immutable source identifier |
| 8. Final experiments | Prohibited | None | One authorized run after Phase 7 only |
| 9–13. Final analysis, reporting, submission, extension | Development conference package prepared; final substitution pending | Manuscript, supplement, crosswalks, risk-of-bias draft, handoff, generated tables/figures, and reproducibility manifest | Depend on valid locked final evidence and author/venue inputs |

## Current safety decisions

- Seed-42 BRFSS and Hospital130 holdouts are development-only forever.
- No current output is eligible for a final manuscript primary-results table.
- PIDD, Sylhet, and BRFSS are analyzed separately.
- Hospital130 remains a separate readmission endpoint.
- The authoritative Hospital130 study is
  `hospital130_development_holdout_c3aa5fb84a7a`; its seed-42 development-test
  role is permanently ineligible as a concealed final test.
- Mixed-input routing is a software demonstration; probabilities are not fused.
- Age-of-onset prediction remains future work requiring longitudinal data.
- Publication-readiness completion flags remain false until reviewed evidence exists.
- The authoritative BRFSS development study is
  `brfss_development_holdout_56407ef53bba`; its full test role is not a concealed
  final test merely because its sample limit is null.

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
