# Development Ablation Results

**Updated:** 24 August 2026

**Status:** All prespecified development ablation paths complete; scientific review pending

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

The completed full-budget PIDD and Sylhet development studies show no
Holm-corrected advantage for the availability router over the robust fixed-model
baseline and no corrected
advantage for changing the selection objective away from Brier score. This
supports retaining algorithm switching as a secondary or potentially negative
result rather than the primary contribution.

PIDD selected calibration produced corrected development improvements for three
model-metric contrasts: Random Forest AUROC and log loss, and XGBoost log loss.
In Sylhet, CatBoost average precision exceeded Logistic Regression in one
corrected development contrast. These are development findings and cannot be
presented as locked final evidence.

The matched-panel analysis remains the more relevant contribution: PIDD's
non-laboratory panel produced consistent Brier and average-precision degradation,
whereas removal of insulin and skinfold measurements was close to neutral.

BRFSS artifact ablations are smoke-only. The older BRFSS routing study did not
contain Logistic Regression, so the model-family baseline is correctly recorded
as unavailable rather than silently omitted or reconstructed post hoc.

The missing-indicator retraining runner has completed all 25 outer splits on
PIDD and Sylhet for Logistic Regression and Random
Forest. Both variants were separately tuned on identical outer and inner folds,
trial budgets, search spaces, and seeds. The PIDD development study covered all
768 participants and produced eight complete paired contrasts with individual
resampling; none showed a Holm-corrected advantage for indicators. Sylhet
covered all 520 participants with cluster resampling and produced exact null
Random Forest contrasts plus small Logistic Regression differences; no contrast
survived correction and all Logistic Regression adjusted p-values were 1.000.
This is expected because the dataset has no applicable numeric missingness for
the indicator transformer. A numerical-equivalence guard
collapses probability differences within `1e-12` before inference, preventing
machine-precision noise from creating rank or sign-test artifacts. These remain
development findings and cannot enter a locked final results table.

Panel-specific training versus masked full-panel inference has now been run for
Random Forest and XGBoost across all five reduced PIDD panels and all four
reduced Sylhet panels. The analysis produced 40 PIDD individual-resampled and 32
Sylhet cluster-resampled contrasts. The full Sylhet execution produced 41,600
held-out prediction rows from 200 separately tuned tasks. No contrast remained
significant after
metric-wise Holm correction. Brier changes were small and usually crossed zero;
the largest observed PIDD improvement was 0.0034 for Random Forest on the
non-laboratory panel. The minimum adjusted Sylhet p-value was 0.064. These
results do not justify claiming that separate per-panel training is superior.

Random missingness stress testing now covers MCAR-like independent masks and
structured block masks at 0%, 25%, 50%, and 75% imposed severity with shared
masks across Random Forest and XGBoost. PIDD mean Brier scores worsened from
approximately 0.155 at baseline to 0.209-0.213 at the highest severity, while
named-panel coverage fell to 4-7%. Sylhet Brier scores worsened from 0.076-0.080
to 0.246-0.295 and supported-panel coverage fell to 4-6%. This supports explicit
applicability abstention. These simulations are stress tests, not MNAR or
real-world deployment validation.

The applicability-guard ablation shows why retained-case metrics must not be
reported without coverage. Under 75% imposed dropout, the named-panel guard
retained only about 5.5% of PIDD and 5.0% of Sylhet participants and a similar
fraction of positive events. Most guarded fold-replicate cells were therefore
suppressed. The lower retained-case Brier scores do not justify claiming better
overall performance; the proper behavior is explicit abstention outside a
supported panel.

The non-deployable leakage demonstrations found negligible change from global
preprocessing alone in the present data. In contrast, naive row-level Sylhet
splitting allowed 263 identical-profile overlaps across five folds, inflated
AUROC from 0.9574 to 0.9735, and reduced Brier from 0.0798 to 0.0565. This
confirms that group-preserving Sylhet evaluation is necessary.

Panel-size-only fits explain little PIDD named-panel variation (R-squared 0.18
for Brier and 0.08 for AP), supporting clinically meaningful panel composition
over feature count alone. Size explains more Sylhet panel variation (R-squared
0.89-0.91), but the small five-panel design makes this descriptive rather than a
validated selection rule. Grouped original-feature SHAP retained the leading
features while collapsing PIDD missing-indicator expansions; it is therefore
the primary explanation format.

## Remaining ablations

No prespecified development ablation execution remains. The protocol flag stays
false until the completed evidence is jointly reviewed, its retained components
are recorded in the frozen decision report, and the authorized final analysis is
run without post-hoc expansion.

No value in `config/publication_protocol.yaml` is changed by this report.
