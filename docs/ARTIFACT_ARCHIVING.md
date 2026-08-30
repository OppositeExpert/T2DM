# Artifact Preservation and External Archiving

Git preserves source, configuration, documentation, and small evidence indexes.
It intentionally excludes raw data, fitted models, row-level predictions, and
large generated study outputs. Reproducible source does not by itself preserve
the exact fitted artifacts used in a report.

After all authoritative studies and secondary analyses are complete, run:

```bash
python scripts/build_study_registry.py
python scripts/build_artifact_release_manifest.py
python scripts/verify_artifact_release_manifest.py
```

`evidence/artifact_release_manifest.json` records logical names, study IDs,
endpoints, evidence tiers, local paths, byte sizes, SHA-256 hashes, requirement
status, regeneration commands, and empty external-archive fields. Upload the
listed files to an approved immutable archive, then record its real identifier
and URI; never invent an archive location or DOI.

The release manifest enumerates every file in each authoritative study except
resumable `checkpoints/`, which are execution scratch rather than completed
evidence. Core metadata, metrics, intervals, thresholds, decision curves, and
model bundles are marked required; dependent tables, figures, and diagnostics
are marked optional so archive custodians can apply an explicit retention tier.

To verify a restored archive unpacked under another directory:

```bash
python scripts/verify_artifact_release_manifest.py \
  --artifact-root /path/to/restored/repository-root
```

Exact model bytes are only expected on the recorded platform and environment.
Cross-platform reproduction should verify contracts and metric agreement, not
promise byte-identical fitted models when numerical libraries do not guarantee it.
