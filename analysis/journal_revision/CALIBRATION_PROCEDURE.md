# Calibration procedure from implementation

Sources: `calibration/calibrators.py::{fit_calibrator,select_calibrator}`, `training/tuning.py::{cross_fitted_probabilities,cross_fitted_probabilities_by_scenario}`,
`routing/evaluator.py`, `routing/holdout_evaluator.py`, `runner.py`, `holdout_runner.py`.

## Base-model original full-schema calibration

Each fitted family has an original calibrator selected using full-schema base out-of-fold training/development probabilities.
PIDD/Sylhet: five inner training folds inside each of 25 outer training partitions; Sylhet uses full-predictor identical-profile groups.
BRFSS/Hospital130: five original development folds from the manifest; Hospital130 preserves patients.
Hyperparameters are selected on the corresponding training/development data, never outer/evaluation labels.
The base OOF predictions are cross-fitted conditional on hyperparameters chosen using the same development partition;
this is not a fully nested-out-of-sample estimate of the hyperparameter selection process itself.

## Panel-specific masked-development calibration

Original router candidates are random_forest, xgboost, lightgbm and catboost; Logistic Regression is a benchmark family but not an original router candidate.
For each candidate, `cross_fitted_probabilities_by_scenario` refits preprocessing and the full-schema base model inside each training fold.
It masks excluded predictors only in that fold's held-out development records and applies training-fitted preprocessing.
There is one base OOF probability per development/training record and scenario. Missingness indicators and categorical vocabularies remain training-local.
Every family/scenario, including full, receives calibration selection; identity is an eligible mapping, not an unsupported/no-calibration error.

`select_calibrator` performs a second five-fold (or class-count-capped) layer on the base OOF probabilities. Candidates fit on calibration-training
labels and are scored only on calibration-validation labels. Grouped data use StratifiedGroupKFold with shuffle and the recorded seed;
individual data use StratifiedKFold. Both classes must have at least two observations.
Identity clips p to [1e-6, 1-1e-6]. Sigmoid fits unpenalized LogisticRegression(C=infinity, lbfgs, max_iter=2000)
on logit(clipped p). Isotonic fits IsotonicRegression(out_of_bounds=clip) on clipped probabilities.
The final profile requires >=1000 observations in the input calibration population for isotonic eligibility.
The threshold is checked on the supplied overall calibration population, not independently enforced on every calibration-training subfold.
Thus isotonic is ineligible throughout PIDD/Sylhet; it can be selected for BRFSS/Hospital130.

Cross-fitted Brier score is minimized, log loss breaks ties, then configured method order identity/sigmoid/isotonic.
The winning mapping is refitted on all supplied training/development OOF probabilities/labels and applied once to the outer/evaluation raw probabilities.
The second layer re-splits precomputed base OOF probabilities; it does not refit base learners for each calibration subfold.
Group boundaries are maintained by each layer, but this is conditional cross-fitting, not an independently nested calibration-selection study.
Family/panel choices minimize development Brier then log loss then negative AP; robust fixed family averages development scores across scenarios.
No evaluation labels are used in mapping or family selection. Selected identity maps and sigmoid/isotonic maps are exported per fold/scenario in MODEL_CONFIGURATIONS.csv.

## New controlled comparisons

Reduced-schema models fit both preprocessing and base learners using only declared panel columns in each original training partition.
Five OOF base fits use the original panel-calibration splitting seeds and seeds for corresponding base OOF fits;
five calibration folds use original calibration seeds/candidates/minimum counts. Final model fitting uses original final seeds.
The family and hyperparameters are frozen to the original panel's development choice. No new tuning or evaluation-driven family selection occurs.
Original full-schema tuning budgets are inherited equally and disclosed; this is a matched-parameter schema experiment, not an independently retuned optimum.

In the 2x2 ablation A/C use the original model-bundle full-schema calibrator on masked raw scores; B/D use the saved scenario-specific calibrator.
Both calibrated and raw per-repeat/participant probabilities are retained privately. B matches the historical robust runtime policy;
D matches the original framework. A is fixed imputation with original full-schema calibration. Family choices remain fixed across calibration arms.
Evaluation calibration intercept/slope are joint logistic descriptive diagnostics from `evaluation/metrics.py`;
these evaluation mappings are never applied to the evaluated predictions.
