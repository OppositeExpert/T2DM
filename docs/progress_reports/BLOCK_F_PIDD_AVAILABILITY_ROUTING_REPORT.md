# Block F Checkpoint: PIDD Feature-Availability Routing

## Status

The four-model availability router is implemented and evaluated without outer-
fold leakage. The experiment tests the routing hypothesis rather than assuming
that switching algorithms is beneficial.

Parent experiment: `pidd_development_pilot_27b9bc88b493`

## Routing design

For each outer fold and feature panel:

1. Random Forest, XGBoost, LightGBM, and CatBoost are fitted on the complete
   outer-training features.
2. Inner validation inputs are masked to the candidate panel.
3. Scenario-specific calibration is selected from inner cross-fitted
   probabilities.
4. The model with the lowest development Brier score is selected; log loss and
   average precision break ties.
5. The selected model is evaluated once on masked outer-fold patients.

Two non-routing baselines are evaluated on the same patients:

- Full-panel champion: the model selected using the full feature panel, reused
  for every incomplete panel.
- Robust single model: one model selected for its mean development Brier score
  across all panels.

The router never uses an outer patient's label to choose a model.

## Feature panels

| Scenario | Available features | Count |
|---|---|---:|
| Full | All PIDD predictors | 8 |
| No insulin or skinfold | Pregnancies, Glucose, BloodPressure, BMI, pedigree, Age | 6 |
| Routine clinic | Pregnancies, Glucose, BloodPressure, BMI, Age | 5 |
| Core metabolic | Glucose, BMI, pedigree, Age | 4 |
| Non-laboratory | Pregnancies, BMI, pedigree, Age | 4 |
| Minimal glucose-age | Glucose, Age | 2 |

## Pooled outer performance of the availability router

Intervals are 95% stratified bootstrap intervals from 200 resamples.

| Scenario | AUROC (95% CI) | Average precision (95% CI) | Brier (95% CI) | Log loss (95% CI) |
|---|---:|---:|---:|---:|
| Full | 0.8394 [0.8088, 0.8675] | 0.7068 [0.6522, 0.7663] | 0.1540 [0.1406, 0.1678] | 0.4686 [0.4356, 0.5049] |
| No insulin or skinfold | 0.8389 [0.8135, 0.8649] | **0.7144 [0.6615, 0.7698]** | **0.1539 [0.1418, 0.1652]** | **0.4682 [0.4365, 0.4971]** |
| Routine clinic | 0.8346 [0.7984, 0.8639] | 0.6980 [0.6465, 0.7612] | 0.1563 [0.1423, 0.1711] | 0.4755 [0.4405, 0.5133] |
| Core metabolic | 0.8357 [0.8053, 0.8633] | 0.7209 [0.6706, 0.7640] | 0.1550 [0.1420, 0.1687] | 0.4705 [0.4380, 0.5063] |
| Minimal glucose-age | 0.8048 [0.7743, 0.8384] | 0.6847 [0.6301, 0.7410] | 0.1676 [0.1545, 0.1808] | 0.5054 [0.4709, 0.5362] |
| Non-laboratory | 0.7393 [0.7037, 0.7746] | 0.5750 [0.5294, 0.6305] | 0.1913 [0.1803, 0.2027] | 0.5626 [0.5376, 0.5920] |

The panel result is much stronger than the algorithm-switching result:

- Removing Insulin and SkinThickness causes almost no degradation.
- Four core features retain performance close to the full panel.
- Removing Glucose causes the largest drop: average precision falls to 0.5750
  in the non-laboratory scenario.
- Glucose plus Age alone retains some discrimination but has worse probability
  accuracy than richer panels.

These are development findings for this cohort, not clinical feature-
acquisition recommendations.

## Does dynamic model selection help?

Only marginally, and not reliably.

- Versus the full-panel champion, mean fold-average Brier reduction is 0.00274
  for the core panel, 0.00056 for glucose-age, 0.00053 for routine clinic, and
  0.00068 for the non-laboratory panel.
- Average-precision changes versus that baseline range from +0.00485 to
  -0.00805.
- Against the robust single-model baseline, the router often has slightly lower
  average precision and mixed Brier/log-loss changes.
- No router-versus-baseline comparison is significant after Holm correction.
- Model selections are unstable across five outer folds. For example, the core
  panel chooses every model at least once, while the non-laboratory panel chooses
  XGBoost in three folds and two other models in the remaining folds.

Therefore the present PIDD evidence does not support claiming that per-panel
algorithm switching improves outcomes. The honest publishable result is that
feature availability materially changes reliability, while the four tree
algorithms are too similar and the sample is too small for stable routing.

## Inference and abstention

Each outer fold saves a complete router bundle containing:

- Supported feature panels.
- Development-selected model per panel.
- Four fitted model bundles.
- Scenario-specific calibrators.
- Default probability threshold.

At inference, the router selects the largest supported panel contained in the
patient's observed features, masks unsupported extras to reproduce the tested
scenario, and returns calibrated probability plus the selected model. If no
supported panel is present, it returns `abstain` rather than manufacturing a
prediction. Both the prediction and abstention paths pass automated tests.

## Verification

- 120 development score rows: 5 folds × 6 panels × 4 models.
- 18,432 model/panel outer predictions.
- 30 development-only model selections.
- 32,256 individual, router, and baseline system predictions.
- 210 fold metric rows.
- 216 bootstrap interval rows for router and fixed baselines.
- Five reloadable outer-fold router bundles.
- 21 automated tests plus 5 model-adapter subtests pass.
- Two complete routing runs produced byte-identical scientific outputs.

## Deterministic artifact hashes

- Development scores:
  `933f54b85ce367464adf127dcaabe55089540d867f7870d9b1468e87b8656be8`
- Stress predictions:
  `89a912243196678a821e7af34ed43475ca4287f0a49bccd0fe689c159e2bdc75`
- Router selections:
  `62db0f928208f7e0975ebfe5e81b438c70fa304d66be217dde3d2cfdc8461dee`
- Summary metrics:
  `13881cefed9d7602f0af00977a62218e4fb94b50bf79ff989548c5ad5bb85176`
- Bootstrap intervals:
  `1bcf1c894192c0d83552dcd8c637838111f7cf2a8d20e12e54c5839f23dc395b`

## Publication decision

Keep the router as a tested component and negative/ablation result. Do not make
“dynamic algorithm selection improves diabetes prediction” the central claim
unless the effect becomes stable on the much larger BRFSS cohort. The stronger
current novelty direction is an availability-aware calibrated system that
quantifies degradation, selects only supported panels, explains predictions,
and abstains outside evaluated conditions.

## Next block

1. Scale feature-availability evaluation to BRFSS, where the sample is large
   enough to test routing stability properly.
2. Add a patient-result formatter combining probability, uncertainty/policy,
   SHAP factors, cohort context, panel provenance, and abstention reasons.
3. Implement the locked large-dataset holdout runner and final external-style
   evaluation path.
