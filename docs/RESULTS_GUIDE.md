# Results guide

## Current publication evidence

`results/final_publication/` is a tracked, reviewed aggregate package. Start with
`FINAL_RESULTS.json`, `FINAL_RESULTS_SUMMARY.md` and
`provenance/frozen_protocol.yaml`. `config/authoritative_studies.yaml` maps each
cohort to its final study. `tables/` contains machine-readable CSV plus Markdown
and LaTeX presentations; different formats are intentional, not duplicates to
remove. `figure/` contains PNG, PDF, SVG and the three plotted source-data files.

| Evidence | Source and interpretation |
|---|---|
| Full-model comparisons | `full_panel_model_performance.csv`, `model_performance_confidence_intervals.csv`, `statistical_comparisons.csv`; five models per endpoint |
| Threshold results | `threshold_metrics.csv`, `threshold_performance.csv`, `descriptive_threshold_confidence_intervals.csv`; distinguish development-selected thresholds from threshold-free probability estimands |
| Prespecified masked panels | `availability_panel_degradation.csv`, `availability_panel_confidence_intervals.csv`, `repeated_panel_all_system_performance.csv`; fixed scenario/stress estimand |
| Actual fallback and coverage | `routing_fallback_performance.csv`; largest supported panel policy, robust fixed and full-panel fixed comparators |
| Calibration and utility | `calibration_selection.csv`, `decision_curves.csv`, decision-curve intervals/contrasts; retrospective model utility only |
| Selective and subgroup analyses | `selective_prediction_*`, `subgroup_*`; inspect accepted sample/event counts and interval status |
| Explanations | `shap_summary.csv`; model associations with endpoint/scale limits |
| BRFSS survey sensitivity | `brfss_survey_weighted_*`; a separate survey estimand |
| Consolidated figure | `figure/data/panel_a_calibration.csv`, `panel_b_decision_curves.csv`, `panel_c_availability_degradation.csv` |

PIDD and Sylhet repeated predictions are averaged per participant before the
reported probability-level summaries; Sylhet intervals preserve identical
predictor-profile clusters. Fixed masked-panel evaluation and naturally missing
runtime fallback answer different questions. Cross-cohort probabilities are
never pooled, and Hospital130 is always 30-day readmission.

`provenance/protocol_correction.json` records October corrected source selection,
aggregation and uncertainty, with input hashes and executed-code fingerprints.
`correction_value_changes.csv` and interval-change tables retain before/after
comparisons. The existing `superseded_pre_protocol_correction/2026-10-03/`
archive preserves the original 87-file fingerprint manifest, earlier summaries,
study derivatives and executed correction-code snapshots. The current manifest
contains 101 fingerprints. Neither historical evidence nor negative switching
findings were removed during cleanup.

The completed final study IDs are:

- PIDD: `pidd_final_internal_validation_5739531d61c3`
- Sylhet: `sylhet_final_internal_validation_5d98677ca7d9`
- BRFSS: `brfss_final_internal_validation_holdout_2cfa4a7e2a3a`
- Hospital130: `hospital130_final_internal_validation_holdout_26b332f2e8a8`

## Source artifacts and historical evidence

Private `outputs/publication_pipeline/studies/<study_id>/` directories retain
predictions, models, trials, calibration/threshold decisions, routing bundles,
subgroup/selective analyses, SHAP outputs, receipts and checkpoints. Splits and
raw data are preserved locally with hashes. These are not clone contents; see
[ARTIFACT_ARCHIVING.md](ARTIFACT_ARCHIVING.md).

`conference_package/`, `docs/progress_reports/`, the September audit and historical
development study IDs are dated traceability records. Their original paths are
referenced by report builders/manifests. They are retained in place and must not
be cited as the current finalized evaluation.

The current manuscript target is Discover Computing. Frozen protocol and some
September records still name Discover Applied Sciences; preserve their original
bytes and update submission-facing metadata separately after author review.
The sibling `journal_readiness_revision/` manuscript package is outside this
repository and was left intact; complete manuscript-to-table verification still
requires that final author-approved package.
