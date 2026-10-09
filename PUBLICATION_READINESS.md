# Publication evidence and remaining release work

The current tracked package is
[`results/final_publication/`](results/final_publication/), including finalized
internal-validation results and the October 2026 protocol-summary corrections.
Start with the [results guide](docs/RESULTS_GUIDE.md),
[master JSON](results/final_publication/FINAL_RESULTS.json),
[summary](results/final_publication/FINAL_RESULTS_SUMMARY.md),
[frozen protocol](results/final_publication/provenance/frozen_protocol.yaml) and
[correction provenance](results/final_publication/provenance/protocol_correction.json).

The four studies retain separate endpoints, five models, 75 Optuna trials per
applicable model/fold and 2,000 bootstrap replicates. BRFSS is internal validation
only; Hospital130 remains patient-grouped 30-day readmission. No untouched,
external, temporal, prospective, clinical or causal validation is claimed.
Dynamic model-family switching did not establish consistent multiplicity-corrected
superiority. Historical development findings and superseded summaries remain
available for comparison.

Cleanup verifies preservation and engineering checks; it does not certify
journal acceptance or independent scientific review. Remaining work includes:

- Author-approved Discover Computing manuscript-to-table reconciliation,
  declarations, authorship and venue-specific reporting checks.
- Mentor-requested additional analyses within a successor analysis plan; see
  [CONTRIBUTING.md](CONTRIBUTING.md) for implemented paths and gaps.
- Complete executed training-source recovery and approved immutable artifact
  archival with truthful access information.
- A software-license decision and approved author list for `CITATION.cff`.

Frozen records retain the earlier journal name and historical source fingerprints.
Do not rewrite them to match current submission metadata. See the
[cleanup report](REPOSITORY_CLEANUP_REPORT.md) for executed validation and remaining
portability, archival and manuscript limits.
