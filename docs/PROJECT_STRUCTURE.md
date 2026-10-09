# Project structure

Paths remain stable; cleanup does not rename research APIs or configuration keys.

| Path | Purpose and status |
|---|---|
| `src/diabetes_pipeline/data/`, `contracts.py` | Dataset loading, validation, immutable input fingerprints |
| `splitting/`, `preprocessing/` | Group-aware split contracts and training-fold transformations |
| `models/`, `training/` | Five-family registry, search spaces and seeded Optuna tuning |
| `calibration/` | Identity/sigmoid/isotonic selection and development-selected thresholds |
| `evaluation/` | Metrics, bootstrap inference, Holm comparisons, DCA, subgroups, missingness, ablations and selective prediction |
| `routing/` | Prespecified dataset-native panels, fitted routing bundles, actual fallback evaluation and abstention |
| `explainability/`, `reporting/` | Held-out SHAP, reconstruction/stability and research-facing reports |
| `features/` | Semantic feature ontology and endpoint constraints |
| `publication/` | Final governance, exporter, source selection, protocol corrections and consolidated figure |
| `runner.py`, `holdout_runner.py`, `cli.py` | Repeated nested-CV and holdout-shaped internal evaluation; CLI |
| `config/` | Dataset, source, feature, availability, output and frozen protocol contracts |
| `scripts/` | Acquisition, verification, final orchestration, export and historical report builders |
| `tests/`, `.github/workflows/ci.yml` | Unit/research-control tests and lightweight CI |
| `results/final_publication/` | Tracked aggregate current publication evidence and existing superseded archive |
| `evidence/` | Tracked artifact hashes; final and historical inventories are distinct |
| `docs/` | Current contributor guides plus dated research/progress/audit records |
| `conference_package/` | Historical development drafts and their original QA/render evidence; retained in place |
| `examples/` | Explicit synthetic inputs |
| `data/raw/` | Ignored immutable cohort records; acquire separately |
| `outputs/publication_pipeline/` | Ignored studies, model bundles, predictions, splits, trials, logs, receipts and checkpoints |
| `.venv-pipeline/` | Ignored local environment; recreate for each checkout |

The source flow is input contract → immutable splitting → fold-fitted
preprocessing → five model families → calibration/thresholds → panel/router
policies → metrics/uncertainty/explanations. Unsupported input abstains.
Hospital130 remains an isolated readmission endpoint throughout.

Authoritative study IDs and evidence tiers are declared in
`config/authoritative_studies.yaml`. Current tables and source selection are
explained in [RESULTS_GUIDE.md](RESULTS_GUIDE.md). Earlier reports may describe
pre-final code or superseded findings; their dates are part of their meaning.
