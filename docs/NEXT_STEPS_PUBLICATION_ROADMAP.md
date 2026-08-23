# Comprehensive Next-Steps and Publication Roadmap

**Project:** Multi-dataset diabetes prediction and feature-availability routing pipeline

**Prepared:** 23 August 2026

**Current target:** Defensible conference submission first; journal extension after external or temporal validation

**Current readiness:** Not ready — 16 blocking checks and 1 journal-strength warning

## Execution status

Execution began on 23 August 2026. Phase 0 baseline capture and governance
documentation are complete. The environment, source/configuration hashes,
raw-data hashes, split manifests, capacity, test results, evidence tiers, and
publication blockers are recorded under `docs/research/`. The existing seed-42
BRFSS and Hospital130 test partitions are permanently classified as
development-only because earlier smoke and audit runs exposed their outcomes.

Phase 1 protocol documents are now in draft. They remain unlocked and may be
revised using development evidence and the structured novelty review. No new
final holdout may be generated or accessed until the protocol-freeze gate.

## 1. Purpose of this roadmap

This document defines the order of work required to turn the current research-grade software prototype into a defensible scientific study. It is deliberately stricter than a normal software to-do list. The final result must satisfy four independent requirements:

1. The software must behave correctly and reproducibly.
2. The numerical results must be estimated without leakage or test-set adaptation.
3. The scientific claim must be novel, supported, and narrower than the software's full capability.
4. The manuscript must satisfy modern clinical-prediction reporting and risk-of-bias expectations.

The roadmap prevents a common failure mode: repeatedly improving results after seeing the final test set. Development work may change models, panels, calibration, thresholds, and analyses. After the protocol is frozen and the final evaluation begins, those choices may not be changed in response to final results.

## 2. Current scientific position

### 2.1 What is already implemented

- Dataset-specific pipelines for PIDD, Sylhet, BRFSS, and Hospital130.
- Endpoint isolation: Hospital130 predicts 30-day readmission and is not pooled with diabetes-screening endpoints.
- Five model families: Logistic Regression as a benchmark plus Random Forest, XGBoost, LightGBM, and CatBoost.
- Fold-fitted preprocessing, tuning, calibration, threshold estimation, uncertainty estimation, and saved provenance.
- Twenty-two prespecified feature-availability panels across the four datasets.
- Within-dataset availability routing and model-bundle reload.
- Namespaced mixed-patient input with explicit abstention when several cohort experts are eligible and no environment is selected.
- Patient-level probability reports, applicability checks, provenance, and SHAP explanations.
- Automated software tests and a publication-readiness gate.

### 2.2 What the present results support

- The models have useful discrimination on the configured endpoints.
- Performance degrades in a measurable and often graceful manner as feature availability falls.
- Some reduced panels retain nearly all full-panel discrimination, especially PIDD without insulin/skinfold and compact BRFSS cardiometabolic panels.
- The availability router functions and remains close to strong fixed-model baselines.

### 2.3 What the present results do not support

- They do not prove that dynamic algorithm switching is superior.
- They do not validate automatic cross-dataset selection or probability fusion.
- They do not estimate future diabetes incidence or age of onset.
- They do not justify clinical deployment.
- Pilot and smoke results cannot be placed in the manuscript's final primary-results table.

### 2.4 Proposed primary paper claim

The recommended primary claim is:

> A prespecified, availability-aware, calibrated and abstaining prediction pipeline can quantify and manage performance degradation across clinically meaningful missing-feature environments while preserving endpoint boundaries and prediction provenance.

Dynamic model switching should remain a secondary or negative result unless the locked final analysis shows a clear, corrected, practically meaningful advantage.

The mixed-source patient interface should remain a software demonstration. It must not be described as learned multi-cohort fusion unless a matched cohort containing jointly observed source profiles becomes available.

## 3. Non-negotiable study rules

1. Do not cite smoke or development-pilot estimates as final evidence.
2. Do not access a new final holdout before the protocol, code, panels, metrics, thresholds, and claims are frozen.
3. Do not change the pipeline because of an unfavorable final result.
4. Do not average PIDD, Sylhet, and BRFSS probabilities.
5. Do not mix Hospital130 readmission results into the diabetes-screening efficacy claim.
6. Do not describe BRFSS or the cross-sectional screening datasets as predicting the age at which diabetes will develop.
7. Do not use accuracy or F1 as the sole evidence of clinical usefulness.
8. Report negative and statistically inconclusive comparisons.
9. Set a publication-protocol flag to `true` only after its signed-off artifact exists.
10. Preserve every final configuration, raw-data hash, split hash, source-tree hash, model bundle, and analysis output.

