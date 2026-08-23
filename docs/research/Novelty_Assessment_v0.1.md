# Novelty Assessment v0.1

**Date:** 23 August 2026

**Status:** Development conclusion; requires database-complete search and independent review

## Verdict

The project still has a plausible conference contribution, but the novelty is
narrower than the software implementation.

The following are not publishable novelty claims by themselves:

- comparing Logistic Regression, Random Forest, XGBoost, LightGBM, and CatBoost;
- applying SHAP to diabetes models;
- reporting calibration, fairness, or ordinary feature ablations;
- handling missing predictors by imputation or pattern-specific submodels;
- automatically choosing a model or suggesting the next feature to collect;
- accepting mixed namespaced input in a software interface.

Each of those ideas is already represented in the screened literature. In
particular, a 2026 BRFSS study reports tree-model comparison, Brier/calibration,
fairness, SHAP, and ablation, while established methodological studies cover
pattern submodels, real-time missing-predictor imputation, and dynamic feature
acquisition.

## Provisional primary contribution

> A prespecified, endpoint-safe framework for evaluating calibrated prediction
> degradation across clinically interpretable feature-availability panels, with
> explicit abstention, paired uncertainty, and complete routing provenance across
> separately analysed diabetes-status environments.

The central scientific product is the degradation and coverage evidence, not the
router's existence and not a model leaderboard.

## Secondary contributions

1. Leakage-controlled evaluation for small duplicate-heavy and population-specific
   diabetes datasets, including profile grouping and participant-level repeated-CV inference.
2. Comparison of an availability router with robust fixed-family and full-panel-
   champion-family baselines using proper probability scores and paired uncertainty.
3. A contract-driven mixed-input demonstration that refuses cross-cohort probability
   fusion and exposes applicability/abstention reasons.

## Required direct comparisons

| Closest work | Established contribution | Required contrast in our study |
|---|---|---|
| Pattern submodels | Selects a submodel matching an observed missing-data pattern | We use named, clinically interpretable panels and evaluate calibration/degradation/coverage prospectively across endpoint-separated datasets |
| Real-time imputation | Applies one risk model when individual predictors are unavailable | We must acknowledge this alternative and compare or discuss why panel-specific models are appropriate for the intended interface |
| Explanation-guided dynamic feature selection | Flexible risk estimates plus personalized next-feature recommendation | Our study does not claim adaptive acquisition; it tests prespecified availability environments and abstention |
| BRFSS calibration/fairness/SHAP study | Multi-model BRFSS evaluation with reliability and fairness components | Our differentiation is availability-panel degradation and routing evidence, not the metric catalogue |
| AutoPrognosis | Automated clinical pipeline and model selection | Our contribution is a frozen evaluation design and endpoint/applicability contract, not AutoML automation |

## Negative-result commitment

Dynamic model-family switching will remain secondary. If the router does not meet
the frozen practical-effect and corrected-uncertainty criteria, the paper will state
that a robust fixed family was sufficient. The primary contribution can survive as
an availability/degradation study only if the panel, calibration, abstention, and
uncertainty analyses are complete and informative.

## Publication feasibility

- Conference scope: feasible if the full development and locked analyses validate
  the degradation/abstention contribution and the comparison with closest work is complete.
- Journal scope: not yet sufficient without external or temporal validation and a
  stronger transportability analysis.
- Clinical/deployment claims: prohibited with the current public retrospective datasets.

## Novelty lock gate

- [x] Ordinary model comparison is excluded from novelty.
- [x] SHAP/calibration/fairness/ablation are excluded as standalone novelty.
- [x] Pattern-submodel, real-time-imputation, and dynamic-feature-selection work is identified.
- [x] One provisional primary and three secondary contributions are written.
- [x] A negative dynamic-switching statement is written.
- [ ] Searches are completed in at least two scholarly databases.
- [ ] Full extraction is completed for the closest diabetes and missing-predictor studies.
- [ ] A supervisor or second reviewer confirms the closest-work assessment.
- [ ] SAP margins and threshold ranges are revised or justified from evidence.

`novelty_review_complete` must remain false until the unchecked items are closed.
