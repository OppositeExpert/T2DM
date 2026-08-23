# Block E Checkpoint: Grouped Sylhet Development Pilot

## Status

The five-model evaluation and held-out SHAP pipeline now runs across all five
Sylhet outer folds while keeping identical questionnaire profiles in the same
partition.

Experiment ID: `sylhet_development_pilot_ed7c05460503`

This remains a development pilot: five tuning trials, one outer repeat, and 200
bootstrap resamples. It is not the locked final paper run.

## Why grouped validation is essential

- Raw rows: 520.
- Positive outcomes: 320 (61.54%).
- Unique feature-profile groups: 251.
- Duplicate feature rows: 269.
- Largest identical-profile group: 16 records.

All duplicate profiles share a group ID. Every outer and inner split was checked
for zero group overlap. Ordinary row-wise random cross-validation would allow
identical predictor vectors to occur in both training and validation and would
therefore produce optimistic evidence.

## Pooled held-out probability performance

Intervals are 95% stratified percentile bootstrap intervals from 200 resamples.

| Model | AUROC (95% CI) | Average precision (95% CI) | Brier (95% CI) | Log loss (95% CI) |
|---|---:|---:|---:|---:|
| CatBoost | **0.9722 [0.9577, 0.9820]** | **0.9841 [0.9764, 0.9899]** | **0.0642 [0.0489, 0.0803]** | **0.2093 [0.1662, 0.2567]** |
| LightGBM | 0.9649 [0.9515, 0.9784] | 0.9801 [0.9730, 0.9872] | 0.0701 [0.0570, 0.0836] | 0.2373 [0.1954, 0.2811] |
| Random Forest | 0.9586 [0.9436, 0.9728] | 0.9749 [0.9668, 0.9828] | 0.0759 [0.0623, 0.0896] | 0.2518 [0.2074, 0.2972] |
| XGBoost | 0.9535 [0.9362, 0.9712] | 0.9709 [0.9606, 0.9817] | 0.0800 [0.0630, 0.0958] | 0.2665 [0.2162, 0.3093] |
| Logistic Regression | 0.9478 [0.9287, 0.9644] | 0.9704 [0.9591, 0.9785] | 0.0871 [0.0718, 0.1033] | 0.3026 [0.2434, 0.3692] |

At threshold 0.5, pooled sensitivities range from 0.8938 to 0.9313,
specificities from 0.8050 to 0.9300, and F1 values from 0.9008 to 0.9380.
Despite CatBoost's numerically best values, none of the paired five-fold model
comparisons for AUROC, average precision, Brier score, or log loss is
significant after Holm correction. The pilot is too small to support a strong
champion claim.

## Calibration safeguard discovered during development

An earlier unconstrained pilot allowed isotonic calibration on roughly 416
outer-training rows. It selected isotonic in several folds and caused extreme
probabilities: pooled XGBoost log loss was 0.5070 and LightGBM log loss was
0.3426. The finalized development contract now marks isotonic ineligible below
1,000 calibration samples. With identity/sigmoid selection, the corresponding
log losses are 0.2665 and 0.2373.

This rule is consistent with the original probability-calibration study and
current scikit-learn guidance that isotonic regression is more prone to
small-sample overfit:

- Niculescu-Mizil and Caruana, 2005:
  <https://doi.org/10.1145/1102351.1102430>
- Scikit-learn probability calibration guidance:
  <https://scikit-learn.org/stable/modules/calibration.html>

The exploratory failed run remains on disk for auditability; only the revised
predeclared protocol should advance to final experiments.

Selected calibrators across the revised five folds were:

| Model | Identity | Sigmoid | Isotonic eligible |
|---|---:|---:|---:|
| CatBoost | 3 | 2 | 0 |
| LightGBM | 5 | 0 | 0 |
| Logistic Regression | 3 | 2 | 0 |
| Random Forest | 0 | 5 | 0 |
| XGBoost | 5 | 0 | 0 |

## Held-out SHAP result

The dominant features are highly consistent at the top:

- Polyuria ranks first in CatBoost, LightGBM, Random Forest, and XGBoost.
- Polydipsia ranks first in Logistic Regression and second in the other four.
- Gender ranks third in all five models.
- Itching, irritability, partial paresis, sudden weight loss, alopecia, and age
  occupy the remaining top-five positions depending on the model.

Random Forest has unusually strong stability: mean full-rank Spearman 0.9303
and top-five Jaccard 1.0. Other model mean rank correlations range from 0.6285
to 0.7926, showing that lower-ranked symptom importance is not completely
stable in this small grouped cohort.

The very high performance must be interpreted cautiously. Sylhet is a small,
specific symptom-questionnaire cohort, and several predictors are close to
manifest disease symptoms. It is not evidence that these estimates transport
to general-population screening.

## Verification and provenance

- 2,600 held-out probability rows: 520 records for each model.
- 25 reloadable bundles; maximum reload difference is within CSV precision.
- 41,600 held-out SHAP rows: 520 records × 16 features × 5 models.
- Maximum SHAP additivity error: `7.02589750289917e-06`.
- Raw data SHA-256:
  `7889d9d0beb7dd1ccc58da99f72763f16afb259b5dbbaa086f8195366ff66137`
- Split manifest SHA-256:
  `1c5e2f18959d00d947ebf0248399566cc9535a7307e6692992c8408f8196f496`
- Source-tree SHA-256:
  `a94ba81910f13f0ce26109d7f2a27ec883ac239880b266390c834f7d700b7913`
- Predictions SHA-256:
  `97617d8452910368d12e174f5342e53e2e541652fd8a807a18d4f677bc64dbfd`
- Summary SHA-256:
  `a34259a9bd391b0ac0d983115981329bdad841592774c74d92e3c32068d6b591`
- SHAP values SHA-256:
  `0cec07ad062018a14ec5387b65b9b4e2e3f21262c8b56fd5cd21ee184f73d29f`

## Next block

1. Build the feature-availability and missingness-stress matrix across PIDD and
   Sylhet.
2. Compare a fixed global model against an availability-aware router using only
   development predictions.
3. Define abstention rules for unsupported or severely incomplete inputs.
4. Scale the finalized protocol to BRFSS, then adapt the separate Hospital130
   readmission task.