## 4. Critical path overview

The work must proceed in this order:

1. Preserve the current baseline and create an issue/evidence register.
2. Freeze the scientific question, endpoint hierarchy, claims, metrics, and analysis plan.
3. Complete the structured literature and novelty review.
4. Complete data, split, leakage, and applicability audits.
5. Harden the remaining software and artifact contracts.
6. Run development-only full-budget analyses and all ablations.
7. Complete selective-prediction and subgroup/fairness analyses on development evidence.
8. Review all development evidence and sign off the frozen protocol.
9. Tag the frozen code and create the fresh final evaluation.
10. Run final PIDD, Sylhet, and BRFSS experiments exactly once under the approved design.
11. Perform frozen statistical analysis, explanations, tables, and figures.
12. Complete TRIPOD+AI, PROBAST+AI, and claim-to-evidence traceability.
13. Prepare and internally reproduce the conference manuscript.
14. Add external or temporal validation for a journal extension.

## 5. Phase 0 — Baseline preservation and project control

### Objective

Create a reproducible starting point and ensure that pilot outputs are never confused with final evidence.

### Tasks

- Record the current repository commit, source-tree hash, Python version, operating system, dependency versions, and model-library versions.
- Run the full automated test suite and retain the machine-readable test result.
- Run configuration validation, feature-map generation, dataset audits, artifact reload tests, and CLI help checks.
- Archive the current pilot/smoke study identifiers and label their evidence tier as development-only or execution-only.
- Record raw-file hashes, cleaned-row counts, endpoint prevalence, excluded rows, duplicates, and grouping strategy for every dataset.
- Confirm that ignored output directories are backed up and that irreplaceable final artifacts will be archived outside transient working directories.
- Create a blocker register mapping each of the 16 readiness failures to an owner artifact and completion check.
- Create a decision log. Every later change to panels, metrics, thresholds, or claims must state its development evidence and approval date.

### Deliverables

- `docs/research/Baseline_Reproducibility_Record.md`
- `docs/research/Decision_Log.md`
- `docs/research/Publication_Blocker_Register.md`
- Baseline test and audit logs under a dated development-only directory.

### Exit gate

- Clean reproducibility record exists.
- All tests and audits pass, or every failure is documented and scheduled before Phase 5.
- Current pilot/smoke artifacts are visibly marked ineligible for manuscript claims.

## 6. Phase 1 — Scientific question, endpoint, and protocol design

### Objective

Convert the broad software project into a narrow, testable study before further optimization.

### Tasks

#### 6.1 Define the study hierarchy

- Primary task: diabetes-screening/status prediction under varying feature availability.
- Primary datasets: PIDD, Sylhet, and BRFSS, analyzed separately rather than pooled.
- Secondary endpoint: Hospital130 30-day readmission, reported separately.
- Software-demonstration analysis: mixed-source request routing and abstention.
- Future work only: age of diabetes onset and learned cross-dataset fusion.

#### 6.2 Define hypotheses

- Primary availability hypothesis: the proposed router improves or preserves proper probability performance relative to prespecified practical baselines across feature panels.
- Robustness hypothesis: compact clinically plausible panels retain useful discrimination and calibration relative to full panels.
- Selective-prediction hypothesis: abstention improves retained-case performance as coverage decreases.
- Secondary model-selection hypothesis: dynamic selection may or may not outperform a robust fixed model; superiority will not be assumed.

#### 6.3 Prespecify outcomes

- Tuning metric: average precision, as currently configured.
- Router-selection metric: Brier score, with log loss and negative average precision as deterministic tie-breakers.
- Primary reported probability metrics: Brier score, log loss, calibration intercept, calibration slope, observed/expected ratio, and calibration curves.
- Primary discrimination metrics: AUROC and average precision with uncertainty.
- Thresholded secondary metrics: sensitivity, specificity, PPV, NPV, balanced accuracy, F1, MCC, and confusion matrix.
- Clinical utility: decision-curve net benefit across prespecified clinically meaningful thresholds.
- Selective prediction: coverage, accepted-case Brier/log loss/AUROC/AP, abstention rate, failure reason, and subgroup coverage.
- Model comparison: paired effect sizes, confidence intervals, raw p-values, and multiplicity-adjusted p-values.

