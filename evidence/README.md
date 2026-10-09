# Evidence indexes

The aggregate publication package is now tracked under
`results/final_publication/`. `study_registry.json` maps the four finalized
internal-validation studies to private local artifacts; its recorded presence
flags reflect its generation date and must not be read as proof of external
upload. Frozen metadata is preserved unchanged.

| Inventory | Scope |
|---|---|
| `artifact_release_manifest.json` | Historical development snapshot: 1,962 artifacts, retained unchanged |
| `final_artifact_release_manifest.json` | Cleanup-time inventory of final study artifacts and input/split/execution dependencies, including checkpoints; hashes only |
| `docs/audits/repository-cleanup-2026-10-09/file_classification.csv.gz` | Every original local file, category, purpose, reference evidence, retention decision and SHA-256 |

Verify without regenerating or overwriting results:

```bash
python scripts/verify_publication_results.py
python scripts/verify_artifact_release_manifest.py --manifest evidence/final_artifact_release_manifest.json
```

The second command needs restored private artifacts. Empty archive URI/identifier
fields mean no immutable deposit is recorded. A manifest never replaces the
models, predictions, raw inputs, splits or exact executed source. The complete
private local pre-cleanup snapshot is documented in the cleanup report; it must
not be published because it includes raw and row-level data.

`scripts/build_study_registry.py` and `build_artifact_release_manifest.py` are
retained builders that write tracked indexes. Their defaults do not preserve an
older manifest automatically. Do not rerun them over historical indexes; prepare
successor inventories in a separate working copy and review the evidence scope.
See [ARTIFACT_ARCHIVING.md](../docs/ARTIFACT_ARCHIVING.md).
