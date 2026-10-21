# Availability-Aware and Leakage-Controlled Evaluation of Predictive Models Across Heterogeneous Feature Schemas

**Case Studies in Diabetes Status and 30-Day Readmission**

Paper software and aggregate evidence prepared for **Discover Computing (Springer Nature)**, with research mentor **Dr. Sandhya Dubey**. The objective is to evaluate how prespecified feature availability, leakage controls, calibrated prediction and explicit abstention interact across heterogeneous dataset-native schemas.

**Local release candidate, pending approval.** The intended canonical URL is [OppositeExpert/T2DM](https://github.com/OppositeExpert/T2DM). The original research repository has not yet been renamed; this clean snapshot is not public. `v1.0.0-paper` is proposed, not created. No production Zenodo DOI is available. [Release and licensing status](publication_release/RELEASE_STATUS.md).

| Cohort | Prediction endpoint | Evaluation boundary |
| --- | --- | --- |
| PIDD | Recorded diabetes-positive label | Repeated nested internal validation |
| Sylhet | Early-stage diabetes-positive label | Repeated nested internal validation with identical-profile grouping |
| BRFSS 2015 | Self-reported diagnosed diabetes | Historical internal evaluation partition |
| Hospital130 | Readmission within 30 days | Patient-grouped internal evaluation; a separate readmission task |

The benchmark includes **Logistic Regression, Random Forest, XGBoost, LightGBM and CatBoost**. The four tree families are the routing candidates. No cohort probabilities are pooled. The work establishes internal evaluation only; it does not establish untouched independent final testing, external/prospective validity or clinical benefit.

**Negative switching result:** dynamic model-family switching did not demonstrate consistent Holm-corrected superiority over the robust fixed-family policy. Complete negative, mixed and nonsignificant results are retained. SHAP explains model associations, not causes.

## Evaluations represented

- **Masked-input experiments:** prespecified panels mask inputs to the original full-schema fitted models and training-derived calibration mappings; these are not independently trained smaller models.
- **Reduced-schema comparisons:** preprocessing, learners and calibration were separately refitted within the original training boundaries using only panel fields. Families and original full-schema hyperparameters remained fixed; no independent reduced-schema tuning was performed.
- **Calibration/switching ablation:** A/B use the robust fixed family, C/D panel-selected families; A/C use full-schema mappings and B/D panel mappings. Identity is an eligible map. Five-contrast ablation Holm families differ from the original three-policy families.
- **Runtime routing:** choose the largest supported dataset-native panel with all required fields observed. Unsupported inputs abstain. Availability abstention is distinct from confidence rejection among supported cases.
- **Selective prediction:** report both observation and positive-event coverage, excluded prevalence and accepted-case metrics. Better accepted-case scores do not establish better whole-population performance.
- **Repeat sensitivity:** retain each of five dependent repeats, their mean/sample SD, and the primary metrics computed after averaging probabilities per record. Repeat SD is descriptive, not a confidence interval.
- **Computational cost:** retain historical tuning/final-fit timers, successor component sums, warmed one-router inference distributions and serialized sizes. Saved estimator thread settings were retained; these were not universally single-thread benchmarks. Loading, explanations and cold starts were excluded from probability-only latency.

## Quick verification

Use CPython **3.12.x** from the snapshot root; the reference interpreter is 3.12.0. Install in a new environment:

```bash
python3.12 -m venv .venv-review
source .venv-review/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python scripts/verify_environment.py
```

Then verify the included evidence and run the portable suite:

```bash
python scripts/verify_publication_results.py
python publication_release/verify_public_aggregates.py
python publication_release/verify_manuscript_sources.py
python publication_release/verify_snapshot.py
python -m pytest -q -m "not local_research_data"
```

The public fingerprint scope is **85 unchanged retained publication artifacts plus 14 correction artifacts**. Sixteen metadata-bearing members of the original 101-file research export are intentionally excluded. The preserved original checksum index is historical provenance, not a claim that all 101 files are public. All inherited test files remain unchanged; added release tests assert this boundary.

## Reconstruct tables and figures

Use new, empty output directories:

```bash
python scripts/finalize_journal_handoff.py reconstruct --destination outputs/reviewer-tables
python publication_release/paper_evidence/REGENERATE_FIGURES.py outputs/reviewer-figures
```

These commands curate saved aggregates and draw the three paper figures. They do not fit models, rerun bootstrap samples, generate individual predictions or replace frozen results. The statistical-verification supplement has a separately named `07_STATISTICAL_VERIFICATION_PUBLIC.csv` derivative that removes its private source-path column; every retained cell string is unchanged.

The [complete paper source map](publication_release/RESULT_TO_SOURCE_MAP.md) maps **Main Tables 1–15, Figures 1–3 and Tables S1–S15** to exact public inputs, meanings and commands. The 1,988-cell paper ledger checker validates saved source strings and rounding. It does not independently verify every prose statement or PDF placement. [Actual candidate test results](publication_release/VERIFICATION_RESULTS.md) distinguish fresh measurements from earlier reference results.

## What is reproducible

| Pathway | Public inputs / limits |
| --- | --- |
| Table curation, figure drawing, scalar source/rounding checks | Included aggregates and source index; directly executable without patient records |
| Saved contrasts, Holm correction, repeat/routing/selective reconciliation | Included aggregates; verifies exported arithmetic, not raw bootstrap P values or prediction-derived uncertainty |
| Eligible cohort/event counts | Requires separately acquired public provider data and matching byte hashes; no split-membership reconstruction |
| Full prediction/model reanalysis | Not independently established from public inputs; private predictions/models/splits/bootstrap arrays are absent |
| Exact historical training replay | **BLOCKED:** original complete source fingerprint unavailable |
| Historical timing component reconstruction | **PARTIAL:** several original components were not separately timed |
| A4 computational-cost reporting | **COMPLETE:** retained aggregate reporting/methods; full measurement reconstruction requires private samples/objects |

No raw data, fitted model, preprocessing/calibration object, individual prediction/SHAP output, bootstrap array, private split membership, preservation archive or unreviewed third-party PDF is included. [Full limitations](publication_release/PUBLIC_RELEASE_LIMITATIONS.md).

## Data, environment and hardware

Acquire PIDD from the documented OpenML 37 preservation/reconstruction source, Sylhet from UCI 529, Hospital130 from UCI 296, and BRFSS 2015 from CDC. Exact source URLs, conversion contracts and hashes are in [config/data_sources.yaml](config/data_sources.yaml) and [data acquisition](docs/DATA_ACQUISITION.md). Data licenses remain separate from the software license. The previous independent download audit matched PIDD/Sylhet/Hospital130 hashes; BRFSS returned HTTP 403. No alternative BRFSS cohort is silently substituted.

The software lock was resolved on macOS arm64; native tree libraries may need platform runtimes elsewhere. Published cost measurements used Apple M2 Pro / 16 GB for the recorded local workload, not necessarily historical training hardware. A portable minimum RAM requirement, cross-platform timing parity and exact fitted-object byte identity have not been established. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md) for full commands and execution boundaries.

## License and citation

[LICENSE](LICENSE) contains standard MIT terms with the owner-requested attribution **Copyright (c) 2026 T2DM Project Contributors**. This local candidate remains subject to final publication approval and confirmation of any necessary contributor/institutional authority; no university approval is implied. The software license does not relicense provider datasets, manuscript material or third-party assets. Approved creator order/affiliations and final tag/commit/DOI will be recorded after verification; no DOI or creator consent is invented.
