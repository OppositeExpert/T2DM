# Scientific evidence index

| File/directory | Why it remains active |
|---|---|
| `study_registry.json` | Four final study identities, endpoint/evidence boundaries and artifact hashes |
| `final_artifact_release_manifest.json` | 1,304 final-study/input/split/execution artifacts, including checkpoints |
| `artifact_release_manifest.json` | 1,962 development artifact hashes supporting negative findings and ongoing mentor analyses |
| `development_reference/` | Unchanged historical 20-row primary-estimand regression table and its source provenance; development only |
| `publication_correction/` | Ten original panel derivatives, two executed correction-code snapshots, original 87-entry publication checksum list and supersession mapping |
| `repository_simplification_manifest.json` | Verified local archive fingerprints, removed-path ledger and exact promotion mappings |

`publication_correction/retained_checksums.json` verifies all 14 retained support
files. The original publication checksum list is unchanged; its paths are relative
to the restored superseded package, not this support directory. Supersession-map
original/replacement paths retain their historical meaning. Current replacements
are under `results/final_publication/`; the complete original package is locally
archived. Code snapshots are provenance, not the source entrypoint to rerun.

The manifests contain hashes and paths rather than raw records, fitted models
or participant predictions. Private artifacts require approved restoration;
null archive identifiers mean no external deposit is established. See
[artifact restoration](../docs/ARTIFACT_ARCHIVING.md) and the
[results guide](../docs/RESULTS_GUIDE.md). Neither hashes nor passing tests prove
external, clinical or causal validity.
