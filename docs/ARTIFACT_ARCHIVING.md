# Artifact preservation and external archiving

Git preserves implementation, contracts, tests, guides and reviewed aggregate
publication evidence. Raw records, patient/group identifiers, split assignments,
row-level predictions, model bundles, trial ledgers and resumable checkpoints
remain intact under ignored `data/raw/` and `outputs/`. Generated status does not
make a research artifact disposable.

The owner has a private complete pre-cleanup local snapshot, including Git state,
environment and all ignored files. Its location, size and checksum are recorded
in `REPOSITORY_CLEANUP_REPORT.md`. It is a local backup, not an immutable off-site
archive or a public dataset release.

`evidence/final_artifact_release_manifest.json` records current final-study and
dependency paths, sizes and SHA-256 values. It includes checkpoints to preserve
recovery options. The historical 1,962-artifact manifest remains unchanged at
`evidence/artifact_release_manifest.json`; its development scope differs from the
final registry. Verify a restored final tree with:

```bash
python scripts/verify_artifact_release_manifest.py --manifest evidence/final_artifact_release_manifest.json --artifact-root /path/to/restored/repository
```

The final manifest is an inventory, not proof of deposit. Review dataset terms
and artifact privacy, choose an approved immutable restricted archive, deposit
permitted artifacts and the complete executed source/configuration closure,
then record the real identifier and access instructions in a successor manifest.
Do not invent a DOI or upload the private snapshot wholesale. Exact final
training-source recovery is still outstanding; reference implementation excerpts
and source hashes do not replace that complete snapshot.

For public evidence, verify the tracked current/superseded packages using
`python scripts/verify_publication_results.py`. CSV, Markdown and LaTeX tables,
and PNG/PDF/SVG figures have distinct review/export uses and remain preserved.
Exact model bytes may vary across platforms; document metric tolerance rather
than promise byte-identical retraining.
