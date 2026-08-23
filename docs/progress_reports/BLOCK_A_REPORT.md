# Block A Report: Publication Pipeline Foundation

## Status

Block A is implemented and verified for seed 42.

The legacy source files under `src/` and all existing files under `results/` remain unchanged. New code is isolated under `src/diabetes_pipeline/`; new artifacts are under `outputs/publication_pipeline/`.

## Environment

- Isolated environment: `.venv-pipeline`
- Package install mode: editable from `pyproject.toml`
- Random seed: 42
- CatBoost: 1.2.10
- LightGBM: 4.7.0
- XGBoost: 3.4.1
- scikit-learn: 1.9.0
- Optuna: 4.9.0
- SHAP: 0.52.0

Direct dependencies are pinned in `pyproject.toml`.

## Dataset audits

| Dataset | Raw rows | Retained rows | Features | Positive prevalence | Rows with missing predictors | Evaluation identity |
|---|---:|---:|---:|---:|---:|---|
| BRFSS | 441,456 | 429,360 | 21 | 0.1334 | 182,289 | Stable source row |
| PIDD | 768 | 768 | 8 | 0.3490 | 376 | Stable source row |
| Sylhet | 520 | 520 | 16 | 0.6154 | 0 | 251 identical-profile groups |
| Hospital130 | 101,766 | 99,343 | 46 | 0.1139 | 99,343 | 69,990 patient groups |

BRFSS retains diagnosed-diabetes target-valid records with missing predictors rather than performing complete-case deletion before splitting. PIDD physiological zero sentinels are converted to missing markers but not imputed globally. Hospital130 excludes 2,423 death/hospice discharges, retains raw categories and patient identity until the grouped split is assigned, and treats identifier-coded admission/discharge fields as categorical.

The approved primary BRFSS endpoint uses raw code 1 (reported diagnosed diabetes) as positive and raw code 3 as negative. Pregnancy-only diabetes, prediabetes/borderline diabetes, unknown, refused, and missing responses are excluded. The legacy combined diabetes/prediabetes complete-case definition is reserved for a sensitivity analysis.

## Missingness observations

- BRFSS: the largest missing counts are Income 77,130; HighChol 61,201; Veggies 49,754; Fruits 42,573; PhysActivity 37,073.
- PIDD: Insulin 374; SkinThickness 227; BloodPressure 35; BMI 11; Glucose 5 zero-sentinel missing values.
- Sylhet: no missing predictors, but 269 duplicate feature-plus-target rows.
- Hospital130: max_glu_serum 94,191; A1Cresult 82,509; medical_specialty 48,616; payer_code 39,398; race 2,234 missing values after the at-risk-cohort exclusion.

## Split strategies

| Dataset | Strategy | Manifest rows | Key protection |
|---|---|---:|---|
| BRFSS | Stratified locked holdout plus five development folds | 429,360 | Balanced prevalence; test rows have no development fold |
| PIDD | Five repeats of five-fold nested stratified CV | 19,200 | Every row is validation exactly once per repeat |
| Sylhet | Five repeats of five-fold nested stratified group CV | 13,000 | Identical feature profiles never cross an outer fold |
| Hospital130 | Patient-grouped holdout plus five grouped development folds | 99,343 | No patient overlap between development, test, or development folds |

## Immutable fingerprints

| Dataset | Raw SHA-256 | Split-manifest SHA-256 |
|---|---|---|
| BRFSS | `a7d3380aca5aeae94186770983c3089fb6c4b2074aa112418112c11891d16420` | `047d0a8ad36f229ff1d74c8a2f5531f3123aee9cc480f708287ad2fa4265be1e` |
| PIDD | `6bfe5d0f379d17a0e0819b996407e3c09bf80febd4287f2ed212190dfff154af` | `774f1aa295d71e607b555247543a8761662be7ab31ca03db43c355b2ed18d87d` |
| Sylhet | `7889d9d0beb7dd1ccc58da99f72763f16afb259b5dbbaa086f8195366ff66137` | `1c5e2f18959d00d947ebf0248399566cc9535a7307e6692992c8408f8196f496` |
| Hospital130 | `0689e7ec031237dc63031b938805c48377748761a3b26acab621567afa24df97` | `6339ee87b228d61f351e56160591746448ed4052785ab8c035c7c42853371ca0` |

## Leakage barriers implemented

- Raw identity and grouping are separated from model features.
- PIDD imputation is deferred to a fold-fitted `SimpleImputer`.
- Hospital130 categorical encoding and numeric imputation are fold-fitted.
- Unknown held-out categories are ignored safely by the fitted encoder.
- Sylhet duplicate profiles are treated as evaluation groups.
- Hospital130 encounters are grouped by patient before identifiers are removed from features.
- Hospital130 expired/hospice encounters are outside the at-risk population and are excluded before splitting.
- Hospital130 admission type, discharge disposition, and admission source codes are one-hot encoded as categories.
- Split manifests are deterministic and validated before writing.

## Verification

Twenty-nine automated tests plus five model-adapter subtests now pass in the isolated environment. They cover the original Block A checks plus the complete modelling, reporting, holdout, clustered-bootstrap, and SHAP layers. Foundation-specific checks include:

- Dataset and experiment configuration loading.
- Deferred PIDD imputation.
- Sylhet profile grouping.
- Repeated split reproducibility.
- Split group-isolation checks.
- Training-only numeric imputer fitting.
- Unknown-category handling.

The complete Block A command was rerun using `.venv-pipeline` and reproduced the same split hashes.

## Approved cohort decision

BRFSS now uses 429,360 diagnosed-diabetes target-valid records and fold-specific imputation, rather than the legacy combined diabetes/prediabetes complete-case cohort of 251,702 records. The primary paper cohort and sensitivity cohort will be reported separately.
