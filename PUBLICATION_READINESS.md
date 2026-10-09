# Publication Readiness

**Experimental verdict (11 September 2026):** ready for manuscript update from
finalized internal-validation evidence.

The canonical package is [`results/final_publication/`](results/final_publication/).
Start with:

- [`FINAL_RESULTS.json`](results/final_publication/FINAL_RESULTS.json) for the
  machine-readable source of truth;
- [`FINAL_RESULTS_SUMMARY.md`](results/final_publication/FINAL_RESULTS_SUMMARY.md)
  for the claim-bounded human summary;
- [`FINAL_DATA_LEAKAGE_AUDIT.md`](results/final_publication/audits/FINAL_DATA_LEAKAGE_AUDIT.md)
  for the passing end-to-end leakage audit;
- [`checksums.json`](results/final_publication/provenance/checksums.json) for
  package integrity.

All four endpoint-separated studies use the frozen
`t2dm-final-internal-validation-v1` protocol, five model families, 75 Optuna
trials per applicable model/fold, 2,000 bootstrap replicates, and unrestricted
final sample budgets. BRFSS is `INTERNAL_VALIDATION_ONLY`; Hospital130 is
`COMPLETE_FULL_INTERNAL_VALIDATION` and remains a separate 30-day-readmission
endpoint. No result is described as untouched independent, external, temporal,
prospective, clinical, or causal validation.

Dynamic model-family switching did not establish multiplicity-corrected
superiority over robust fixed comparators. That negative result is retained in
the master result and summary.

The finalized studies remain bound to their frozen study-source hash. A
post-execution packaging-only repair is disclosed in the package and records a
separate packaging-source hash; it changed no scientific artifact.

Remaining submission work is non-experimental: update the manuscript from the
canonical package, complete author/independent-reviewer sign-off, venue-specific
TRIPOD+AI/PROBAST+AI checks, licensing/data-use review, and immutable archival.
External or temporal validation remains a limitation, not a completed claim.