#### 6.4 Prespecify threshold policy

- Keep fixed 0.5 only as a descriptive benchmark.
- Define the sensitivity-constrained threshold as the primary screening operating point if 80% sensitivity remains clinically justified.
- Treat Youden's threshold as a secondary statistical operating point, not a clinical optimum.
- Define decision-curve threshold ranges separately for PIDD, Sylhet, and BRFSS because their prevalence and intended use differ.
- Never select a threshold using final evaluation labels.

#### 6.5 Define claim-success criteria

- Specify the minimum practically meaningful router improvement before seeing final results.
- Require confidence intervals, not just point-estimate improvement.
- Define when non-inferiority or graceful degradation is the appropriate conclusion.
- Define what result will cause the dynamic-routing claim to remain negative.
- Define what calibration behavior is unacceptable even when AUROC is high.

#### 6.6 Statistical analysis plan

- Specify repeated nested cross-validation for PIDD and grouped Sylhet evaluation.
- Specify development/locked-test separation for BRFSS.
- Specify patient-cluster resampling for Hospital130.
- Specify bootstrap unit, stratification, confidence level, and number of resamples.
- Specify paired comparisons and Holm multiplicity correction.
- Specify missing-data handling inside folds.
- Specify subgroup minimum sample and event counts; suppress unsupported estimates rather than publishing unstable values.
- Specify how failed folds, degenerate calibration fits, and unavailable metrics will be handled.

### Deliverables

- `docs/research/Statistical_Analysis_Plan.md`
- `docs/research/Endpoint_and_Claim_Hierarchy.md`
- `docs/research/Threshold_and_Clinical_Utility_Policy.md`
- Updated protocol configuration, still unlocked until formal sign-off.

### Exit gate

- Every manuscript claim has a defined endpoint, comparison, metric, dataset, and success criterion.
- Hospital130 and mixed routing are correctly scoped.
- No unresolved analysis choice depends on future final-test results.

## 7. Phase 2 — Literature review and novelty lock

### Objective

Prove that the paper contributes more than another algorithm comparison on public diabetes datasets.

### Tasks

- Build a structured literature matrix covering:
  - PIDD prediction studies.
  - Sylhet symptom-based prediction studies.
  - BRFSS diabetes-status prediction studies.
  - Hospital130 readmission studies.
  - Missing-feature and feature-availability prediction.
  - Dynamic model routing and mixture-of-experts approaches.
  - Selective prediction, abstention, and risk-coverage analysis.
  - Calibration and decision-curve analysis in clinical prediction.
  - Multi-source or multi-environment clinical prediction.
- Record for every paper: cohort, endpoint, sample size, split design, leakage controls, models, tuning, calibration, metrics, uncertainty, external validation, fairness analysis, code availability, and limitations.
- Identify inflated or non-comparable results caused by resampling before splitting, duplicate leakage, different target definitions, balanced test sets, or accuracy-only reporting.
- Compare the proposed router against the closest methodological work, not only diabetes benchmark papers.
- Write one primary novelty statement and no more than three secondary contributions.
- Write a negative-claim statement acknowledging that algorithm switching may not beat a strong fixed model.
- Select a conference scope and a journal-extension scope before final analysis.

### Deliverables

- `docs/research/Literature_and_Novelty_Matrix.xlsx`
- `docs/research/Novelty_and_Contribution_Statement.md`
- `docs/research/Related_Work_Outline.md`

### Exit gate

- `novelty_review_complete` may become true only after the matrix and claim statement are reviewed.
- The novelty is availability-aware calibrated abstention and degradation analysis, unless stronger development evidence justifies otherwise.

## 8. Phase 3 — Data, endpoint, leakage, and applicability audit

### Objective

Ensure that every final estimate has a valid target, population, split, and intended interpretation.

### Tasks by dataset

#### PIDD

- Confirm all physiologically impossible zero values are converted to missing only inside the documented preprocessing contract.
- Reconfirm class prevalence and exact row count from the raw file.
- Preserve stratification and repeated nested evaluation.
- Document population restriction and prohibit general-population claims.

#### Sylhet

- Reconfirm all exact duplicate feature profiles.
- Verify identical profiles remain in the same group in every inner and outer split.
- Quantify the effect of grouping versus naive random splitting as a leakage demonstration, not as the primary result.
- Document single-center, symptom-enriched recruitment and high apparent separability.

