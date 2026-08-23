# Block C Checkpoint: PIDD Five-Fold Development Pilot

## Status

The complete five-model PIDD evaluation path now works across all five outer
folds. This is a development pilot, not the locked paper experiment: it uses
five Optuna trials per model/fold, one outer repeat, and 200 bootstrap
resamples. The final profile retains a larger tuning and uncertainty budget.

Experiment ID: `pidd_development_pilot_27b9bc88b493`

## Leakage-control design

For each outer fold, the pipeline independently performs:

1. Fold-fitted zero-sentinel handling, median imputation, missing indicators,
   and model-appropriate transformation.
2. Five-fold inner optimization of average precision.
3. Inner out-of-fold base-model probability generation.
4. Cross-fitted comparison of identity, sigmoid, and isotonic calibration by
   Brier score, with log loss as the tie-breaker.
5. Development-only selection of fixed 0.5, Youden, and 80%-sensitivity
   operating thresholds.
6. One evaluation on the untouched outer fold.

Outer labels never participate in preprocessing, tuning, calibration selection,
or threshold selection.

## Pooled held-out probability performance

The table below pools each model's 768 out-of-fold predictions. Intervals are
95% stratified percentile bootstrap intervals from 200 resamples.

| Model | AUROC (95% CI) | Average precision (95% CI) | Brier (95% CI) | Log loss (95% CI) |
|---|---:|---:|---:|---:|
| XGBoost | 0.8376 [0.8089, 0.8667] | **0.7158 [0.6638, 0.7698]** | 0.1547 [0.1413, 0.1680] | 0.4692 [0.4335, 0.5036] |
| CatBoost | **0.8394 [0.8113, 0.8626]** | 0.7097 [0.6586, 0.7622] | **0.1540 [0.1425, 0.1671]** | **0.4688 [0.4402, 0.5021]** |
| Logistic Regression | 0.8352 [0.8084, 0.8626] | 0.7093 [0.6626, 0.7667] | 0.1563 [0.1427, 0.1682] | 0.4775 [0.4428, 0.5074] |
| LightGBM | 0.8353 [0.8079, 0.8625] | 0.7074 [0.6510, 0.7605] | 0.1553 [0.1423, 0.1682] | 0.4718 [0.4396, 0.5058] |
| Random Forest | 0.8360 [0.8099, 0.8660] | 0.6989 [0.6583, 0.7495] | 0.1557 [0.1422, 0.1672] | 0.4735 [0.4396, 0.5076] |

At the fixed 0.5 operating point, pooled sensitivity ranged from 0.5746 to
0.6194 and specificity from 0.8500 to 0.8760. The best F1 was 0.6523 for Random
Forest, but threshold-dependent rankings are secondary to probability quality.

## Sensitivity-constrained operating point

Thresholds were learned separately inside each outer training partition to
meet at least 80% development sensitivity. The reported threshold is the mean
across five outer folds; ranges show threshold instability that the final paper
must report.

| Model | Mean threshold [range] | Outer sensitivity (95% CI) | Outer specificity (95% CI) | PPV | NPV | F1 |
|---|---:|---:|---:|---:|---:|---:|
| XGBoost | 0.3172 [0.2895, 0.3688] | 0.8134 [0.7687, 0.8545] | **0.7100 [0.6700, 0.7461]** | 0.6006 | 0.8765 | **0.6910** |
| CatBoost | 0.3183 [0.3043, 0.3441] | **0.8172 [0.7723, 0.8583]** | 0.7000 [0.6599, 0.7480] | 0.5935 | **0.8772** | 0.6876 |
| LightGBM | 0.3146 [0.2954, 0.3467] | 0.8060 [0.7537, 0.8508] | 0.7100 [0.6679, 0.7460] | 0.5983 | 0.8722 | 0.6868 |
| Random Forest | 0.3363 [0.3122, 0.3810] | 0.8060 [0.7648, 0.8545] | 0.7080 [0.6660, 0.7500] | 0.5967 | 0.8719 | 0.6857 |
| Logistic Regression | 0.2947 [0.2726, 0.3392] | 0.8022 [0.7648, 0.8470] | 0.6860 [0.6519, 0.7261] | 0.5780 | 0.8662 | 0.6719 |

