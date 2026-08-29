# Diabetes Publication Pipeline

This repository contains the publication-focused pipeline for calibrated,
explainable diabetes-risk and readmission experiments. It compares Random
Forest, XGBoost, LightGBM, CatBoost, and an interpretable Logistic Regression
baseline; evaluates feature-availability routing,
produces SHAP explanations, and creates detailed research-facing patient
reports.

## Start here

- [Runbook](docs/RUNBOOK.md): commands for audits, training, evaluation,
  routing, explanations, and patient reports.
- [Clean-clone reproducibility](docs/REPRODUCIBILITY.md): environment, data,
  development-study, package, and audit regeneration.
- [Data acquisition](docs/DATA_ACQUISITION.md): authoritative sources, exact
  filenames, hashes, licenses, loader assumptions, and verified acquisition.
- [Tracked evidence registry](evidence/README.md): mapping from authoritative
  development studies to ignored local artifacts and hashes.
- [Code and data use status](docs/LICENSE_AND_DATA_USE.md): current absence of a
  repository code license and dataset-specific terms that remain separate.
- [Project structure](docs/PROJECT_STRUCTURE.md): what each folder contains.
- [Progress reports](docs/progress_reports): completed experimental blocks and
  their interpretation.
- [Feature ontology source](config/feature_ontology.yaml): endpoint and feature
  relationships across the four datasets; the human-readable dictionary is
  regenerated under ignored `outputs/` by `python -m diabetes_pipeline.cli feature-map`.

## Active pipeline

The only source package is `src/diabetes_pipeline`. The supported datasets are:

- PIDD: clinical diabetes screening.
- Sylhet: symptom-based early diabetes screening.
- BRFSS: population survey diabetes-status prediction.
- Hospital130: 30-day readmission prediction for encounters involving diabetes;
  this is a separate endpoint and is never pooled with screening probabilities.

Feature-availability routing contracts now cover all four datasets. A mixed
patient input may contain any number of dataset-namespaced PIDD, Sylhet, and
BRFSS attributes. Every eligible router is evaluated, but one cohort-specific
screening expert is selected for the final percentage; probabilities are not
averaged across incompatible cohorts. Hospital130 remains isolated because it
predicts readmission, not diabetes status.

The repository includes a publication-readiness gate. The authoritative PIDD,
Sylhet, and BRFSS artifacts are full development evidence and intentionally fail
the final-profile, profile-lock, and human-review gates; they must not be
described as final paper evidence. The gate also prevents the unvalidated cross-dataset heuristic from
entering the primary efficacy claim; mixed requests with multiple eligible
environments abstain unless an appropriate environment is explicitly selected.

The technical final pathway is documented in `FINAL_RUN_CHECKLIST.md`. It
separates one-time concealed-manifest creation from execution authorization and
binds any future run to exact data, manifest, source/configuration, environment,
seed, and signed-record hashes. All authorization and protocol flags remain
false until legitimate human review occurs.

## Quick verification

From this directory:

```bash
source .venv-pipeline/bin/activate
python scripts/verify_environment.py
python scripts/acquire_data.py --dataset all
python -m pytest -q
python -m diabetes_pipeline.cli --help
```

The authoritative study IDs are declared in `config/authoritative_studies.yaml`.
The corresponding large artifacts under `outputs/publication_pipeline/studies`
are ignored and must be regenerated after a clean clone. Smoke results verify
execution only; full-development results support development decisions only;
neither is final locked paper evidence.
