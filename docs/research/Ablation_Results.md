# Development Ablation Results

**Updated:** 23 August 2026

**Status:** Artifact-based components complete; retraining-dependent components open

## Scope

The implemented ablation runner reuses identical held-out participants and
performs paired individual or cluster bootstrap comparisons with metric-wise
Holm correction. It currently covers:

1. selected calibration versus raw probabilities;
2. availability routing versus a robust fixed model;
3. Brier-based routing selection versus average-precision and log-loss selection;
4. tree model families versus Logistic Regression where that baseline exists;
5. the separately implemented matched full-panel versus reduced-panel contrasts.

Repeated-CV probabilities are averaged to one probability per participant before
inference. Sylhet resamples complete identical-profile clusters. Holdout studies
use the same held-out respondents for both sides of every contrast.

## Development findings

The current PIDD and Sylhet pilots show no Holm-corrected advantage for the
availability router over the robust fixed-model baseline and no corrected
advantage for changing the selection objective away from Brier score. This
supports retaining algorithm switching as a secondary or potentially negative
result rather than the primary contribution.

PIDD selected calibration produced corrected development improvements for three
model-metric contrasts: Random Forest AUROC and log loss, and XGBoost log loss.
In Sylhet, CatBoost average precision exceeded Logistic Regression in one
corrected development contrast. These are pilot findings with only 200 bootstrap
replicates and cannot be presented as final evidence.

The matched-panel analysis remains the more relevant contribution: PIDD's
non-laboratory panel produced consistent Brier and average-precision degradation,
whereas removal of insulin and skinfold measurements was close to neutral in the
current pilot.

BRFSS artifact ablations are smoke-only. The older BRFSS routing study did not
contain Logistic Regression, so the model-family baseline is correctly recorded
as unavailable rather than silently omitted or reconstructed post hoc.

## Remaining ablations

The ablation blocker remains open. Completion still requires:

- missing-indicator on/off retraining on identical folds and budgets;
- full-panel masked inference versus models trained separately per panel;
- prespecified random feature-dropout stress experiments;
- applicability/abstention guard removal, coordinated with selective prediction;
- a clearly non-deployable global-preprocessing leakage demonstration;
- a clearly non-deployable grouped-versus-naive Sylhet split demonstration.

No value in `config/publication_protocol.yaml` is changed by this report.
