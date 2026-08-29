# Clean-Clone Reproducibility

This document separates deterministic engineering reproduction from scientific
authorization. It reproduces smoke and development evidence. It does not grant
permission to create or inspect a protected final outcome.

## 1. Create the exact environment

The tested reference interpreter is CPython 3.12.0; Python 3.12.x is supported.
The lock was resolved on macOS arm64. Linux CPU runs should use the same package
versions, but compiled numerical libraries, thread scheduling, and model-library
implementations can prevent byte-identical model files across operating systems
or architectures even when metrics agree within numerical tolerance.

```bash
python3.12 -m venv .venv-pipeline
source .venv-pipeline/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python scripts/verify_environment.py
```

Do not copy a virtual environment from another checkout. Editable environments
embed an absolute source path; the previously copied local environment pointed
at the historical `XGBoost` repository and caused test discovery/import failures.

## 2. Acquire and verify data

Follow `docs/DATA_ACQUISITION.md`, then require this command to pass:

```bash
python scripts/acquire_data.py --dataset all
```

## 3. Validate contracts and manifests

```bash
export MPLCONFIGDIR=outputs/.matplotlib
python -m pytest -q
python -m diabetes_pipeline.cli feature-map
python -m diabetes_pipeline.cli block-a --dataset all --seed 42
python -m diabetes_pipeline.cli research-audit --seed 42
python -m diabetes_pipeline.cli test-concealment --dataset brfss --seed 42
python -m diabetes_pipeline.cli test-concealment --dataset hospital130 --seed 42
```

The seed-42 concealment commands are control tests on development partitions.
They do not create new final evidence.

## 4. Reproduce authoritative development studies

PIDD and grouped Sylhet use the full `development` profile:

```bash
python -m diabetes_pipeline.cli benchmark --dataset pidd --profile development
python -m diabetes_pipeline.cli benchmark --dataset sylhet --profile development
```

BRFSS uses the entire seed-42 development/test structure as explicitly
development-only evidence. That test role was inspected previously and is
permanently ineligible to become a concealed final test:

```bash
python -m diabetes_pipeline.cli benchmark-holdout \
  --dataset brfss --profile development \
  --models logistic_regression random_forest xgboost lightgbm catboost
```

The holdout runner checkpoints each completed development model under the
study's `checkpoints/development_models/` directory. Repeating the identical
command resumes only checkpoints tied to the same experiment identifier,
dataset configuration, raw-data hash, split-manifest hash, profile, model bank,
and source tree.

## 5. Reproduce BRFSS secondary development analyses

The completed authoritative development identifier is
`outputs/publication_pipeline/studies/brfss_development_holdout_56407ef53bba`.
Use that path as `<BRFSS_STUDY>` below:

```bash
python -m diabetes_pipeline.cli evaluate-routing --dataset brfss --study-dir <BRFSS_STUDY>
python -m diabetes_pipeline.cli matched-panel-contrasts --study-dir <BRFSS_STUDY>
python -m diabetes_pipeline.cli artifact-ablations --study-dir <BRFSS_STUDY>
python -m diabetes_pipeline.cli selective-prediction --study-dir <BRFSS_STUDY>
python -m diabetes_pipeline.cli subgroup-analysis --study-dir <BRFSS_STUDY>
python -m diabetes_pipeline.cli brfss-survey-sensitivity --study-dir <BRFSS_STUDY> --n-bootstrap 500 --seed 42
python -m diabetes_pipeline.cli explain-holdout --dataset brfss --study-dir <BRFSS_STUDY> --maximum-samples-per-model 1000
python scripts/verify_holdout_bundles.py --study-dir <BRFSS_STUDY>
```

The missing-indicator, panel-specific retraining, missingness-stress, and
reporting-ablation runners currently support repeated nested-CV studies, not
holdout studies. The artifact-based calibration, routing, selector, model-family,
matched-panel, selective-prediction, subgroup, survey, and held-out SHAP paths
are the supported BRFSS analyses.

## 6. Regenerate the development conference package and readiness audit

```bash
python scripts/build_development_evidence_snapshot.py
python scripts/build_conference_package.py
python scripts/build_conference_manifest.py
python -m diabetes_pipeline.cli publication-readiness \
  --study-dir outputs/publication_pipeline/studies/pidd_development_072cd2104089 \
  --study-dir outputs/publication_pipeline/studies/sylhet_development_b52477910fe6 \
  --study-dir <BRFSS_STUDY> \
  --format markdown --output outputs/publication_readiness_audit.md
```

The readiness audit is expected to remain `NOT READY` until the human and
scientific gates in `FINAL_RUN_CHECKLIST.md` are satisfied. Never change flags
merely to make the audit pass.

## 7. Read-only final preflight

This command computes the current raw-data and executable-analysis fingerprints
without loading outcomes. It is expected to exit with status 2 and report
`authorized: false` until the checklist is completed:

```bash
python scripts/final_preflight.py --dataset brfss
```

Use the same command with `pidd` or `sylhet` for their authorization-gated final
repeated-CV profiles; those datasets do not use a concealed holdout manifest.

The future split-creation and final-execution procedures are deliberately
separate. Follow `FINAL_RUN_CHECKLIST.md`; never repurpose the seed-42
development partition or enable flags merely to make preflight pass.