#### BRFSS

- Verify the raw target coding, excluded prediabetes/borderline and pregnancy-only responses, and all missing/refused responses.
- Confirm that the task is self-reported diagnosed-diabetes status, not future incidence.
- Determine whether survey weights, strata, and primary sampling units are available. If available, define weighted descriptive and/or sensitivity analyses; if unavailable, state that population-representative inference is limited.
- Define a fresh final holdout that remains untouched until Phase 8.
- Predefine any temporal BRFSS year reserved for journal validation.

#### Hospital130

- Confirm patient-level grouping prevents encounters from the same patient crossing partitions.
- Reconfirm exclusions for expired/hospice discharge dispositions.
- Audit diagnosis and medication variables for post-outcome or discharge-time leakage.
- Keep the task separate from diabetes screening.
- Decide before final execution whether Hospital130 is a secondary paper analysis or excluded from the primary conference manuscript.

#### Cross-dataset semantics

- Revalidate the master feature ontology and namespacing.
- Identify features that are semantically related but not numerically exchangeable, such as age in years versus BRFSS age groups.
- Document why cohort probabilities cannot be averaged.

### Deliverables

- Final dataset audit reports and versioned split manifests.
- `docs/research/Data_Provenance_and_Eligibility.md`
- `docs/research/Leakage_Risk_Register.md`
- `docs/research/Applicability_and_Endpoint_Limitations.md`

### Exit gate

- No unresolved target leakage.
- No duplicate or patient grouping violations.
- Fresh final holdout definition exists but has not been evaluated.
- Every endpoint's wording matches the recorded label.

## 9. Phase 4 — Engineering and reproducibility hardening

### Objective

Remove software uncertainty before expensive development and final runs.

### Tasks

- Expand automated tests for every panel and dataset.
- Add property-based or matrix tests for:
  - Exact panel matches.
  - Supersets of panels.
  - Same-size panel tie-breaking.
  - Unknown fields.
  - Missing required scenario fields.
  - Non-finite numeric values.
  - Out-of-reference-range behavior.
  - Multiple eligible mixed experts.
  - Invalid preferred dataset.
  - Hospital130 endpoint mismatch.
- Verify saved-bundle reload reproduces original probabilities within a strict numerical tolerance.
- Verify calibration and thresholds are always learned from development predictions only.
- Verify preprocessing is fitted within folds and panel masking occurs before transformation.
- Add checks for source hash, raw-data hash, config hash, feature order, scenario contract, model version, and calibrator availability.
- Make all stochastic components deterministic under the recorded seeds.
- Add resumable experiment execution and explicit partial-run status so long final runs cannot silently produce incomplete tables.
- Add disk-space, dependency, and raw-file preflight checks.
- Produce machine-readable experiment manifests and validation summaries.
- Run static checks, tests, and a clean-environment installation test.
- Remove or ignore temporary Word lock files and other non-research artifacts from deliverables.

### Deliverables

- Expanded automated tests.
- `docs/research/Reproducibility_and_Artifact_Contract.md`
- Final-run preflight command and checklist.

### Exit gate

- Full test suite passes from a clean environment.
- Artifact reload is deterministic.
- Deliberate leakage and contract-mismatch tests fail safely.
- No final experiment is needed to debug ordinary software behavior.

## 10. Phase 5 — Full development experiments

### Objective

Use development evidence to make every remaining scientific and engineering choice before the final lock.

### Required experiment profile

Use the full datasets with the development profile: 30 tuning trials and 500 bootstrap resamples. These results remain development-only.

### Core model experiments

- Run Logistic Regression, Random Forest, XGBoost, LightGBM, and CatBoost on full panels.
- Run all four router candidates on every availability panel.
- Retain raw and calibrated probabilities.
- Evaluate identity, sigmoid, and eligible isotonic calibration strictly from development predictions.
- Confirm that optimization and calibration decisions are stable across repeats/folds.

### Required baselines

- Logistic Regression benchmark.
- One robust fixed tree model across all panels.
- Full-panel champion applied under missingness using the documented preprocessing strategy.
- Separate prespecified model per panel without dynamic family switching.
- Simple imputation plus fixed-model baseline.
- Oracle post-hoc best model, clearly labeled as an unattainable upper bound and never treated as a deployable comparator.

