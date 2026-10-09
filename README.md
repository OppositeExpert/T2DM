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
- [Artifact archiving](docs/ARTIFACT_ARCHIVING.md): external immutable-archive
  manifest generation and restored-artifact verification.
- [Publication readiness](PUBLICATION_READINESS.md): pointer to the one canonical
  current final-experimental evidence package and remaining human release work.
- [Canonical final results](results/final_publication/FINAL_RESULTS_SUMMARY.md):
  endpoint-separated finalized internal-validation findings, tables, figure,
  leakage audit, provenance, and checksums.
- [Code and data use status](docs/LICENSE_AND_DATA_USE.md): current absence of a
  repository code license and dataset-specific terms that remain separate.
- [Software license status](LICENSE_STATUS.md): explicit no-license governance
  state; this repository is not yet approved for open-source reuse.
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

The final experimental pathway is complete under the frozen
`t2dm-final-internal-validation-v1` protocol. The authoritative studies use 75
Optuna trials per applicable model/fold and 2,000 bootstrap replicates with no
sample caps. BRFSS is transparently internal validation because no defensible
untouched final holdout remained. Hospital130 completed full-cohort,
patient-grouped internal validation and remains a separate 30-day-readmission
endpoint. Neither is called an independent final test.

`results/final_publication/FINAL_RESULTS.json` is the machine-readable source of
truth. The package preserves the negative result that dynamic model-family
switching did not establish multiplicity-corrected superiority, and it includes
the passing leakage audit, source tables, figure, execution provenance, and
checksums. A documented post-execution repair changed only packaging code; the
study-source and packaging-source hashes remain separate.

## Quick verification

From this directory:

```bash
source .venv-pipeline/bin/activate
python scripts/verify_environment.py
python scripts/acquire_data.py --dataset all
python -m pytest -q
python -m diabetes_pipeline.cli --help
```

The authoritative final study IDs are declared in
`config/authoritative_studies.yaml`. Large study artifacts and the canonical
package are Git-ignored and therefore require immutable external archival for
release. Historical smoke and development studies remain preserved under their
original evidence tiers and must not replace the finalized internal-validation
package.

An optional CPU container is provided for cross-platform setup and lightweight
verification. It pins Python and package versions, but it does not promise
byte-identical trained models across operating systems or CPU architectures.
