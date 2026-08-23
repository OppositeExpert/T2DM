# Project Structure

```text
XGBoost/
├── README.md                   Project overview and starting point
├── pyproject.toml              Package metadata and pinned dependencies
├── .venv-pipeline/             Environment used by the new pipeline
│
├── config/                     Reproducible experiment definitions
│   ├── datasets.yaml           Dataset schemas, endpoints, and raw file paths
│   ├── availability_scenarios.yaml
│   ├── feature_ontology.yaml   Cross-dataset feature relationships
│   ├── output_schemas.yaml
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
│   ├── PROJECT_STRUCTURE.md    This map
│   └── progress_reports/       Human-readable completed-block reports
│
└── outputs/
    └── publication_pipeline/   Reproducible generated research artifacts
        ├── manifests/          Dataset audit records and hashes
        ├── splits/             Immutable split assignments
        ├── feature_ontology/   Generated cross-dataset dictionary
        └── studies/            Four retained canonical experiment runs
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

## Retained canonical studies

- `pidd_development_pilot_27b9bc88b493`
- `sylhet_development_pilot_ed7c05460503`
- `brfss_smoke_holdout_1f1344dceb63`
- `hospital130_smoke_holdout_6640beff7a08`

The BRFSS and Hospital130 studies are smoke runs for engineering verification,
not final publication estimates. Final experiments remain locked until the
protocol is frozen.