### Required ablations

- No calibration versus selected calibration.
- No routing versus panel routing.
- Fixed algorithm versus dynamic family selection.
- Full-panel model versus panel-specific training.
- Selection by Brier score versus average precision versus log loss.
- With and without abstention/applicability guards.
- With and without missingness indicators.
- Model-only explanation versus grouped original-feature explanation.
- Panel-size-only heuristic versus named clinically meaningful panels.

### Missingness and stress experiments

- Evaluate all 22 named panels.
- Add prespecified random feature dropout stress tests without changing the primary named-panel analysis.
- Where defensible, simulate severity levels resembling MCAR and structured/MAR-like missingness.
- Do not claim real-world MNAR validation from simulation alone.
- Test invalid values, unknown categories, reference-range violations, and unsupported panels.
- Measure failure reason and abstention rate, not merely successful predictions.

### Deliverables

- One development study directory per dataset.
- Development model/routing comparison tables.
- `docs/research/Development_Experiment_Decision_Report.md`
- `docs/research/Ablation_Results.md`

### Exit gate

- All later model, panel, calibration, and threshold choices can be justified from development evidence.
- Ablations are complete.
- Dynamic switching is either retained as a prespecified secondary analysis or removed from the primary claim.

## 11. Phase 6 — Selective prediction, clinical utility, and subgroup analysis

### Objective

Demonstrate whether the system remains useful and fair when it predicts, abstains, or operates at different thresholds.

### Selective-prediction tasks

- Define confidence/applicability scores without using final labels.
- Evaluate performance at prespecified coverage levels, for example 100%, 95%, 90%, 80%, and 70% where sample size permits.
- Plot risk-coverage or loss-coverage curves.
- Report which patients and subgroups are disproportionately rejected.
- Compare abstention against always-predict baselines.
- Separate abstention caused by missing panels, out-of-range inputs, and unvalidated cross-dataset ambiguity.

### Clinical-utility tasks

- Produce decision curves for all primary models and routing systems.
- Select clinically plausible threshold ranges before final evaluation.
- Report model, treat-all, and treat-none net benefit.
- Explain whether a threshold represents further testing, clinician review, or another action.
- Avoid calling a statistically optimized threshold clinically optimal without a decision context.

### Subgroup and fairness tasks

- Prespecify supported subgroups by dataset, including sex and age where available.
- Consider race/ethnicity and socioeconomic variables only where measurement and sample sizes support interpretation.
- Report subgroup prevalence, sample size, event count, AUROC, AP, Brier, calibration, sensitivity, specificity, and abstention coverage with uncertainty.
- Evaluate intersectional subgroups only when event counts are sufficient.
- Suppress unstable cells and state the suppression rule.
- Distinguish model fairness from dataset representativeness.

### Deliverables

- `docs/research/Selective_Prediction_Analysis.md`
- `docs/research/Clinical_Utility_Analysis.md`
- `docs/research/Subgroup_and_Fairness_Analysis.md`
- Risk-coverage, decision-curve, and subgroup figures.

### Exit gate

- `selective_prediction_evaluation_complete` and `subgroup_analysis_complete` may become true only after reviewed artifacts exist.
- The intended operating threshold has evidence beyond F1 or accuracy.

## 12. Phase 7 — Protocol freeze and final-run authorization

### Objective

Create the irreversible boundary between development and final evaluation.

### Freeze checklist

- Approve the statistical analysis plan.
- Approve endpoint and claim hierarchy.
- Approve datasets, exclusions, panels, baselines, models, tuning spaces, calibration methods, metrics, thresholds, comparisons, subgroup definitions, and missingness analyses.
- Approve final table and figure shells with blank result cells.
- Approve the novelty statement and literature matrix.
- Complete development ablations, selective prediction, and subgroup work.
- Resolve every engineering issue.
- Run the test suite and final-run preflight.
- Set `locked: true` in the final experiment profile only after approval.
- Set `protocol_frozen: true` only after the signed protocol exists.
- Tag the exact source revision and record all hashes.
- Protect the final split and prohibit exploratory access.
- Define the rule for handling infrastructure failure versus scientific failure.

### Deliverables

- Signed/versioned statistical analysis plan.
- Frozen configuration bundle.
- Tagged source revision.
- Blank primary-results table shells.
- Final-run authorization record.

### Exit gate

