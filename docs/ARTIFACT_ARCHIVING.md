# Local preservation and artifact restoration

Raw data, patient/group identifiers, split assignments, row-level predictions,
fitted models, trial ledgers and checkpoints remain intact under ignored
`data/raw/` and `outputs/`. Generated status does not make scientific evidence
disposable. Never use broad ignored-file cleanup commands on this project.

The owner's verified historical archives are outside the repository at
`../T2DM-local-archives/2026-10-09-simplification/`. They contain the complete
465-file pre-simplification tracked state and a dedicated complete conference
package. Every archived member was verified against its original SHA-256; the
[simplification report](../REPOSITORY_SIMPLIFICATION_REPORT.md) and
`evidence/repository_simplification_manifest.json` record archive checksums and
path mappings. Original untracked historical files also remain on the owner's
computer. A separate full private snapshot including raw data, outputs and Git
exists at `../T2DM-preservation/2026-10-09/complete-local-state.tar`.
These are local backups, not off-site or immutable deposits. Do not upload the
full private snapshot to GitHub.

## Active scientific inventories

- `evidence/final_artifact_release_manifest.json`: 1,304 final-study artifacts and
  input/split/execution dependencies, including resumable checkpoints.
- `evidence/artifact_release_manifest.json`: 1,962 development artifacts; retained
  because mentor ablations and negative findings still depend on this evidence.
- `evidence/study_registry.json`: final-study identities, hashes and claim boundary.
- `evidence/publication_correction/`: unique original panel derivatives, executed
  correction-source snapshots, supersession mapping and original fingerprints.

Verify approved restored private artifacts with:

```bash
python scripts/verify_artifact_release_manifest.py --manifest evidence/final_artifact_release_manifest.json --artifact-root /path/to/restored/repository
```

No external archive URI/DOI is established. Review data terms/privacy, recover the
complete executed source/configuration closure, deposit permitted artifacts in
an approved immutable restricted archive and record the real access information
in a successor manifest. Do not overwrite frozen records or invent identifiers.

## Historical publication verification

A fresh clone verifies 101 current frozen fingerprints plus 14 retained correction
support files. To additionally verify all 87 original historical fingerprints,
restore the preserved superseded package into a separate directory and run:

```bash
python scripts/verify_publication_results.py --historical-results-root /path/to/restored/results/final_publication/superseded_pre_protocol_correction/2026-10-03
```

The explicit historical option fails if requested files are missing or changed.
No historical conference file is required for portable tests or current result
verification. Old paths inside immutable provenance records are historical
identities; the retained mapping and local archive resolve them.
