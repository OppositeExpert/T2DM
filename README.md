# Diabetes Publication Pipeline

This repository contains the publication-focused pipeline for calibrated,
explainable diabetes-risk and readmission experiments. It compares Random
Forest, XGBoost, LightGBM, and CatBoost, evaluates feature-availability routing,
produces SHAP explanations, and creates detailed research-facing patient
reports.

## Start here

- [Runbook](docs/RUNBOOK.md): commands for audits, training, evaluation,
  routing, explanations, and patient reports.
- [Project structure](docs/PROJECT_STRUCTURE.md): what each folder contains.
- [Progress reports](docs/progress_reports): completed experimental blocks and
  their interpretation.
- [Master feature dictionary](outputs/publication_pipeline/feature_ontology/master_feature_dictionary.md):
  endpoint and feature relationships across the four datasets.

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

The repository includes a publication-readiness gate. Current pilot/smoke
artifacts intentionally fail it and must not be described as final paper
evidence. The gate also prevents the unvalidated cross-dataset heuristic from
entering the primary efficacy claim; mixed requests with multiple eligible
environments abstain unless an appropriate environment is explicitly selected.

## Quick verification

From this directory:

```bash
source .venv-pipeline/bin/activate
python -m pytest -q
python -m diabetes_pipeline.cli --help
```

The retained studies under `outputs/publication_pipeline/studies` are the
canonical completed runs. Smoke results verify execution only and are not final
paper evidence.
