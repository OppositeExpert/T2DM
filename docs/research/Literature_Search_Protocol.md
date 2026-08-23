# Literature Search and Novelty Review Protocol

**Version:** 0.1, 23 August 2026

**Status:** Search initiated; screening incomplete

## 1. Review questions

1. What has already been reported for PIDD, Sylhet, BRFSS diabetes status, and
   Hospital130 readmission, using comparable endpoints and validation designs?
2. Do prior studies evaluate probability calibration, clinical utility,
   uncertainty, subgroup performance, feature availability, and abstention?
3. What is the closest prior work on availability-aware routing or dynamic model
   selection under missing predictor panels?
4. Which methodological standards should govern the present evaluation?

## 2. Scope

The review includes model-development and evaluation studies using any of the
four configured datasets, plus methodological studies on:

- prediction with missing or unavailable predictor sets;
- model routing, gating, mixture-of-experts, and dynamic model selection;
- probability calibration and recalibration;
- selective prediction, reject options, abstention, and risk-coverage analysis;
- decision-curve analysis and net benefit;
- internal validation, repeated/nested cross-validation, and clustered data;
- fairness/subgroup evaluation in clinical prediction.

Non-clinical methodological papers may be included when they define a directly
applicable routing, calibration, or selective-prediction method. Reviews are used
for citation chasing but the novelty matrix prioritizes original studies and
authoritative reporting/risk-of-bias guidance.

## 3. Sources

Planned sources are PubMed/MEDLINE, Crossref, IEEE Xplore, ACM Digital Library,
Scopus or Web of Science if institutionally available, Google Scholar for forward
citation chasing, UCI/CDC source documentation, and reference lists of included
papers. Searches must record access date and exact query.

The 23 August 2026 seed search used web-indexed PubMed, PMC, BMJ, UCI, and journal
pages. It identified the initial records in `Literature_Matrix.md`; this is not
yet a complete or reproducible database search.

## 4. Query blocks

Queries will combine one term block from each applicable row:

| Concept | Search terms |
|---|---|
| Dataset | `Pima Indians Diabetes`, `PIDD`, `early stage diabetes`, `Sylhet`, `BRFSS diabetes`, `Diabetes 130-US Hospitals`, `Hospital130` |
| Prediction | `prediction model`, `machine learning`, `risk model`, `classification`, `screening`, `readmission` |
| Availability | `missing predictor`, `feature availability`, `feature subset`, `dynamic routing`, `model selection`, `mixture of experts` |
| Reliability | `calibration`, `Brier`, `log loss`, `decision curve`, `net benefit`, `selective prediction`, `abstention`, `risk coverage` |
| Validity | `external validation`, `nested cross-validation`, `bootstrap`, `subgroup`, `fairness`, `duplicate`, `grouped split` |

Example PubMed-compatible query:

`("Pima Indians Diabetes" OR Sylhet OR (BRFSS AND diabetes)) AND (prediction OR machine learning) AND (calibration OR "decision curve" OR abstention OR "feature availability")`

Dedicated searches are required because one combined query will miss benchmark
papers that report only accuracy/AUC and methodological papers without diabetes
terms.

## 5. Eligibility

Include a record when it:

- evaluates a prediction model on a configured dataset or presents a method
  directly relevant to the proposed contribution;
- provides enough methods/results detail to extract its endpoint, sample, split,
  models, and at least one performance measure;
- is an original peer-reviewed study, dataset paper, official dataset document,
  or authoritative reporting/risk-of-bias statement.

Exclude or separate:

- papers with a materially different outcome that cannot inform the endpoint;
- tutorials, blogs, student reports, and unreviewed claims from the evidence base;
- duplicate publications of the same experiment, retaining the most complete;
- papers whose full methods cannot be recovered after documented attempts.

Preprints may be tracked as emerging competition but cannot alone establish the
clinical or methodological justification for a frozen decision.

## 6. Screening and extraction

Each record progresses through `identified`, `title/abstract included`,
`full-text included`, or `excluded with reason`. For included studies extract:

- DOI/PMID/URL and publication status;
- cohort, country/setting, endpoint, sample size, events, prevalence;
- predictor count and missing-data handling;
- train/tune/evaluation split and grouping;
- leakage controls and whether sampling occurred before or after splitting;
- algorithms, hyperparameter tuning, feature selection, and calibration;
- AUROC, AP/PR-AUC, Brier/log loss, calibration, threshold metrics, net benefit;
- interval/resampling method and multiplicity control;
- external/temporal validation;
- subgroup/fairness analysis, applicability, code/data access;
- feature-availability/routing/abstention contribution;
- limitations and direct relevance to the proposed claim.

Accuracy values are never compared without verifying endpoint, prevalence,
sampling, duplicate handling, and evaluation design.

## 7. Novelty decision rule

The primary novelty statement survives only if no close prior study jointly
provides all of the following on comparable diabetes-screening environments:

1. prespecified clinically meaningful feature-availability panels;
2. fold-safe tuning and calibration;
3. explicit performance-degradation estimation with uncertainty;
4. evaluated abstention/selective prediction;
5. endpoint-safe routing and provenance;
6. proper probability and clinical-utility evaluation rather than accuracy alone.

If a close prior study exists, the contribution must be narrowed to the element
that is demonstrably new or the project must add a stronger comparison. Dynamic
model switching is not treated as novel merely because different algorithms are
available.

## 8. Completion gate

- [ ] All query strings and search dates are recorded.
- [ ] At least two scholarly databases plus citation chasing are complete.
- [ ] Dataset-specific and methodological searches are both complete.
- [ ] Full-text extraction is complete for all closest studies.
- [ ] Endpoint and evaluation-design mismatches are documented.
- [ ] One primary and no more than three secondary contribution statements exist.
- [ ] A negative-claim statement is written.
- [ ] Numerical margins and threshold ranges in the SAP are reviewed against evidence.
- [ ] A second reviewer or supervisor resolves the closest-work and novelty decision.
- [ ] `novelty_review_complete` remains false until this gate is signed.