- No unresolved choice can be influenced by final outcomes.
- The readiness gate passes all pre-experiment requirements that can pass before final results.

## 13. Phase 8 — Locked final experiments

### Objective

Generate the only estimates eligible for the conference manuscript's primary results.

### PIDD final run

- Full sample.
- Five repeats of five-fold outer nested evaluation.
- Five-fold inner tuning.
- Seventy-five tuning trials per model/fold.
- Two thousand bootstrap resamples for final uncertainty.
- All prespecified full-panel and availability-routing analyses.

### Sylhet final run

- Full sample.
- Identical-feature-profile grouping in all nested splits.
- Five repeats of five-fold outer evaluation.
- Seventy-five tuning trials per model/fold.
- Two thousand bootstrap resamples.
- Explicit calibration-stability diagnostics.

### BRFSS final run

- Full development and final-test partitions with no smoke sample limits.
- All tuning, calibration, thresholds, and model/router selection from development data only.
- One locked access to the fresh test partition after all choices are frozen.
- Seventy-five tuning trials per model.
- Two thousand bootstrap resamples.
- Full-panel, availability-panel, subgroup, and decision-curve outputs.

### Hospital130 final/secondary run

- Run only if approved as a secondary endpoint or separate manuscript component.
- Preserve patient-grouped development/test separation and cluster bootstrap.
- Do not consume conference resources if it weakens the primary diabetes-screening narrative.

### Post-run rule

If the final result is disappointing, report it. Do not retune, replace panels, change thresholds, or create a new test split. Corrections are allowed only for demonstrable implementation errors; the error, correction, and rerun decision must be documented before rerunning.

### Deliverables

- Immutable final study directories.
- Complete model bundles and provenance.
- Final routing evaluations.
- Final held-out explanations.
- Run logs and completion manifests.

### Exit gate

- Every final study is complete, reloadable, and checksum-verified.
- No final-test labels were used for tuning, calibration, thresholding, or claim selection.

## 14. Phase 9 — Frozen final statistical analysis

### Objective

Turn final predictions into a complete, uncertainty-aware scientific result without adding post-hoc analyses disguised as prespecified work.

### Tasks

- Populate the frozen table shells.
- Report prevalence and positive counts with every dataset result.
- Report raw and calibrated performance.
- Report bootstrap confidence intervals for all primary measures.
- Report paired model/router differences with corrected p-values.
- Report effect sizes even when nonsignificant.
- Compare router, robust fixed model, panel-specific model, imputation baseline, and oracle upper bound.
- Quantify performance degradation from full to reduced panels.
- Evaluate calibration intercept/slope and visually inspect every calibration curve.
- Report net benefit over the prespecified threshold range.
- Report thresholded performance at the prespecified operating point.
- Report risk-coverage and subgroup results.
- Report model-selection frequency and instability across folds.
- Mark any unplanned analysis as exploratory.
- Write a results-conclusion consistency audit.

### Deliverables

- Final CSV tables and vector figures.
- `docs/research/Final_Statistical_Analysis_Report.md`
- `docs/research/Results_Conclusion_Consistency_Audit.md`

### Exit gate

- Every result statement has an artifact, metric definition, uncertainty estimate, and analysis role.
- Negative and inconclusive results are retained.

## 15. Phase 10 — Explainability and applicability reporting

### Objective

Provide model-behavior evidence without making causal or clinical-cutoff claims.

### Tasks

- Generate held-out SHAP explanations for the frozen selected models.
- Report grouped original-feature importance as primary for one-hot encoded features.
- Retain per-fold additivity checks and explanation stability.
- Identify features whose direction changes substantially across folds/models.
- Explain that SHAP describes model behavior, not causal effect.
- Avoid turning exploratory dependence transitions into clinical thresholds.
- Report reference-range violations and dataset applicability warnings.
- Create model cards describing intended population, endpoint, unsupported use, performance, and abstention.

### Deliverables

- Final explanation tables and figures.
- `docs/research/Model_Cards/`.
- `docs/research/Explainability_Limitations.md`.

### Exit gate

- Explanation additivity checks pass.
- Every interpretation is compatible with the endpoint and cohort.

## 16. Phase 11 — Reporting, bias assessment, and manuscript package

### Objective

Produce a complete conference manuscript and supplement that can survive methodological review.

### TRIPOD+AI work

