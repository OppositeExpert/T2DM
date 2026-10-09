# Reproducibility and verification

A clone contains source, configuration, tests, aggregate publication results and
provenance indexes. It does **not** contain raw data, fitted models, row-level
predictions or split assignments. Verifying fingerprints is different from
retraining a model or independently validating a scientific claim.

## Environment and installation

The reference interpreter is CPython 3.12.0; the package accepts 3.12.x. The
48-distribution lock was resolved on macOS arm64. From the repository root:

```bash
python3.12 -m venv .venv-pipeline
source .venv-pipeline/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python scripts/verify_environment.py
```

Use an editable installation in a source checkout. Configuration is resolved
relative to that checkout; standalone wheel installation outside a checkout is
not a supported reproduction path. Do not copy another checkout's environment:
editable-install metadata embeds its source path. Numerical libraries and CPU
architecture can prevent byte-identical fitted artifacts across platforms.

## Safe checks in a fresh clone

```bash
python -m pytest -q -m "not local_research_data"
python scripts/verify_publication_results.py
python -m diabetes_pipeline.cli --help
```

The checksum verifier reads the current and superseded publication manifests;
it does not load patient records or rewrite tables. CI runs all data-independent tests, source compilation, feature-map validation
and publication verification. Seven checks carry the `local_research_data` marker because they require raw
cohort files or historical study artifacts. After acquisition and restoration,
run `python -m pytest -q` for the complete suite.
The feature-map command writes a generated dictionary under ignored `outputs/`.

## Raw data

Follow [DATA_ACQUISITION.md](DATA_ACQUISITION.md) for the four official-source
records, exact filenames, download/conversion procedures and licensing limits.
Verify an existing local data directory without downloading:

```bash
python scripts/acquire_data.py --dataset all
```

All four hashes are bound in `config/data_sources.yaml` and the frozen protocol.
Raw data remains excluded from Git. Hospital130 uses patient groups and a
30-day-readmission endpoint; it is not another diabetes-status cohort.

## Restore recorded study artifacts

[evidence/README.md](../evidence/README.md) distinguishes the historical
`artifact_release_manifest.json` from `final_artifact_release_manifest.json`.
The latter inventories the retained final studies and dependencies, including
checkpoints; both manifests have truthful unfilled archive-location fields.
Obtain artifacts through an approved restricted channel and restore their
relative paths under the source checkout. Then run:

```bash
python scripts/verify_artifact_release_manifest.py --manifest evidence/final_artifact_release_manifest.json
```

For a separate restored tree, add `--artifact-root /path/to/restored/repository`.
A manifest is not proof of external deposit. No public artifact archive or DOI
has been created by cleanup. A private full local snapshot exists for the owner;
it contains raw/row-level records and must not be uploaded to GitHub.

## What the current results reproduce

The locked `t2dm-final-internal-validation-v1` record uses five models, 75 Optuna
trials per applicable model/fold and 2,000 bootstrap resamples. PIDD/Sylhet use
repeated nested evaluation, with Sylhet profile grouping. BRFSS and Hospital130
use historical partitions reported as internal validation, with Hospital130
patient-cluster inference. No untouched independent final test is claimed.

The October correction provenance distinguishes participant-mean probability
aggregation, Sylhet profile-cluster uncertainty, fixed-panel stress evaluation
and actual runtime fallback. See [RESULTS_GUIDE.md](RESULTS_GUIDE.md).

Exact retraining remains limited: the recorded training-source fingerprint is
`7d5347cf4c10e50dceb201ad36527f6d1c3e2770bba364c15c9093bf97cc6a94`;
current source includes later governance/packaging corrections. An exact complete
training-source snapshot has not been demonstrated in Git. Historical study
metadata also contains absolute paths that require controlled restoration or
path adaptation in a new working copy. Do not rewrite historical metadata/hashes
to make it appear portable, or bypass source-binding and single-use receipts.

## Development and further analyses

[RUNBOOK.md](RUNBOOK.md) preserves the supported development command catalogue.
Training, routing, ablation and export commands can be expensive and can write
into study directories. Run them only in a separate working checkout with fresh
output paths and an agreed analysis plan. Existing locked studies and the
canonical publication package are evidence, not scratch space.

`python scripts/run_final_internal_validation.py --help` documents the final
orchestrator. Its `--study-dir` mode runs dependent analyses and writes outputs;
it is not a read-only verifier. Export/correction scripts likewise write results.
Cleanup executed none of these workflows. Do not replay finalized training or
change protocol authorization to make a check pass.

Panel-specific retraining and missing-indicator retraining currently support
unlocked nested-CV development studies. Locked profiles and BRFSS/Hospital130
holdout studies are not supported by those retraining paths. Calibration,
model-family, matched-panel, selective, subgroup and runtime-policy code remains
preserved. The mentor-analysis gaps are listed in [CONTRIBUTING.md](../CONTRIBUTING.md).

An optional CPU container is defined by `Dockerfile`. Container build/run and a
fresh network installation of every locked dependency were not established by
this local cleanup; consult the cleanup report for executed checks.
