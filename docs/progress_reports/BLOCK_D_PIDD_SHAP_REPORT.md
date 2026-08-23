# Block D Checkpoint: Held-Out PIDD SHAP Explanations

## Status

Fold-specific SHAP explanations are complete for every held-out PIDD patient in
the five-fold development pilot. Explanations are generated from each fold's
saved preprocessor and fitted model; no in-fold training patient is included in
the reported SHAP evidence.

Parent experiment: `pidd_development_pilot_27b9bc88b493`

## Explanation contract

- Logistic Regression is explained on the raw log-odds scale.
- Random Forest is explained on the raw probability scale.
- XGBoost, LightGBM, and CatBoost are explained on their raw-margin scales.
- Calibration is applied after the base-model prediction, so SHAP values explain
  the base model while the accompanying patient row retains both raw and
  calibrated probabilities.
- Because explanation scales differ, SHAP magnitudes must not be compared
  directly between model families. Within-model rankings, directions, and
  fold-stability are the valid comparisons.

## Global result

Glucose is the top-ranked feature in all five models and BMI is second in all
five. The remaining top-five patterns are:

| Model | Features ranked 1–5 |
|---|---|
| CatBoost | Glucose, BMI, Age, DiabetesPedigreeFunction, Pregnancies |
| LightGBM | Glucose, BMI, Age, DiabetesPedigreeFunction, Pregnancies |
| Logistic Regression | Glucose, BMI, Pregnancies, DiabetesPedigreeFunction, missing Insulin indicator |
| Random Forest | Glucose, BMI, Age, DiabetesPedigreeFunction, Pregnancies |
| XGBoost | Glucose, BMI, Age, DiabetesPedigreeFunction, Insulin |

Higher Glucose and BMI values have strong positive SHAP associations in every
model. Age is also positively associated in the four tree models. The missing
Insulin indicator entering Logistic Regression's top five is evidence that
feature availability itself can affect prediction and should be included in the
planned missingness/routing experiments.

## Fold-to-fold stability

Each model has ten pairwise comparisons across the five outer folds.

| Model | Mean rank Spearman | Minimum rank Spearman | Mean top-5 Jaccard | Minimum top-5 Jaccard |
|---|---:|---:|---:|---:|
| XGBoost | 0.9787 | 0.9405 | 0.8000 | 0.6667 |
| Random Forest | 0.9706 | 0.9216 | 0.7333 | 0.6667 |
| LightGBM | 0.9689 | 0.9500 | 0.7667 | 0.6667 |
| CatBoost | 0.9588 | 0.9286 | 0.7667 | 0.6667 |
| Logistic Regression | 0.8130 | 0.5967 | 0.7667 | 0.6667 |

Tree-model importance ranks are highly stable. Logistic Regression has a stable
top-five set but less stable complete ranking, largely among lower-importance
features and missingness indicators.

## Contextual age evidence

Quantile-binned held-out dependence summaries place the first median-positive
Age contribution at approximately:

- Age 28 for CatBoost and LightGBM.
- Age 31 for Random Forest and XGBoost.
- Age 36 for Logistic Regression.

These values mean “positive relative to that model's baseline in this PIDD
cohort.” They are not diagnostic or clinical age thresholds. A patient-facing
system may use them only as carefully worded model context, such as “age begins
to contribute above the model baseline in this cohort,” and must not state that
diabetes risk clinically begins at that age.

## Verification

- 49,920 SHAP rows: 768 held-out patients × 13 transformed features × 5 models.
- 19,200 patient-level top-contributor rows: five factors per patient/model.
- 390 dependence-bin rows.
- 22 PNG and 22 SVG explanation figures.
- Every model/fold passes the SHAP additivity check.
- Maximum absolute reconstruction error: `3.0514784157276154e-06`.
- Two complete explanation runs produced byte-identical SHAP values, global
  importance, stability, local contributors, and transition files.
- Automated suite: 19 tests plus 5 model-adapter subtests pass.

## Deterministic artifact hashes

- SHAP long table:
  `a1b6843fe0c191927bae98362052ea15d800e8ef7d6f83432d4494ad4c889075`
- Global importance:
  `c52f460888936964db462d62b0133dbfa0d83308923d22dfc5442ec3ae3cebba`
- Stability summary:
  `97f18f2cffb82828204aee7eed289dcf758ef852fc5f662d22f262f75ba873d7`
- Local contributors:
  `ef570d223e9612971ef973f4f37a6b93c7075ea4f95bb0980e8058d68b8c583a`
- Exploratory contribution transitions:
  `a28bf910f5b1c2edb29f257a69a129e266f7faae422c71f5367cc1a1bc20d649`

## Next block

1. Run the validated pipeline on grouped Sylhet data to test duplicate-profile
   isolation and group-aware calibration selection.
2. Build the feature-availability stress matrix and missingness-aware model
   routing evidence.
3. Add a patient-result formatter that combines calibrated probability, chosen
   operating policy, SHAP factors, and cautiously phrased cohort context.
4. Scale to BRFSS and adapt the separate grouped Hospital130 endpoint.