- Complete all applicable checklist items and manuscript-page cross-references.
- Report participant flow, missing data, sample sizes, events, model specification, evaluation design, calibration, discrimination, fairness, open science, and limitations.
- Complete the abstract checklist separately.

### PROBAST+AI work

- Assess participants/data sources, predictors, outcome, and analysis domains.
- Record signaling-question evidence and judgments.
- Separate risk-of-bias judgment from applicability judgment.
- Disclose limitations rather than forcing a low-risk result.

### Claim-to-evidence work

- Link every abstract, results, discussion, and conclusion claim to a final table, figure, frozen artifact, or citation.
- Remove unsupported adjectives such as “superior,” “robust,” “clinical,” or “generalizable.”
- Use label-accurate wording: current diabetes-status/screening probability rather than future onset probability.

### Manuscript structure

- Introduction: practical missing-feature problem and evidence gap.
- Methods: datasets and endpoints, panels, nested/holdout designs, preprocessing, models, calibration, thresholds, router, abstention, metrics, comparisons, subgroups, and reproducibility.
- Results: participant/data flow, full-panel benchmarks, panel degradation, router comparisons, calibration, clinical utility, selective prediction, subgroup results, and negative findings.
- Discussion: principal findings, comparison with literature, practical interpretation, limitations, and future validation.
- Supplement: protocol, tuning spaces, full metrics, calibration plots, decision curves, subgroup tables, ablations, checklists, and model cards.

### Deliverables

- Conference manuscript.
- Supplementary appendix.
- TRIPOD+AI crosswalk.
- PROBAST+AI assessment.
- Claim-to-evidence table.
- Reproducibility package and archived code release.

### Exit gate

- `claim_evidence_table_complete`, `tripod_ai_checklist_complete`, and `probast_ai_assessment_complete` may become true.
- Publication-readiness gate has zero conference blockers.

## 17. Phase 12 — Independent reproducibility and submission

### Objective

Verify that the work can be reproduced and that the manuscript matches a suitable venue.

### Tasks

- Rebuild the environment from the lock/configuration on a clean machine or isolated environment.
- Reproduce representative development outputs and verify all final artifacts from saved predictions without retraining.
- Independently check table values against source CSV files.
- Inspect every manuscript and supplement page after rendering.
- Verify figure labels, accessibility descriptions, references, DOIs, table notes, and endpoint wording.
- Check code/data licenses and dataset citation requirements.
- Complete authorship, contribution, funding, conflict-of-interest, ethics/public-data, and data/code availability statements.
- Select a venue based on actual contribution and evidence, not only acceptance probability.
- Adapt length and formatting only after the scientific package is frozen.
- Prepare a reviewer-response evidence map in advance.

### Exit gate

- Another person or clean environment can verify the tables and artifact provenance.
- Submission files pass venue and internal quality checks.

## 18. Phase 13 — Journal extension

### Objective

Add transportability evidence rather than merely lengthening the conference paper.

### Preferred validation strategy

- Use a later BRFSS year as temporal validation if the endpoint and features can be harmonized without target leakage.
- Freeze the BRFSS model and preprocessing before applying it to the external year.
- Report distribution shift, missingness shift, prevalence shift, discrimination, calibration, net benefit, and subgroup performance.
- If recalibration is performed, report the original frozen model and recalibrated model separately.

### Additional journal-strength options

- External clinical cohort for PIDD-like measurements.
- Independent symptom-questionnaire cohort for Sylhet transportability.
- Hospital- or time-stratified external validation for readmission.
- Prospective or silent prospective evaluation if feasible.
- Decision-impact study only after predictive validity is established.

### Mixed-source fusion requirement

A true fused mixed-source model requires a matched cohort in which the same people have jointly observed clinical, symptom, and survey variables. Without that cohort, the mixed interface remains an abstaining orchestrator, not a validated fusion model.

### Age-of-onset requirement

Age of onset requires longitudinal event-time labels and censoring information. It should be implemented as a separate survival/time-to-event target only after suitable data are acquired and should not alter the frozen diabetes-status probability output.

### Exit gate

- `external_or_temporal_validation_complete` may become true only after frozen-model validation is documented.
- Journal claims are restricted to populations and settings supported by the validation evidence.

## 19. Readiness-blocker traceability

