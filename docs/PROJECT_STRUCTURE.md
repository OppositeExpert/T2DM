# Project Structure

```text
T2DM/
├── README.md                   Project overview and starting point
├── pyproject.toml              Package metadata and pinned dependencies
├── requirements.lock          Resolved Python environment
├── .python-version            Reference CPython version
├── .venv-pipeline/            Local environment; never copy between checkouts
│
├── config/                     Reproducible experiment definitions
│   ├── datasets.yaml           Dataset schemas, endpoints, and raw file paths
│   ├── availability_scenarios.yaml
│   ├── feature_ontology.yaml   Cross-dataset feature relationships
│   ├── output_schemas.yaml
│   ├── data_sources.yaml      Raw-source, license, and byte-hash manifest
│   ├── authoritative_studies.yaml
│   └── experiments/            Smoke, pilot, development, and final profiles
│
├── data/
│   └── raw/                    Four immutable source datasets
│
├── src/
│   └── diabetes_pipeline/      The complete active Python package
│       ├── data/               Loading, validation, and manifests
│       ├── splitting/          Leakage-safe folds and grouped splits
│       ├── preprocessing/      Fold-fitted transformations
│       ├── models/             RF, XGBoost, LightGBM, CatBoost, and baseline
│       ├── training/           Hyperparameter optimization
│       ├── calibration/        Probability calibration and thresholds
│       ├── evaluation/         Metrics, bootstrap CIs, DCA, and comparisons
│       ├── routing/            Feature-panel and model selection
│       ├── explainability/     SHAP analysis and stability checks
│       ├── reporting/          Detailed patient research reports
│       ├── features/           Master feature ontology
│       ├── runner.py           Nested-CV experiment runner
│       ├── holdout_runner.py   Locked holdout experiment runner
│       └── cli.py              Command-line entry point
│
├── tests/                      Automated leakage, metric, model, and reload tests
├── examples/                   Synthetic, non-identifiable example inputs
├── docs/
│   ├── RUNBOOK.md              How to run each pipeline stage
│   ├── REPRODUCIBILITY.md      Clean-clone-to-development-evidence path
│   ├── DATA_ACQUISITION.md     Verified raw-data acquisition
│   ├── PROJECT_STRUCTURE.md    This map
│   └── progress_reports/       Human-readable completed-block reports
│
├── evidence/                  Tracked registry for ignored study artifacts
└── outputs/
    └── publication_pipeline/   Reproducible generated research artifacts
        ├── manifests/          Dataset audit records and hashes
        ├── splits/             Immutable split assignments
        ├── feature_ontology/   Generated cross-dataset dictionary
        └── studies/            Generated studies; ignored, not clone contents
```

## Data flow

```text
Raw dataset + configuration
          │
          ▼
Validation and immutable splitting
          │
          ▼
Fold-fitted preprocessing
          │
          ▼
RF / XGBoost / LightGBM / CatBoost
          │
          ▼
Calibration + threshold selection + model/panel routing
          │
          ├──────────────► Metrics, confidence intervals, plots, comparisons
          ├──────────────► SHAP explanations and stability checks
          └──────────────► Detailed patient research result or safe abstention
```

## Authoritative studies

- `pidd_development_072cd2104089`
- `sylhet_development_b52477910fe6`
- `brfss_development_holdout_56407ef53bba`

The exact mapping is machine-readable in `config/authoritative_studies.yaml` and
`evidence/study_registry.json`. Historical BRFSS and Hospital130 smoke studies
remain engineering provenance, not publication estimates. No current study is
a final locked result; final execution remains prohibited until the protocol is
frozen and independently authorized.