Every learned sensitivity-constrained threshold met the 0.80 target on its
inner development predictions. Outer sensitivity is correctly allowed to vary.

## Calibration selection

No calibration method was forced. Cross-fitted Brier-score selection chose:

| Model | Identity folds | Sigmoid folds | Isotonic folds |
|---|---:|---:|---:|
| Logistic Regression | 2 | 3 | 0 |
| Random Forest | 1 | 4 | 0 |
| XGBoost | 3 | 2 | 0 |
| LightGBM | 2 | 3 | 0 |
| CatBoost | 3 | 2 | 0 |

The changing identity/sigmoid choice across folds is useful evidence: always
applying one calibrator would not be justified on this small dataset. Isotonic
is recorded as ineligible because each calibration set has fewer than 1,000
samples, a predeclared protection against small-sample nonparametric overfit.

## Statistical interpretation

- The five models are very close. Their confidence intervals overlap heavily.
- Across AUROC, average precision, Brier score, and log loss, no paired
  five-fold model comparison is significant after Holm correction; the minimum
  adjusted p-value is 1.0 in this low-powered pilot.
- Therefore this run does not support claiming one universally superior model.
- Logistic Regression remains competitive with the four tree ensembles. A
  publishable contribution must come from the calibrated, leakage-free,
  missingness-aware, explainable, and clinically evaluated system—not from a
  weak claim that a particular boosted tree wins PIDD.
- Decision-curve results suggest positive net benefit for all five models over
  a broad threshold range, but this remains exploratory until the locked final
  experiment and external/population validation.

## Artifacts and verification

- 3,840 held-out probability rows: 768 patients for each of five models.
- 11,520 threshold-specific prediction rows.
- 100 outer-fold metric rows.
- 460 bootstrap confidence-interval rows.
- 75 calibration candidate rows with exactly 25 selected calibrators.
- 75 learned threshold rows.
- 40 paired model-comparison rows.
- 25 complete reloadable model bundles.
- Five PNG and five SVG figures.
- All 25 bundles reproduce their saved raw and calibrated probabilities within
  CSV floating-point precision; maximum observed error was
  `1.1102230246251565e-16`.
- Automated suite: 15 tests plus 5 model-adapter subtests pass.
- The current smoke profile reproduced byte-identical predictions, summary,
  calibration selection, thresholds, confidence intervals, and decision curves
  across two complete runs.

## Provenance

- Raw PIDD SHA-256:
  `6bfe5d0f379d17a0e0819b996407e3c09bf80febd4287f2ed212190dfff154af`
- Dataset configuration SHA-256:
  `c000944c58f8e2edf5c5ef337bfe7b7243a1f4f9e3e7916a4466594864dd4add`
- Split manifest SHA-256:
  `774f1aa295d71e607b555247543a8761662be7ab31ca03db43c355b2ed18d87d`
- Source-tree SHA-256:
  `a94ba81910f13f0ce26109d7f2a27ec883ac239880b266390c834f7d700b7913`
- Predictions SHA-256:
  `ade12cab7aa59dc04ae792823da4b4c01c4809880dc51380657ae5db75d3e864`
- Summary SHA-256:
  `9d4f33602618c6f90a8ecd37fb010fc39489e74fdd4bc83426c9bec8b03a106b`

## Next block

1. Implement fold-specific SHAP explanations and stability analysis.
2. Add explicit feature-availability/missingness stress experiments, which are
   central to the proposed routing novelty.
3. Run the same validated evaluation layer on Sylhet and BRFSS.
4. Adapt the grouped holdout runner for the separate Hospital130 readmission
   endpoint.
5. Only after those checks, lock the final tuning, resampling, and analysis
   profile and begin the paper's final results tables.
