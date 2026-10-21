# BRFSS Final Evaluation Decision

**Decision:** `BRFSS_FINAL_STRATEGY = INTERNAL_VALIDATION_ONLY`

**Decision date:** 10 September 2026

## Scope and endpoint

BRFSS remains a separate diabetes-status/screening cohort with the endpoint
`self_reported_diagnosed_diabetes`. It is not pooled with PIDD, Sylhet, or the
Hospital130 readmission task.

## Evidence reviewed

The raw BRFSS source contains 429,360 target-valid respondents after the
prespecified target exclusions. The authoritative seed-42 split contains
343,488 development respondents and 85,872 evaluation respondents. The labels,
predictions, metrics, calibration results, model comparisons, availability
results, subgroup results, and manuscript-facing summaries from that 85,872-row
partition have already been inspected during development.

The repository contains no separately acquired temporal, geographic, or
externally custodied BRFSS cohort whose labels remained inaccessible throughout
development. All records in the local raw cohort were available to earlier data
audits, and decisions about models, feature definitions, panels, calibration,
thresholds, routing, and reporting were made after access to results from the
seed-42 partition.

## Why an untouched holdout is not defensible

Carving a new random partition from the same fully accessed cohort would change
only the random assignment. It would not undo the prior influence of cohort
labels and observed evaluation results on downstream choices. Such a partition
could support a locked reanalysis, but calling it genuinely unseen or
independent would overstate the evidence.

Accordingly, the project retains the deterministic seed-42 partition for
reproducible, paired finalized internal validation. The 75-trial/2,000-bootstrap
execution is a prespecified reanalysis of an accessed cohort. Its outputs must
use the evidence tier `final_internal_validation` and evaluation role
`locked_internal_validation`; exporters must reject any independent-final-test
label for these artifacts.

## Consequences for reporting

- BRFSS results may be reported as finalized internal-validation estimates.
- The 85,872-row evaluation partition must never be called an untouched,
  independent, external, prospective, or temporal test set.
- Hyperparameters, calibrators, thresholds, panels, and comparison rules are
  frozen before the finalized reanalysis and must not be changed in response to
  the new outputs.
- The limitations section must state that development and finalized internal
  validation used one previously accessed public cohort.
- Independent validation remains future work and is required before
  transportability or clinical-generalization claims.

This decision is encoded in `config/final_publication_protocol.yaml` and is a
hard publication-export validation rule.
