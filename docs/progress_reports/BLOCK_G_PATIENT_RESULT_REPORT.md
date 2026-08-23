# Block G Checkpoint: Detailed Patient Research Result

## Status

The availability router now has an end-to-end, probability-first result layer.
It accepts one partially observed record, routes it through every saved outer-
fold router, aggregates the calibrated probabilities, computes local SHAP
explanations, adds descriptive cohort context, and returns either JSON or a
readable Markdown report.

This is deliberately labelled as research validation output. It is not a
diagnostic device or treatment recommendation.

## Why the result uses five model folds

The PIDD routing pilot did not identify one stable best algorithm. For example,
the no-insulin/no-skinfold panel selected CatBoost in three folds and Random
Forest in two. A single saved fold would hide this model-selection instability.

The formatter therefore reports:

- Mean calibrated probability across the five independently developed routers.
- Minimum, maximum, and standard deviation across model folds.
- The number of folds at or above the predeclared threshold.
- Model and calibration-method selection counts.
- Every fold-level probability for reproducibility.

The fold spread is explicitly described as model-fold variability, not a
confidence interval.

## SHAP aggregation contract

Tree SHAP is computed separately for the model selected by each fold. Every
explanation must reconstruct that model's raw output within an absolute error of
`1e-4`.

Absolute SHAP magnitudes from Random Forest probabilities and boosted-tree raw
margins are not averaged. Instead, contributions are:

1. grouped back to the original patient feature;
2. normalized within each fold;
3. ranked within each fold; and
4. summarized by mean normalized importance, median rank, direction agreement,
   and fold counts.

The language says that a factor raised or lowered the model estimate. It never
says that the factor caused the outcome.

## Additional patient context

For each leading numeric factor, the report locates the patient's value in a
quantile band of the reference cohort and reports the observed outcome
prevalence in that band beside overall cohort prevalence. This supports useful
statements such as “this age band had a higher observed prevalence in the study
cohort” without inventing a clinical age cutoff.

All context is labelled unadjusted, observational, cohort-specific, non-causal,
and unsuitable as a personalized recommendation.

## Safety and applicability behavior

The system produces no probability when:

- no predeclared feature panel is supported;
- a numeric field is invalid or non-finite;
- a required scenario is requested but its fields are missing; or
- a used numeric value is outside the reference dataset's observed range.

Out-of-range behavior can be relaxed to a warning only through an explicit
command option. Unknown fields are ignored and reported. Patient input and
results are not saved by default.

## Synthetic integration example

The synthetic example intentionally omits Insulin. The largest supported panel
was `no_insulin_or_skinfold`, which uses six predictors and masks Insulin and
SkinThickness exactly as in the routing experiment.

- Mean calibrated probability: **0.6605**.
- Model-fold range: **0.5954 to 0.7838**.
- Model-fold standard deviation: **0.0660**.
- Folds at or above the 0.5 research threshold: **5 of 5**.
- Selected models: CatBoost in 3 folds; Random Forest in 2.
- Leading factors: Glucose, Age, BMI, Pregnancies, and diabetes pedigree score.
- SHAP direction agreed across all five folds for each of those five factors.
- Maximum SHAP reconstruction error: less than `5e-15`.

These numbers demonstrate the formatter and are not a real patient's result.

## Verification

- 23 automated tests plus 5 model-adapter subtests pass.
- Integer-valued JSON inputs and feature-panel masking are covered by a
  regression test.
- Prediction, unsupported-panel abstention, and out-of-range abstention paths
  pass.
- Two complete JSON runs for the synthetic example were byte-identical.
- Deterministic synthetic-result SHA-256:
  `e9fcdde23426bd32cc5236772bb2cb8562cd0a563948fa3fcd218f9e36c49997`.
- Source-tree SHA-256 at verification:
  `13b5996cf0a46bbb0efa3b7337c8473c90a2a28f49c2e015291c98df9a8906f0`.

## Publication value

This component turns the project from a leaderboard comparison into a tested
decision-support research pipeline: incomplete-input routing, calibrated
probability, model uncertainty proxy, local explanation, cohort-relative
context, provenance, and safe abstention are evaluated together.

It should be presented as a prototype and methodological contribution until a
final model is refitted on all development data and externally/prospectively
validated.
