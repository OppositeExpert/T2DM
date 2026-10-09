# Project structure and research workflow

| Path | Active purpose |
|---|---|
| `src/diabetes_pipeline/data/`, `contracts.py` | Loading, validation, cohort flow and immutable input fingerprints |
| `splitting/`, `preprocessing/` | Group-aware splits, outcome-blind controls and fold-fitted transforms |
| `models/`, `training/` | Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost and seeded Optuna tuning |
| `calibration/` | Calibration selection and development-selected thresholds |
| `evaluation/` | Metrics, paired bootstrap intervals, Holm correction, DCA, subgroups, missingness, ablations and selective prediction |
| `routing/` | Availability panels, fitted routing bundles, runtime fallback, policy coverage and abstention |
| `explainability/`, `reporting/` | Held-out SHAP, stability, research reports and readiness controls |
| `features/` | Dataset-native measurement semantics and endpoint ontology |
| `publication/` | Frozen governance, final export, protocol corrections, leakage audit and consolidated figure |
| `runner.py`, `holdout_runner.py`, `cli.py` | Repeated nested-CV and holdout-shaped internal evaluation; command interface |
| `config/` | Dataset/source, feature, availability, output-schema, study and protocol contracts |
| `scripts/` | Acquisition, verification, final orchestration, export/correction, registry and migration tools |
| `tests/`, `.github/workflows/` | Research-contract, control and portable validation |
| `examples/` | Explicit synthetic inputs |
| `results/final_publication/` | Current frozen aggregate metrics, tables, visualizations and provenance |
| `evidence/` | Final/development artifact inventories, registry, unique correction evidence and historical estimand reference |
| `docs/` | Installation, acquisition, command, result and manuscript-review guides |
| `docs/research/` | Scientifically relevant plans, decisions, literature, ablation findings and execution deviations |
| `docs/audits/2026-09-05/` | Retained integrity findings/evidence requiring explicit closure review |
| `data/raw/`, `outputs/` | Ignored local cohort records, fitted models, predictions, splits, trials, logs and checkpoints |

The end-to-end flow is dataset contracts → immutable/group-aware splits →
fold-fitted preprocessing → five-family tuning/training → calibration/thresholds
→ fixed panels and runtime routing/abstention → paired statistical analysis,
selective/subgroup/missingness/ablation analysis → explanations → locked final
provenance → publication tables and figures. Tests cover each source subsystem.

Hospital130 is separate patient-grouped 30-day readmission. Other cohorts retain
their own recorded diabetes-status endpoints and measurement environments;
probabilities are not pooled. See [RESULTS_GUIDE.md](RESULTS_GUIDE.md).

The active tree has no conference package, block progress-report directory,
first-cleanup audit inventory or complete superseded publication package.
Their originals remain locally preserved and recoverable from prior commits.
The [simplification report](../REPOSITORY_SIMPLIFICATION_REPORT.md) identifies
archives and the few historical scientific records deliberately retained.
