# Block K Checkpoint: Research-Grade Audit and Claim Control

## Verdict

The implementation is a serious research prototype, but the current evidence
package is **not ready for paper submission**. The automated audit reports 16
blocking checks and one journal-strength warning after the research-grade
safeguards added in this block.

Passing unit tests and producing calibrated percentages are not sufficient for
a clinical-prediction paper. The final experimental protocol, analysis set,
claims, reporting checklist, and bias assessment are separate deliverables.

## Safeguards added

- Router bundles record their study profile, evidence tier, and whether they
  are eligible for publication claims.
- Patient reports explicitly distinguish execution/development evidence from a
  future final locked study.
- Mixed PIDD/Sylhet/BRFSS inference abstains when multiple environments are
  eligible unless the environment is explicitly supplied.
- The unvalidated automatic environment heuristic requires an explicit
  experimental opt-in and is excluded from efficacy claims.
- A machine-readable publication gate checks study profiles, locks, sample
  limits, test access, required artifacts, protocol status, ablations,
  selective-prediction analysis, subgroup analysis, claim traceability,
  TRIPOD+AI, and PROBAST+AI.
- The paper thesis is narrowed to availability-aware calibrated degradation and
  abstention. Dynamic algorithm selection is retained as a secondary negative
  result because current gains are small and unstable.

## Current blocking evidence

1. BRFSS is a 10,000-row-per-partition smoke run, not a full final analysis.
2. PIDD and Sylhet use reduced-budget development pilots.
3. No primary profile is final and locked.
4. The statistical protocol and novelty review are not frozen/completed.
5. The ablation, risk-coverage, and subgroup analyses are incomplete.
6. The claim-evidence table, TRIPOD+AI checklist, and PROBAST+AI assessment are
   incomplete.
7. No external or temporal validation has been completed.

The current audit is saved at `outputs/publication_readiness_audit.md`.

## Empirical claim decision

The PIDD development study does not support a headline claim that dynamic model
selection improves prediction. Router gains over strong fixed baselines are
small, inconsistent across panels, and not significant after multiplicity
correction. Sylhet shows some favorable panel estimates, but only five grouped
folds and unstable/extreme calibration parameters prevent a strong selection
claim. BRFSS routing is smoke-only.

Accordingly, the defensible conference-paper direction is:

> Quantify discrimination and calibration degradation across prespecified
> feature-availability environments; retain calibrated probabilities,
> provenance, explanations, and explicit abstention; report model switching as
> a negative feasibility result unless the locked final evidence changes it.

## Reporting standards

- TRIPOD+AI: BMJ 2024;385:e078378, doi:10.1136/bmj-2023-078378.
- PROBAST+AI: BMJ 2025;388:e082505, doi:10.1136/bmj-2024-082505.

The protocol file records checklist completion as false until a signed-off
crosswalk and assessment exist. These flags must never be changed just to make
the gate green.
