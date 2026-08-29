# Tracked Evidence Metadata

`study_registry.json` is the tracked map from authoritative development claims
to ignored local artifacts. Rebuild it only after every declared study and its
secondary analyses are complete:

```bash
python scripts/build_study_registry.py
```

The registry records study IDs, endpoints, evidence tiers, commands, hashes,
artifact paths, local presence, and model bundles. It deliberately marks every
listed study ineligible for final claims. Large predictions, fitted models, and
plots remain under ignored `outputs/` and must be regenerated after a fresh
clone unless the research team provides a separately checksum-verified archive.

Study IDs include the source-tree fingerprint. Running a regeneration command
after source changes correctly creates a successor study ID instead of silently
overwriting the declared study. Exact byte-for-byte regeneration of an older
ignored study therefore also requires the source revision identified by its
recorded source hash or a separately archived source bundle. Because this task
was explicitly performed without creating a commit, the current local BRFSS
study is fully identified by hashes but still needs an immutable source/results
archive before protocol freeze.
