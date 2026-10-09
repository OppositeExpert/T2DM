# Tracked Evidence Metadata

`study_registry.json` is the tracked map from authoritative finalized
internal-validation claims to ignored local artifacts. Rebuild it only after
every declared study and its dependent analyses are complete:

```bash
python scripts/build_study_registry.py
```

The registry records study IDs, endpoints, evidence tiers, commands, hashes,
artifact paths, local presence, and model bundles. It marks the listed studies
eligible for finalized internal-validation claims while explicitly prohibiting
untouched independent-holdout wording. Large predictions, fitted models, and
plots remain under ignored `outputs/`; the checksum-verified canonical package
is under ignored `results/final_publication/`. Both require immutable external
archival for a fresh clone or release.

After rebuilding this registry, create and verify the external-archive inventory:

```bash
python scripts/build_artifact_release_manifest.py
python scripts/verify_artifact_release_manifest.py
```

The resulting tracked manifest is an inventory, not proof of upload. Its URI and
archive identifier remain empty until a real immutable archive is configured.

Study IDs include the source-tree fingerprint. Running a regeneration command
after source changes correctly creates a successor study ID instead of silently
overwriting the declared study. Exact byte-for-byte regeneration of an older
ignored study therefore also requires the source revision identified by its
recorded source hash or a separately archived source bundle. The finalized
studies are fully identified by their frozen study hashes. The documented
packaging-only successor hash does not retroactively change those studies. An
immutable source/results archive is still required before release.
