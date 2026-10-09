# Final Internal-Validation Execution Checklist

**Execution completed:** 11 September 2026

**Protocol:** `t2dm-final-internal-validation-v1`

**Evidence tier:** `final_internal_validation`

**Canonical package:** `results/final_publication/`

This checklist supersedes the earlier proposal to manufacture new concealed
BRFSS/Hospital130 holdouts. Audit showed that those cohorts and their historical
partitions had already influenced development evidence. They are therefore
reported transparently as finalized, prespecified internal validation rather
than untouched independent tests.

## A. Frozen design

- [x] Endpoint definitions remain separated across PIDD, Sylhet, BRFSS, and
      Hospital130.
- [x] Hospital130 remains 30-day readmission and is never pooled with diabetes
      screening/status probabilities.
- [x] Protocol, raw-data hashes, split-manifest hashes, dataset-configuration
      hashes, analysis-configuration hashes, source-tree hash, and requirements
      lock are frozen in `config/final_publication_protocol.yaml`.
- [x] Five-model registry frozen: Logistic Regression, Random Forest, XGBoost,
      LightGBM, and CatBoost.
- [x] Average precision tuning objective, 75 trials, 2,000 bootstrap replicates,
      calibration candidates, threshold policies, availability panels, router,
      abstention, Holm correction, subgroup rules, and SHAP settings frozen.
- [x] All final sample limits are null.

## B. Defensible evaluation strategy

- [x] `BRFSS_FINAL_STRATEGY = INTERNAL_VALIDATION_ONLY` documented in
      `BRFSS_FINAL_EVALUATION_DECISION.md`.
- [x] `HOSPITAL130_FINAL_STRATEGY = COMPLETE_FULL_INTERNAL_VALIDATION`
      documented in `HOSPITAL130_FINAL_DECISION.md`.
- [x] BRFSS and Hospital130 metadata prohibit independent-holdout wording.
- [x] Sylhet identical predictor profiles remain grouped.
- [x] Hospital130 uses patient grouping and patient-cluster uncertainty.
- [x] No cross-cohort probability pooling or fabricated feature harmonization.

## C. Final execution

- [x] PIDD: `pidd_final_internal_validation_5739531d61c3`.
- [x] Sylhet: `sylhet_final_internal_validation_5d98677ca7d9`.
- [x] BRFSS: `brfss_final_internal_validation_holdout_2cfa4a7e2a3a`, all
      429,360 retained respondents with 85,872 internally evaluated rows.
- [x] Hospital130: `hospital130_final_internal_validation_holdout_26b332f2e8a8`,
      all 99,343 eligible encounters and 19,868 patient-grouped internally
      evaluated encounters.
- [x] All five trial ledgers contain 75 completed trials per dataset/model.
- [x] Calibration, thresholds, decision curves, availability routing,
      runtime fallback, abstention/selective prediction, subgroup uncertainty,
      and held-out SHAP analyses completed.
- [x] BRFSS survey-weight sensitivity completed with 2,000 replicates.
- [x] Failed pre-execution/downstream attempts were preserved and documented;
      no disappointing result was rerun away.

## D. Verification and publication package

- [x] Locked Python 3.12 environment and 48 pinned distributions verified.
- [x] Five BRFSS and five Hospital130 model bundles reproduced stored
      probabilities within `1e-12` across 85,872 and 19,868 rows respectively.
- [x] End-to-end leakage audit passed split identity, group isolation,
      preprocessing, bootstrap accounting, and SHAP reconstruction checks.
- [x] Full repository suite passed: 119 tests, 7 subtests; three upstream SHAP
      deprecation warnings only.
- [x] Canonical JSON, summary, CSV/Markdown/LaTeX tables, figure data, 600-dpi
      PNG, vector PDF/SVG, metadata, logs, receipts, decisions, deviations, and
      checksums exported.
- [x] Every manifest-listed package artifact passed SHA-256 verification.
- [x] Consolidated figure visually inspected for legibility and endpoint safety.
- [x] Negative router-switching finding retained without engineering it away.

## E. Remaining human release work

- [ ] Update the Discover Applied Sciences manuscript using only
      `results/final_publication/`.
- [ ] Complete author and independent statistical/scientific review.
- [ ] Finalize venue-specific TRIPOD+AI and PROBAST+AI mappings.
- [ ] Confirm authorship, affiliations, declarations, code license, and dataset
      use statements.
- [ ] Archive the source, studies, and canonical package immutably and record
      the DOI/archive identifier.
- [ ] Do not claim external, temporal, prospective, clinical, causal, or
      untouched-independent validation without new evidence.

## Recovery rule

The completed studies are immutable evidence. A source or methodological change
requires a new protocol version and new authorization; existing outputs must
remain preserved. The documented packaging-only repair may regenerate tables
and figures from unchanged study artifacts, but it may not reinterpret or
modify those artifacts.