| Current blocker | Resolution phase | Required evidence |
|---|---:|---|
| BRFSS final profile | 8 | Full locked final BRFSS study |
| BRFSS profile locked | 7–8 | Signed freeze plus locked profile |
| BRFSS full sample | 8 | No sample limit in final metadata |
| BRFSS fresh test access | 3, 7–8 | Untouched final split and single locked evaluation |
| PIDD final profile | 8 | Full final repeated nested study |
| PIDD profile locked | 7–8 | Signed freeze and final metadata |
| Sylhet final profile | 8 | Full grouped final repeated nested study |
| Sylhet profile locked | 7–8 | Signed freeze and final metadata |
| Protocol frozen | 1, 7 | Signed statistical analysis plan and frozen config |
| Novelty review | 2 | Structured literature matrix and approved claim |
| Claim-evidence table | 9, 11 | Final claim crosswalk |
| TRIPOD+AI checklist | 11 | Completed checklist and manuscript crosswalk |
| PROBAST+AI assessment | 11 | Completed bias/applicability assessment |
| Ablation study | 5 | Prespecified ablation report on identical folds/budgets |
| Selective prediction | 6 | Risk-coverage and abstention analysis |
| Subgroup analysis | 6 | Supported subgroup metrics, calibration, and coverage |
| External/temporal validation warning | 13 | Frozen-model external or temporal validation |

## 20. Risk register and mitigations

| Risk | Consequence | Mitigation |
|---|---|---|
| Final computation is too expensive | Incomplete or rushed experiments | Benchmark development runtime, add resumability, verify disk capacity, and schedule datasets separately before lock |
| Router does not outperform fixed model | Primary superiority claim fails | Frame primary study around availability, calibration, degradation, and abstention; report switching as a negative result |
| Sylhet remains nearly perfect | Reviewers suspect leakage/optimism | Preserve duplicate grouping, show naive-versus-grouped sensitivity analysis, emphasize single-center symptom enrichment, and seek external validation |
| BRFSS threshold has low sensitivity | Poor screening usability | Use development-selected sensitivity-constrained threshold and decision-curve analysis; never optimize on final labels |
| Calibration is unstable | Percentages are unreliable | Prefer simpler calibration when selected by cross-fitted evidence, report slopes/intercepts and plots, and abstain from overclaiming |
| External data are not feature-compatible | Journal validation delayed | Pre-audit candidate datasets and define harmonization before model application |
| Subgroups are too small | Unstable fairness claims | Prespecify minimum counts, suppress unsupported estimates, and report coverage limitations |
| Public benchmark novelty is weak | Rejection despite good scores | Center the paper on availability-aware evaluation, proper probabilities, abstention, and rigorous leakage controls |
| Test contamination | Final estimates lose validity | Freeze first, create a fresh final split, restrict access, and keep immutable logs |
| Mixed-patient interface is misunderstood | Invalid fusion claim | Maintain explicit non-fusion wording, provenance, and default abstention |

## 21. Definition of done

### Conference-ready

The project is conference-ready only when:

- All 16 current blockers pass.
- PIDD, Sylhet, and BRFSS final studies are complete and locked.
- Ablation, selective-prediction, subgroup, calibration, and clinical-utility analyses are complete.
- The primary claim is supported or honestly revised.
- TRIPOD+AI, PROBAST+AI, and claim-to-evidence documents are complete.
- An independent reproducibility check passes.
- The manuscript never presents mixed-source routing as validated fusion or cross-sectional status as future onset.

### Journal-ready

Journal readiness additionally requires:

- External, temporal, or prospective validation appropriate to the claim.
- Transportability and prevalence-shift analysis.
- Stronger subgroup/fairness evidence where possible.
- A complete reproducibility/code/data package.
- Claims limited to settings supported by the external evidence.

## 22. Immediate execution queue

The next concrete work should occur in this exact sequence:

1. Create the baseline reproducibility record, blocker register, and decision log.
2. Draft the statistical analysis plan and endpoint/claim hierarchy.
3. Build the structured literature and novelty matrix.
4. Complete the final data/leakage/applicability audit, including BRFSS final-holdout and temporal-validation design.
5. Implement remaining engineering, baseline, ablation, selective-prediction, subgroup, and preflight support.
6. Run full development-profile studies and interpret them without touching a new final test set.
7. Review development evidence, finalize claims, and sign the protocol.
8. Lock and tag the exact final configuration.
9. Run final studies once.
10. Complete frozen analysis, reporting checklists, manuscript, reproducibility verification, and conference submission.
11. Add external/temporal validation for the journal extension.
