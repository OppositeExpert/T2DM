# Definitive Technical Project Context: T2DM Prediction and Availability-Aware Evaluation

**Repository audited:** `OppositeExpert/T2DM`, local checkout at `/Users/pranavprabhu/Codex/Minor Proj/T2DM`  
**Workspace audited:** 30 August 2026; current working tree based on `main`/`origin/main` commit `99ff8fa` (`Add reproducible final-run safeguards`, 29 August 2026)

**Revision warning:** the current workspace contains intentional uncommitted Hospital130, registry, release, documentation, CI, and conference-package changes. No single Git commit captures the complete state described here; `99ff8fa` is the base revision, not the whole audited implementation.
**Document purpose:** technical source of truth and context transfer, not a polished dissertation, clinical protocol, or claim of final validation  
**Evidence rule used here:** final code and configuration outrank generated development documents; current-code artifacts outrank older artifacts; historical reports explain evolution but do not override the final implementation.

## Evidence notation and evidence tiers

Paths are relative to the T2DM repository unless an absolute path is explicitly shown. A claim such as `src/diabetes_pipeline/runner.py -> run_benchmark()` identifies both the evidence file and relevant implementation entry. Generated study artifacts live locally under `outputs/publication_pipeline/`, but most are Git-ignored; this matters for reproducibility and is discussed repeatedly below.

The project uses four evidence tiers that must not be conflated:

1. **Smoke:** a small, deliberately under-powered execution check. It proves the path runs, not scientific performance.
2. **Development pilot:** full workflow but reduced tuning/repetition/bootstrap budget.
3. **Full development:** the complete configured development budget for PIDD, Sylhet, BRFSS, and the separate Hospital130 readmission study. These analyses are still unlocked, their outcomes have been inspected, and they are not final paper evidence.
4. **Final locked:** would require a frozen protocol and authorized concealed final manifests. No such study exists. `config/publication_protocol.yaml` has `protocol_frozen: false` and `final_execution_authorized: false`.

The current machine state has extensive ignored outputs. A clean GitHub clone does not.

# 1. EXECUTIVE PROJECT OVERVIEW

This project is a research-grade prototype for evaluating calibrated machine-learning predictions under heterogeneous diabetes-related datasets and incomplete feature availability. It trains separate cohort- and endpoint-specific models, measures discrimination, probability accuracy, calibration, threshold-dependent classification and clinical utility, generates held-out SHAP explanations, evaluates prespecified reduced-feature panels, abstains when no validated panel is supported, and produces provenance-rich research patient reports. PIDD, Sylhet and BRFSS are three related but non-interchangeable diabetes-screening/status tasks; Hospital130 is a separate 30-day readmission task among people already involved in diabetes care. The system does **not** merge these cohorts, diagnose a real patient, predict age of onset, or establish external clinical validity.

## Exact problem and final research question

The engineering problem is: given datasets with different endpoints, populations, measurement scales and feature sets, how can one build a leakage-controlled experiment and inference prototype that (a) preserves each dataset's semantics, (b) produces calibrated probabilities and uncertainty-aware comparisons, (c) measures how performance degrades when only a prespecified subset of features is present, and (d) abstains rather than fabricating unsupported interoperability?

The strongest final research question is:

> Across heterogeneous diabetes-screening cohorts, how do discrimination, calibration and clinical-utility estimates degrade under prespecified feature-availability environments, and can a provenance-preserving router provide evaluated fallback predictions or abstain safely without claiming that incompatible cohorts are interchangeable?

This formulation follows the final claim control in `config/publication_protocol.yaml`, `docs/progress_reports/BLOCK_K_RESEARCH_GRADE_AUDIT.md`, and `conference_package/Conference_Manuscript_Development_Draft.md`. Dynamic algorithm switching is a secondary negative result, not the headline.

## Motivation and evolution of the idea

The original work was closer to a conventional comparison centred on XGBoost and several diabetes datasets. The legacy project trained XGBoost separately and reported headline classification metrics. It exposed three deeper problems:

- the datasets did not share one endpoint or schema;
- complete-case processing and ordinary row splitting could discard data or leak duplicate profiles;
- a leaderboard did not address calibration, missing measurements, provenance, or safe patient-facing interpretation.

The final project therefore evolved from “which classifier scores best?” to “what evidence can be produced safely when endpoints, cohorts and available measurements differ?” The active package is `src/diabetes_pipeline`; the old implementation is retained outside the authoritative repository as `XGBoost_Legacy_Backup_2026-08-20` and is historical only.

## Final scope

The implemented scope combines:

- **multi-dataset ML**, but with separate dataset-specific models rather than pooled training;
- **robustness/applicability evaluation**, especially panel masking, missingness stress, selective prediction and subgroup reporting;
- **explainable AI**, using held-out SHAP with reconstruction and stability checks;
- **availability-aware prediction**, selecting the largest pre-evaluated panel and a development-selected model for that panel;
- **research decision-support prototyping**, including calibrated probabilities, thresholds, provenance, warnings and abstention;
- **research governance**, including outcome concealment, final-run authorization, participant-level inference, multiplicity correction and publication-readiness checks.

It explicitly does not provide clinical diagnosis, treatment advice, prospective validation, causal explanations, a universal diabetes model, cross-cohort probability fusion, onset-age prediction, a production API/UI, or regulatory-grade software. Hospital130 is not a diabetes-detection dataset.

## Why this is more than “train XGBoost on diabetes data”

XGBoost is only one of five model families and is not universally best. The substantive work is the surrounding experimental system: dataset contracts, cohort audits, group-aware nested CV, holdout concealment, fold-fitted preprocessing, Optuna tuning, cross-fitted calibrator selection, development-only threshold selection, participant/cluster bootstrap inference, paired Holm-corrected comparisons, decision curves, feature ontology, panel-specific masking, routing, abstention, SHAP scale controls, patient reporting, ablations, selective prediction, missingness stress, subgroup analysis, reproducibility metadata and a fail-closed publication gate. Evidence: `src/diabetes_pipeline/`, `config/`, 107 passing tests plus seven subtests, and the development conference package.

# 2. PROJECT EVOLUTION — FROM INITIAL EXPERIMENT TO FINAL SYSTEM

## Pre-Block legacy baseline

The historical `XGBoost_Legacy_Backup_2026-08-20` contains the earlier XGBoost-oriented work. It used a different BRFSS definition (combined diabetes/prediabetes, complete-case cohort of 251,702) and simpler evaluations. Historical values such as PIDD AUROC 0.8198, Sylhet 0.9949, BRFSS 0.8212 and Hospital130 0.684 are **not comparable** with final-pipeline studies because endpoints, cohorts, preprocessing, splitting and model banks changed. The active repository deliberately excludes the legacy package.

## Block A — publication pipeline foundation

**Problem discovered:** the datasets required explicit endpoint, grouping, missingness and split contracts before trustworthy modelling.  
**Implemented:** dataset registry, validators, audits, deterministic manifests, leakage barriers and an isolated package/environment. Principal evidence: `config/datasets.yaml`; `src/diabetes_pipeline/data/loaders.py`; `data/manifests.py`; `splitting/strategies.py`; `splitting/registry.py`; `docs/progress_reports/BLOCK_A_REPORT.md`.  
**Experiment/result:** audited 429,360 BRFSS, 768 PIDD, 520 Sylhet and 99,343 Hospital130 retained records. PIDD zero sentinels were deferred to fold imputation; 251 Sylhet profile groups were created; Hospital patients were grouped; BRFSS retained predictor missingness.  
**Learning:** the legacy BRFSS complete-case/combined endpoint was unsuitable as the primary cohort. Dataset identity had to survive until split construction.  
**Survival:** fully active. The original Block A report still says the legacy `src/` coexisted, but the final T2DM repository now contains only `src/diabetes_pipeline`.

## Block B — PIDD smoke path

There is no standalone `BLOCK_B_REPORT.md`; its existence is inferred only from later reports and retained smoke study directories such as `outputs/publication_pipeline/studies/pidd_smoke_*`. The smoke path verified that model adapters, nested-fold control, calibration, thresholding and artifact writing executed. It was superseded by Block C and must not be treated as a scientific result.

## Block C — PIDD development pilot

**Before:** the foundation could audit and split data but lacked an end-to-end, multi-model probability evaluation.  
**Implemented:** five-model outer evaluation, Optuna inner tuning on average precision, cross-fitted calibrator selection, three threshold policies, bootstrap intervals, paired comparisons, model bundles and reload verification. Evidence: `runner.py`; `training/tuning.py`; `calibration/calibrators.py`; `calibration/thresholds.py`; `evaluation/metrics.py`; `docs/progress_reports/BLOCK_C_PIDD_DEVELOPMENT_PILOT_REPORT.md`.  
**Pilot:** `pidd_development_pilot_27b9bc88b493`, one 5-fold repeat, five Optuna trials and 200 bootstraps. Pooled AUROC was about 0.835–0.839 across models; no model difference survived Holm correction. CatBoost had pilot Brier 0.1540; XGBoost AP 0.7158.  
**Learning:** Logistic Regression remained competitive; the contribution could not credibly be “boosting wins.” Threshold policy changed sensitivity materially.  
**Later change:** the final development study `pidd_development_072cd2104089` uses five repeats, 30 trials and 500 bootstraps. Participant-aggregated inference replaced naïve pooling/fold means as the primary repeated-CV estimand.

## Block D — held-out PIDD SHAP

**Problem:** a probability table did not explain model behaviour or explanation stability.  
**Implemented:** explanations from each outer fold's saved preprocessor/model, original-feature grouping, local top contributors, dependence summaries, plots, reconstruction tests and between-fold stability. Evidence: `explainability/shap_analysis.py`; `explainability/stability.py`; `explainability/plots.py`; `BLOCK_D_PIDD_SHAP_REPORT.md`.  
**Result:** Glucose and BMI ranked first and second for all five PIDD model families. Raw SHAP scales differ by family, so magnitudes were not compared across models.  
**Learning:** missing-Insulin indicators could themselves influence estimates, motivating availability experiments.  
**Survival:** active and extended to grouped Sylhet and holdout studies. Final code produces bar/beeswarm/dependence artifacts; final code does not produce waterfall or force plots.

## Block E — grouped Sylhet pilot

**Problem:** 269 of 520 rows repeat an identical feature profile. Row-wise validation would put the same predictor vector on both sides.  
**Implemented:** repeated stratified-group outer and inner CV using a deterministic profile hash; calibration eligibility protection; held-out SHAP. Evidence: `loaders.py -> load_sylhet()`; `splitting/strategies.py`; `training/tuning.py`; `BLOCK_E_SYLHET_GROUPED_PILOT_REPORT.md`.  
**Pilot result:** CatBoost pooled AUROC 0.9722, AP 0.9841, Brier 0.0642; differences were not Holm-significant. An earlier unconstrained isotonic experiment on roughly 416 calibration rows created extreme probabilities and poor log loss; the final rule makes isotonic ineligible below 1,000 calibration samples.  
**Learning:** group isolation and sample-size-aware calibration safeguards materially affect credibility.  
**Later change:** full five-repeat development study `sylhet_development_b52477910fe6`; a formal invalid naïve-split demonstration quantified leakage inflation.

## Block F — PIDD availability routing

**Problem:** real inputs may omit insulin, skinfold or other fields; global imputation of any arbitrary patient schema would silently extrapolate beyond evaluated conditions.  
**Implemented:** six prespecified PIDD panels, full-model masking, development-only model selection by Brier/log loss/AP, an availability router, robust-fixed comparator, abstention and paired routing evaluation. Evidence: `config/availability_scenarios.yaml`; `routing/evaluator.py`; `routing/inference.py`; `BLOCK_F_PIDD_AVAILABILITY_ROUTING_REPORT.md`.  
**Result:** performance degraded as information was removed, but dynamic switching did not show a multiplicity-corrected advantage over a robust fixed model.  
**Learning:** the defensible contribution is quantified degradation and safe applicability, not an algorithm-selection win.  
**Survival:** active and extended to all four datasets.

## Block G — patient research result

**Problem:** routing and SHAP tables were not a coherent single-input output.  
**Implemented:** schema validation, range checks, routing through multiple outer bundles, probability aggregation, threshold agreement, normalized cross-fold local explanations, cohort context, provenance, disclaimers and abstention. Evidence: `reporting/patient_results.py`; `examples/pidd_patient_synthetic.json`; `BLOCK_G_PATIENT_RESULT_REPORT.md`.  
**Synthetic demonstration:** missing Insulin selected `no_insulin_or_skinfold`; mean calibrated probability 0.6605, range 0.5954–0.7838, 5/5 folds above 0.5. This is an old pilot integration result, not a real patient or confidence interval.  
**Survival:** active research-report component; it does not save personal input by default.

## Block H — development-locked holdout engine

**Problem:** large BRFSS and Hospital130 cohorts needed a different design from repeated small-cohort CV and stricter separation of development choices from test access.  
**Implemented:** deterministic 80/20 holdout, patient-grouping for Hospital130, development CV for tuning/calibration/threshold/champion choice, delayed test loading, individual/cluster bootstrap and lock enforcement. Evidence: `holdout_runner.py`; `splitting/concealment.py`; `evaluation/bootstrap.py`; `BLOCK_H_HOLDOUT_ENGINE_REPORT.md`.  
**Initial smoke results:** BRFSS and Hospital130 10,000-row test samples verified execution. Hospital130 XGBoost AUROC 0.6589/AP 0.2065; the 0.5 threshold predicted almost no positives.  
**Later BRFSS completion:** the entire 429,360-row cohort was run under the `development` profile as `brfss_development_holdout_56407ef53bba`, with 343,488 development and 85,872 development-test rows, five model families, full routing, survey sensitivity, SHAP, selective prediction, subgroup analysis and artifact ablations. Because the seed-42 test outcomes were already known and the protocol was not frozen, this is full development evidence, not a final locked test.  
**Learning:** probability quality and operating threshold are separate. Any inspected development/smoke test remains permanently development-only even when the full cohort is used.  
**Survival:** active; final authorization remains disabled.

## Block I — feature and endpoint ontology

**Problem:** similarly named columns were being mistaken for interchangeable measurements, and Hospital readmission risk could be confused with diabetes status.  
**Implemented:** endpoint contracts, 19 explicit shared/related mapping rows, 72 dataset-specific mappings, harmonization policies and a generated 91-row dictionary. Evidence: `config/feature_ontology.yaml`; `features/ontology.py`; `BLOCK_I_FEATURE_ONTOLOGY_REPORT.md`.  
**Learning:** ontology is primarily a semantic safety/audit layer. It does not automatically convert a patient record between datasets.  
**Survival:** active configuration and generator.

## Block J — multi-dataset and mixed-attribute routing

**Problem:** a single JSON request can contain namespaced fields compatible with more than one screening cohort, but those cohort probabilities cannot be averaged.  
**Implemented:** routers for all datasets, namespaced mixed input, endpoint isolation, one-expert selection, audit of unused fields and a reserved `onset_age: not_implemented` output. Evidence: `reporting/mixed_patient_results.py`; `BLOCK_J_MULTI_DATASET_ROUTING_REPORT.md`.  
**Later safety change:** the original transparent priority heuristic became explicitly experimental. Final default behaviour abstains when multiple screening environments qualify unless `preferred_dataset` is supplied. This final behaviour is tested and documented by Block K.

## Block K — research-grade audit and claim control

**Problem:** working software and attractive metrics were being mistaken for submission-ready evidence.  
**Implemented:** evidence tiers, fail-closed mixed-environment behaviour, publication readiness checks, claim scoping, TRIPOD+AI/PROBAST+AI placeholders and a narrowed negative-result-aware thesis. Evidence: `reporting/publication_readiness.py`; `config/publication_protocol.yaml`; `BLOCK_K_RESEARCH_GRADE_AUDIT.md`.  
**Result:** NOT READY, initially because pilots/smoke and scientific work remained. Later work completed all supported machine-executable development analyses, the full BRFSS and Hospital130 development runs, and the conference development package, but human review/freeze/final execution remain pending. The current registry-driven conference-package audit reports 15 blockers and one warning; `PUBLICATION_READINESS.md` is the canonical root pointer to that audit.
**Survival:** central final governance layer.

## Post-Block K publication-development completion

Work after the base revision adds the full BRFSS development execution, held-out BRFSS SHAP, survey-weighted sensitivity, routing and matched panels, artifact ablations, selective prediction, subgroup analysis, exact environment/data acquisition, an authoritative-study registry, CI, bundle-reload verification, and a substantially stronger final-run authorization contract. `docs/research/Execution_Status.md` (29 August) supersedes Block K's statement that these development analyses were incomplete: supported code paths and development runs are complete, but completion flags intentionally remain false pending scientific/human review.

## Compact timeline

`Legacy XGBoost comparisons` → incompatible endpoints and fragile preprocessing recognized → `Block A contracts/audits/splits` → multi-model PIDD smoke/pilot → no clear model winner → held-out SHAP → missingness indicators motivate availability work → Sylhet duplicate leakage recognized and grouped → panel masking/router with negative switching result → patient research formatter → protected holdout engine for BRFSS/Hospital130 → ontology prevents false harmonization → namespaced mixed routing → fail-closed claim control → full PIDD/Sylhet development studies and ablations → development conference package → full BRFSS development, survey/routing/SHAP/secondary analyses → reproducibility and final-run hardening → **final protocol/final study still not authorized**.

# 3. FINAL GITHUB IMPLEMENTATION AUDIT

## Authoritative executable system

The only active Python package is `src/diabetes_pipeline`. The installed console script is `diabetes-pipeline = diabetes_pipeline.cli:main` in `pyproject.toml`; equivalently use `python -m diabetes_pipeline.cli`. `cli.py -> build_parser()` exposes audit, splitting, research audit, concealment test, ontology export, nested benchmark, holdout benchmark, survey sensitivity, SHAP, routing, matched-panel contrasts, artifact/retraining ablations, selective prediction, subgroups, stress tests, leakage demonstrations, patient result, mixed result and publication-readiness commands.

There are no Jupyter notebooks in the final repository. All final execution is Python/config driven. The natural read order is `README.md` → `config/datasets.yaml` → `config/availability_scenarios.yaml` → `config/feature_ontology.yaml` → `docs/RUNBOOK.md` → `runner.py`/`holdout_runner.py` → routing/reporting modules → local study artifacts if available.

## Repository and Git state at audit

- Remote: `git@github.com:OppositeExpert/T2DM.git`.
- Branch: `main`; local `HEAD` and `origin/main` both resolve to `9b15b26b2ed6229353de2ced44022aa22eeaf902`.
- Thirteen commits from baseline `750bcff` to the tracked development-package commit.
- The current workspace is intentionally not clean: 55 tracked paths are modified and 24 paths are untracked. Those changes belong to the post-commit development/reproducibility checkpoint and are part of this audit; they have not been committed or pushed.
- The current active source-tree SHA-256 reported by `settings.source_tree_sha256()` is `d8cd9f406ac37539b604daa74d587604780b03a8008781a21cea94592a596177`.
- `data/raw/`, most of `outputs/`, `.venv-pipeline/` and caches are ignored by `.gitignore`.

The repository's Git history begins after Blocks A–K functionality largely existed. The first commit is a consolidated baseline, so commit history cannot reconstruct every early edit; the Block reports are needed for that history.

## Reproducibility verdict

**Locally reproducible and substantially clean-clone reproducible for development studies, but exact historical evidence remains outside Git and final scientific execution remains authorization-gated.**

What works:

- The reference interpreter is CPython 3.12.0. `requirements.lock` fixes 48 resolved distributions for the audited macOS-arm64 environment; `pyproject.toml` also pins the direct project dependencies.
- Seed 42 is standard; derived fold/model seeds are deterministic. Split manifests and source/data hashes are recorded.
- The current local environment passes `107 passed, 3 warnings, 7 subtests passed`; the warnings are third-party SHAP/Matplotlib `PendingDeprecationWarning`s.
- `scripts/verify_environment.py` verifies Python 3.12.0 and all 48 locked distributions.
- `scripts/acquire_data.py --dataset all` verifies all four exact raw files; with `--download` it can reconstruct/acquire them from the recorded OpenML, UCI and CDC sources and refuses silent hash mismatches.
- `scripts/verify_holdout_bundles.py` reproduced all five BRFSS holdout bundles' raw and calibrated probabilities for all 85,872 development-test rows, with maximum absolute error at or below `3.33e-16`.
- `.github/workflows/ci.yml` adds automated install, environment, config and test verification.

What a clean clone still lacks:

- the raw datasets until `scripts/acquire_data.py --download` is run and the exact hashes are verified;
- almost all `outputs/publication_pipeline/studies/**`, including predictions, metrics, SHAP tables and joblib model/router bundles;
- a cross-platform/container guarantee of byte-identical fitted models;
- a committed final locked study, because none exists.

Therefore the code, acquisition contracts, lightweight evidence registry and generated conference documents can be carried by Git, but the large numerical evidence cannot simply be inspected after clone: it must be regenerated from exact verified data or restored from a separately preserved artifact store. `config/authoritative_studies.yaml` and `evidence/study_registry.json` identify the authoritative local studies and checksums but do not replace them.

## Seeds, determinism and machine assumptions

`settings.py` derives `PROJECT_ROOT` from the installed source, so active code does not require an absolute user path. One research baseline document and ignored `experiment_metadata.json` files preserve old `/Users/pranavprabhu/.../XGBoost` paths; these are provenance remnants, not runtime requirements. `scripts/render_docx_with_word.scpt` assumes macOS Microsoft Word for one document-rendering path. Model libraries are seeded and LightGBM uses deterministic/column-wise options, but byte-identical training across CPU architectures or library builds is not guaranteed, especially for multithreaded boosting.

No credential, password or API-secret pattern was found in tracked source/config/docs. CI, a resolved lockfile, data acquisition instructions and data-use notes now exist. No repository-level software license has been approved, and there is no container or immutable external artifact archive.

## Active, supporting, generated and historical material

- **Active:** `src/diabetes_pipeline/**`, `config/**`, `tests/**`, `pyproject.toml`.
- **Supporting:** `scripts/build_*`, `scripts/acquire_data.py`, environment/bundle/preflight verifiers, `examples/**`, `docs/RUNBOOK.md`, research methods documents.
- **Generated but tracked:** conference development drafts, figures/tables and package manifest.
- **Generated but ignored:** raw data, studies, models, predictions, most metrics and SHAP artifacts.
- **Historical/superseded:** pilot progress reports and older audit files remain useful as history; top-level audit Markdown files can be stale. The legacy XGBoost tree is outside T2DM.
- **No notebooks:** none constitute the final pipeline.

## README accuracy

The current README correctly lists all five benchmark families, endpoint isolation, non-fusion, authoritative study IDs, reproducibility/data-acquisition documents, ignored large artifacts and final-run lockout. `docs/PROJECT_STRUCTURE.md` and `docs/RUNBOOK.md` now use the T2DM root. The main remaining caveat is state provenance: these corrections are in the uncommitted working tree, so the base GitHub revision `9b15b26` does not yet contain the full audited documentation and hardening.

# 4. DATASETS

The final registry contains exactly four datasets. None is an external validation cohort for another dataset. Dataset evidence: `config/datasets.yaml`; `data/loaders.py`; current hashed audits under `outputs/publication_pipeline/manifests/audits/`; `docs/research/Data_and_Split_Leakage_Audit.md`.

## 4.1 Pima Indians Diabetes Database (PIDD)

**Identity and role.** Local `data/raw/pidd.csv`; `config/data_sources.yaml` records OpenML dataset 37 as the verified reconstruction source because the historical UCI raw-file URL returned 404 when rechecked. The headerless raw file has 9 columns: eight predictors plus `Outcome`. It contains 768 rows: 500 negative and 268 positive, prevalence 34.90%. Endpoint is the dataset's binary diabetes-positive label. It is used for small-cohort repeated nested development, SHAP, routing, patient demonstration and all major ablations. The source manifest establishes byte provenance, not a clearer original license; code and data licenses remain separate.

| Feature | Meaning/type/unit | Observed nonmissing range and quality | Preprocessing | Ontology |
|---|---|---|---|---|
| Pregnancies | numeric count | 0–17; zero is valid | fold median/indicator machinery, though no sentinel conversion | dataset-specific |
| Glucose | plasma glucose concentration, numeric | 44–199 after five zero sentinels become missing | zero→NaN before split; fold median + indicator | `glycemia`, direct |
| BloodPressure | diastolic pressure, mmHg | 24–122 after 35 zeros become missing | zero→NaN; fold imputation | `blood_pressure`, direct; not interchangeable with HighBP |
| SkinThickness | triceps skinfold, commonly mm | 7–99 after 227 zeros become missing | zero→NaN; fold imputation | dataset-specific |
| Insulin | 2-hour serum insulin measurement | 14–846 after 374 zeros become missing | zero→NaN; fold imputation | `insulin`, direct lab measurement |
| BMI | body mass index, kg/m² | 18.2–67.1 after 11 zeros become missing | zero→NaN; fold imputation | `body_mass_index`, direct |
| DiabetesPedigreeFunction | unitless pedigree score | 0.078–2.420 | fold numeric pipeline | dataset-specific; the ontology does not create a universal family-history field |
| Age | years | 21–81 | fold numeric pipeline | `age`, direct |

PIDD has no exact duplicate rows in the current audit. Its main problems are small size, population specificity, substantial lab missingness encoded as impossible zeros, outliers that are retained rather than clipped, and no protected external cohort. The zero conversion is deterministic and outcome-blind; learned medians are fit only inside training partitions.

## 4.2 Sylhet Early Stage Diabetes Risk Prediction dataset

**Identity and role.** UCI source is recorded in `datasets.yaml`; local `data/raw/sylhet.csv`. Raw/analysis table has 17 columns: 16 inputs and target `class`. There are 520 rows, 320 positive and 200 negative, prevalence 61.54%. It is a small symptom-questionnaire cohort used for grouped repeated nested development, SHAP, routing and ablations.

`Age` is numeric years, observed 16–90. `Gender` is mapped Male=1, Female=0. The other fourteen fields are binary Yes=1/No=0: `Polyuria`, `Polydipsia`, `sudden weight loss`, `weakness`, `Polyphagia`, `Genital thrush`, `visual blurring`, `Itching`, `Irritability`, `delayed healing`, `partial paresis`, `muscle stiffness`, `Alopecia`, and `Obesity`. All are configured as numeric after deterministic mapping; none is missing. Only Age, Gender and Obesity have explicit shared/related ontology mappings (`age`, `sex_gender`, and BMI proxy). The symptom fields remain dataset-specific.

The critical quality issue is duplication: 251 unique feature-profile groups and 269 repeated rows, largest group 16. Identical profiles are hashed to a group before splitting, and both outer and inner CV isolate the group. These are not assumed to be the same person; grouping prevents the same predictor vector appearing on both sides. The high positive prevalence and symptom-enriched clinical sampling mean high AP/AUROC does not imply population screening performance.

## 4.3 Behavioral Risk Factor Surveillance System 2015 (BRFSS)

**Identity and role.** CDC BRFSS 2015 codebook URL in config; local `data/raw/brfss.csv`. The source file has 441,456 rows and 330 raw survey columns. The current loader retains 429,360 target-valid records and emits 21 predictors plus target. There are 57,256 positives and 372,104 negatives, prevalence 13.34% unweighted. Raw `DIABETE3` code 1 is positive, code 3 negative; codes 2, 4, 7 and 9 are excluded. The endpoint is cross-sectional self-reported diagnosed diabetes, not incidence or laboratory diagnosis.

All configured analysis inputs are numeric-coded. Binary indicators are 0/1 after documented recoding: `HighBP`, `HighChol`, `CholCheck`, `Smoker`, `Stroke`, `HeartDiseaseorAttack`, `PhysActivity`, `Fruits`, `Veggies`, `HvyAlcoholConsump`, `AnyHealthcare`, `NoDocbcCost`, `DiffWalk`, and `Sex` (male=1, female=0). `BMI` is kg/m², observed 12.02–99.95. `GenHlth` is ordered 1–5; `MentHlth` and `PhysHlth` are unhealthy-day counts 0–30; `Age` is an ordered 1–13 five-year age-group code; `Education` is 1–6; `Income` is 1–8. `HeartDiseaseorAttack` is a derived heart-disease/MI composite.

Missing counts after loading are: HighBP 1,227; HighChol 61,201; CholCheck 14,859; BMI 35,155; Smoker 17,055; Stroke 1,102; HeartDiseaseorAttack 3,618; PhysActivity 37,073; Fruits 42,573; Veggies 49,754; HvyAlcoholConsump 25,035; AnyHealthcare 1,776; NoDocbcCost 1,140; GenHlth 1,192; MentHlth 7,082; PhysHlth 9,368; DiffWalk 14,177; Sex 0; Age 5,128; Education 1,731; Income 77,130. These are retained and fold-imputed, rather than complete-case deleted.

The current research audit counts 8,695 repeated analysis rows, but does not group them because repeated survey response profiles do not establish identity. Survey variables `_LLCPWT`, `_STSTR`, and `_PSU` are retained for a separate survey-weighted sensitivity analysis, not model fitting. In the 85,872-row development-test partition, unweighted prevalence is 13.3350% and survey-weighted prevalence is 10.9466%; the Kish effective sample size is about 21,165.5. BRFSS now has a full-cohort **development** holdout study, survey sensitivity, SHAP, routing, selective prediction, subgroup analysis and artifact ablations. It still has no authorized final locked or external-validation study.

## 4.4 Diabetes 130-US Hospitals for Years 1999–2008 (Hospital130)

**Identity and role.** UCI source in config; local `data/raw/hospital130.csv`. The raw table has 101,766 encounters and 50 columns. The loader excludes discharge disposition IDs 11, 13, 14, 19, 20 and 21 (death/hospice), leaving 99,343 encounters from 69,990 patients. Target `readmitted_binary` is 1 for raw `<30` and 0 for `>30` or `NO`: 11,314 positive, 88,029 negative, prevalence 11.39%. This is **30-day readmission**, not diabetes prediction.

The nine numeric inputs are: `age` (10-year bracket converted to ordered 0–9), `time_in_hospital` (1–14 days), `num_lab_procedures` (1–132), `num_procedures` (0–6), `num_medications` (1–81), `number_outpatient` (0–42), `number_emergency` (0–76), `number_inpatient` (0–21), and `number_diagnoses` (1–16).

The 37 categorical inputs are:

- encounter context: `admission_type_id`, `discharge_disposition_id`, `admission_source_id`, `race`, `gender`, `payer_code`, `medical_specialty`;
- diagnoses/tests: `diag_1`, `diag_2`, `diag_3`, `max_glu_serum`, `A1Cresult`;
- medications: `metformin`, `repaglinide`, `nateglinide`, `chlorpropamide`, `glimepiride`, `acetohexamide`, `glipizide`, `glyburide`, `tolbutamide`, `pioglitazone`, `rosiglitazone`, `acarbose`, `miglitol`, `troglitazone`, `tolazamide`, `examide`, `citoglipton`, `insulin`, `glyburide-metformin`, `glipizide-metformin`, `glimepiride-pioglitazone`, `metformin-rosiglitazone`, `metformin-pioglitazone`;
- treatment flags: `change`, `diabetesMed`.

Medication values are source categories such as `No`, `Steady`, `Up`, `Down`; they are one-hot encoded, not interpreted as continuous dosage. Diagnosis codes are deterministically collapsed into nine broad categories: circulatory, diabetes, digestive, genitourinary, injury, musculoskeletal, neoplasms, respiratory and other. Missing counts include race 2,234, payer 39,398, specialty 48,616, max glucose 94,191 and A1C 82,509; missing categoricals receive a fold-fitted `__MISSING__` category. `encounter_id`, `patient_nbr`, `weight` and raw `readmitted` are excluded from predictors. Patient identity is used for grouping before removal.

Hospital130 is a supporting separate-endpoint engineering study for grouped holdout evaluation, clustered bootstrap, SHAP and routing. It is neither an external validation dataset for screening nor eligible for mixed diabetes-status routing.

## Cross-dataset differences and why they matter

| Dimension | PIDD | Sylhet | BRFSS | Hospital130 |
|---|---|---|---|---|
| Population | small population-specific clinical cohort | small symptom-enriched clinical cohort | large US self-report survey | US hospital encounters involving diabetes |
| Endpoint | dataset diabetes label | early-stage diabetes class | reported diagnosed diabetes status | readmission within 30 days |
| Inputs | labs/vitals/history | symptoms/demographics | survey health/lifestyle/access | encounter, diagnoses, utilization, medication |
| Evaluation | repeated nested stratified CV | repeated nested grouped CV | stratified holdout + dev CV | patient-grouped holdout + dev CV |
| Key bias | small/specific | duplicates and spectrum | self-report/survey sampling | encounter/patient dependence and separate target |

Different prevalence changes AP, Brier and useful thresholds. Similar column names can have different units or meanings. Different targets prohibit pooled labels and probabilities. Separate cohorts prevent direct claims of external generalisation. Missingness mechanisms differ: PIDD uses sentinel zeros; BRFSS uses nonresponse; Hospital130 contains “not measured/not recorded” categories; Sylhet has no missing fields but many duplicate profiles.

# 5. FEATURE ONTOLOGY / MASTER FEATURE DICTIONARY

The ontology is a declarative semantic contract in `config/feature_ontology.yaml`. `features/ontology.py -> build_feature_dictionary()` validates every configured feature and emits one row per dataset feature; `write_feature_ontology()` writes CSV, Markdown and metadata under `outputs/publication_pipeline/feature_ontology/`. The dictionary has 91 rows: 19 explicit shared/related mapping rows and 72 automatically labelled `dataset_specific::<dataset>::<feature>` rows.

It solves a **false-harmonization** problem: column resemblance does not establish interchangeable measurement or endpoint. Each explicit row records endpoint, source feature, configured type, canonical concept, domain, relation (`direct`, `binned`, `proxy`, `not_comparable`), measurement scale and harmonization policy.

| Canonical concept | PIDD | Sylhet | BRFSS | Hospital130 | Safe interpretation |
|---|---|---|---|---|---|
| age | `Age` years | `Age` years | `Age` 5-year group code | `age` 10-year bracket code | related; conversion may be possible within screening, not automatic or cross-endpoint |
| body_mass_index | `BMI` kg/m² | `Obesity` binary proxy | `BMI` kg/m² | — | Sylhet proxy must not be substituted as numeric BMI |
| sex_gender | — | `Gender` binary recorded gender | `Sex` binary recorded sex | `gender` category | cohort-specific encoding; Hospital is different endpoint |
| blood_pressure | `BloodPressure` diastolic mmHg | — | `HighBP` binary status | — | direct measurement vs history/status proxy; not interchangeable |
| glycemia | `Glucose` quantitative | — | — | `max_glu_serum` categorical result | not interchangeable and cross-endpoint |
| insulin | `Insulin` serum measurement | — | — | `insulin` medication-change category | explicitly not comparable |
| physical_activity | — | — | `PhysActivity` binary | — | dataset-specific direct concept |
| healthcare_utilization | — | — | `AnyHealthcare` coverage flag | `number_inpatient` prior-year count | explicitly not comparable |

There are no configured aliases beyond these explicit source mappings. Units are strings in `measurement_scale`; categorical value vocabularies remain in loader/source semantics rather than a universal ontology vocabulary. Features without a defensible relation—including PIDD pedigree/family-history score and nearly all Sylhet symptoms—remain dataset-specific. “Hypertension” is represented only approximately by BRFSS `HighBP`; it is not an alias for PIDD diastolic pressure.

The ontology does **not** preprocess values, create common columns, impute missing concepts, select a router model, or translate patient input. The dataset loader and preprocessing pipeline still use dataset-native fields. Routing reads `availability_scenarios.yaml`, not the ontology. Patient input must be dataset-namespaced. The ontology's runtime value is constraint/audit/documentation: endpoint first, only evaluated panels, no fabricated measurements, no pooled incompatible probabilities.

Four terms must be separated:

- **same name:** text matches, e.g. PIDD/Sylhet `Age`; insufficient evidence by itself;
- **same meaning:** comparable construct and scale, e.g. both age in years, still population-specific;
- **similar meaning:** proxy/binned relation, e.g. BMI vs Obesity;
- **safe interoperability:** requires a validated transformation/model and compatible endpoint/population. The ontology documents semantics; it does not prove this final condition.

# 6. DATA PREPROCESSING AND LEAKAGE AUDIT

## Loading and outcome-blind cleaning

`data/loaders.py -> load_dataset()` dispatches to four loaders. Deterministic, non-learned conversions happen before splitting: PIDD sentinel zero→NaN; Sylhet Yes/No, class and gender encoding; BRFSS target filtering and code recoding; Hospital death/hospice exclusion, age parsing and diagnosis grouping. These transformations do not estimate parameters from outcomes or the full predictor distribution.

## Fold-fitted preprocessing

`preprocessing/builders.py -> build_preprocessor()` constructs a scikit-learn `ColumnTransformer`:

- numeric: `SimpleImputer(strategy="median", add_indicator=True, keep_empty_features=True)`;
- Logistic Regression numeric path additionally uses `StandardScaler`;
- categorical: constant `__MISSING__` imputation then `OneHotEncoder(handle_unknown="ignore", dtype=float32)`;
- tree models receive imputed numeric values without scaling.

`training/tuning.py`, `runner.py` and `holdout_runner.py` clone and fit the preprocessor inside each inner-training or outer-development partition. The outer validation/test record never fits medians, scaling or category vocabularies.

There is no global outlier removal, winsorization, feature selection, PCA or SMOTE. Outliers within allowed validation contracts are retained. Class balance is model-specific and tuning-controlled: Logistic Regression/Random Forest may use `class_weight`; XGBoost may receive a training-only `scale_pos_weight`; LightGBM/CatBoost have analogous options. No outcome oversampling is used.

## Splitting

- PIDD: 5 repeats × 5 outer stratified folds; 5 inner stratified folds.
- Sylhet: same repetition/fold counts but stratified-group folds using identical-profile group IDs in both outer and inner loops.
- BRFSS: deterministic stratified 80/20 holdout, then five development folds.
- Hospital130: one fold of a five-fold stratified-group design becomes test (~20%), with five grouped development folds; patient groups never cross partitions.

The standard seed is 42. Manifests store row IDs, groups, targets and fold roles for development audit. `splitting/concealment.py` creates an outcome-blind sanitized holdout representation and contains final-run guards.

## Calibration and thresholds without outer leakage

For each outer fold, inner/out-of-fold development predictions choose identity, sigmoid or—only when calibration N≥1,000—isotonic calibration by Brier score then log loss. Fixed 0.5, Youden's J and ≥0.80 sensitivity thresholds are derived only from development predictions. Tuning optimizes average precision in inner CV. The held-out fold/test is evaluated after choices are fixed.

## Explicit leakage audit

| Risk | Final status | Evidence and judgment |
|---|---|---|
| Global imputation/scaling | Addressed | fitted within training partitions in `tuning.py`/runners |
| SMOTE before split | Not applicable | no SMOTE/oversampling implementation |
| Whole-data feature selection | Not applicable | no learned feature selection |
| Test-guided hyperparameters | Addressed architecturally | tuning uses development only; smoke test observations cannot be reused as final evidence |
| Sylhet duplicate profiles | Addressed | profile groups isolate duplicates in outer/inner CV |
| Hospital repeated patients | Addressed | patient grouping throughout |
| BRFSS repeated response vectors | Partially unavoidable | no identity evidence; not grouped |
| Repeated test inspection | Final path guarded, development tests already inspected | the full seed-42 BRFSS development-test and Hospital smoke test are permanently development-only |
| Manifest label exposure | Safe for development; final path now fail-closed | ordinary manifests contain target; final execution requires a separate outcome-blind concealed manifest bound by hashes and authorization |

`evaluation/leakage_demonstrations.py` deliberately implements invalid comparators and labels them as non-selection evidence. In Sylhet, naïve row splitting produced 263 validation-profile overlaps and inflated AUROC from approximately 0.9574 (grouped) to 0.9735, while Brier improved misleadingly from 0.0798 to 0.0565. A global-preprocessing demonstration had negligible numerical effect in these datasets, which means “no observed inflation here,” not that global preprocessing is acceptable.

The main unresolved methodological exposure is not a preprocessing leak but evidence reuse: the full seed-42 BRFSS development-test and Hospital smoke test have been accessed, so neither can become sealed final evidence. Current code separates one-time concealed-manifest creation from execution authorization, binds a future final run to raw-data, manifest, source/configuration, seed and signed-record hashes, and writes a non-overwritable test-access receipt before outcome loading. That guard is strong procedural engineering, but it has not yet been exercised on an authorized unseen final test or enforced by an independent data custodian.

# 7. MACHINE-LEARNING MODELS

`models/registry.py` registers five families. `models/base.py` defines model adapters. Every dataset can use the five-model benchmark in current code; routing evaluates the four tree families. Older Hospital smoke artifacts contain only four models because Logistic Regression was added to the default holdout bank later.

| Model | Core configuration/search space | Preprocessing | Role/status |
|---|---|---|---|
| Logistic Regression | elastic-net concept represented as `l1_ratio` 0 or 1 with liblinear; C 1e-3–100 log; class weight none/balanced; max_iter 3000 | median+indicators+scaling; one-hot categories | active benchmark and strong linear baseline; not router candidate |
| Random Forest | 200–800 trees; depth None/6/10/16/24; min split 2–20; leaf 1–16; max features sqrt/log2/0.5; weights | median/indicators, one-hot | active benchmark/router |
| XGBoost | 200–800 trees, depth 3–8, LR .01–.2 log, child weight 1–20 log, subsample/colsample .6–1, gamma 0–3, alpha 1e-5–3, lambda .1–10, optional training-derived balance; binary logistic/hist | median/indicators, one-hot | active benchmark/router; no privileged “final XGBoost” |
| LightGBM | 200–800 trees; LR .01–.2 log; leaves 15–127; depth -1/4/6/8/12; child samples 10–80; row/column sample .6–1; alpha 1e-5–3; lambda .1–10; weight none/balanced | same | active benchmark/router; deterministic column-wise option |
| CatBoost | 200–800 iterations; depth 3–9; LR .01–.2; L2 1–15; random strength 0–3; optional auto-balance | same transformed matrix | active benchmark/router |

Optuna uses a seeded TPE sampler and median pruning, optimizing mean inner-fold average precision. Actual selected hyperparameters differ by dataset, repeat and outer fold; there is no honest single list of “the PIDD XGBoost hyperparameters.” Each reloadable bundle stores its own selected parameters. PIDD/Sylhet full development uses 30 trials per model per outer fold, 5 repeats × 5 outer folds and 500 bootstrap resamples. The BRFSS holdout study uses 30 trials per model over five development folds, then one full-development refit per family and 500 development-test bootstraps. Pilot uses five trials, one repeat and 200 bootstraps; smoke uses reduced partitions/folds/trials. Planned final uses 75 trials and 2,000 bootstraps but is locked=false and unexecuted.

The authoritative BRFSS development refit parameters are concrete and single-valued because there is one refit per family: LR `C=0.0010156`, L2 (`l1_ratio=0`), no class weight; RF 500 trees, unlimited depth, `sqrt` features, minimum split 19, minimum leaf 12, no class weight; XGBoost 500 trees, depth 5, learning rate 0.03018, child weight 4.3078, subsample 0.6574, column sample 0.8859, gamma 2.0590, alpha 2.7706, lambda 2.0943, no class weight; LightGBM 600 trees, 61 leaves, depth 8, learning rate 0.01346, minimum child 21, subsample 0.8596, column sample 0.6810, alpha `7.65e-05`, lambda 1.8285, no class weight; CatBoost 700 iterations, depth 6, learning rate 0.04908, L2 10.9503, random strength 0.7016, with balanced automatic class weights. These are development-selected parameters, not clinical or universally optimal settings.

There is no universal model and no final deployed model. PIDD and Sylhet have 25 outer bundles per model in full development. Holdout studies produce one refit model per family after development selection. Router bundles store scenario choices across fold-specific models. Joblib artifacts are regenerated locally and ignored by Git.

XGBoost was reasonable because nonlinear interactions, missing indicators and mixed feature effects can benefit from boosted trees, and it was central to the legacy idea. The final evidence shows why it is not sufficient as the project's identity: CatBoost is numerically strongest in several full-development tables; Logistic Regression is competitive on PIDD/BRFSS; no corrected universal superiority is established.

# 8. MODEL EVALUATION AND ACTUAL RESULTS

## Metrics actually computed

`evaluation/metrics.py -> probability_metrics()` and threshold metric helpers calculate: N, positives, prevalence, AUROC, average precision (PR-AUC summary), Brier score, scaled Brier, log loss, calibration intercept, calibration slope, observed:expected ratio, 10-equal-count-bin expected calibration error, accuracy, balanced accuracy, sensitivity/recall, specificity, false-positive/false-negative rates, PPV/precision, NPV, F1, Matthews correlation coefficient, Youden index, positive/negative likelihood ratios, diagnostic odds ratio and TN/FP/FN/TP. `evaluation/decision_curve.py` adds net benefit; other modules add bootstrap CIs, paired contrasts and Holm-adjusted p-values.

AUROC measures ranking but can hide low precision in imbalanced cohorts. AP reflects positive-class retrieval relative to prevalence. Brier/log loss judge probabilities; calibration slope/intercept/O:E diagnose systematic probability error. Sensitivity matters for missed cases, specificity/PPV for unnecessary follow-up. Threshold-free metrics cannot select a clinical action threshold. Decision-curve net benefit encodes a threshold-specific harm trade-off but is not clinical validation.

## Full PIDD development: participant-aggregated calibrated probabilities, threshold 0.5

Each of 768 people has five repeat-level out-of-fold probabilities averaged before primary participant-level metrics. Evidence: `outputs/.../pidd_development_072cd2104089/participant_*` and conference tables.

| Model | AUROC | AP | Brier | Log loss | Accuracy | Sensitivity | Specificity | F1 | TN/FP/FN/TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| CatBoost | **0.8444** | 0.7092 | **0.1517** | **0.4620** | 0.7604 | 0.5896 | 0.8520 | 0.6320 | 426/74/110/158 |
| LightGBM | 0.8387 | **0.7132** | 0.1539 | 0.4680 | 0.7604 | 0.6007 | 0.8460 | 0.6364 | 423/77/107/161 |
| Logistic Regression | 0.8376 | 0.7117 | 0.1557 | 0.4749 | **0.7669** | 0.5560 | **0.8800** | 0.6247 | 440/60/119/149 |
| Random Forest | 0.8395 | 0.7095 | 0.1539 | 0.4680 | 0.7617 | **0.6007** | 0.8480 | **0.6376** | 424/76/107/161 |
| XGBoost | 0.8383 | 0.7059 | 0.1540 | 0.4690 | 0.7630 | 0.5970 | 0.8520 | 0.6375 | 426/74/108/160 |

Interpretation: model differences are small; no Holm-corrected superiority. At 0.5 roughly 40% of positives are missed, so this arbitrary operating point is not a clinically safe screening policy. CatBoost is numerically best on AUROC/Brier/log loss, not proven universally superior.

## Full Sylhet development: participant-aggregated calibrated probabilities, threshold 0.5

| Model | AUROC | AP | Brier | Log loss | Accuracy | Sensitivity | Specificity | F1 | TN/FP/FN/TP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| CatBoost | **0.9696** | **0.9838** | **0.0609** | **0.2133** | **0.9288** | 0.9219 | **0.9400** | **0.9410** | 188/12/25/295 |
| LightGBM | 0.9608 | 0.9783 | 0.0721 | 0.2452 | 0.8923 | 0.9188 | 0.8500 | 0.9130 | 170/30/26/294 |
| Logistic Regression | 0.9553 | 0.9738 | 0.0805 | 0.2618 | 0.8962 | 0.9188 | 0.8600 | 0.9159 | 172/28/26/294 |
| Random Forest | 0.9682 | 0.9812 | 0.0674 | 0.2264 | 0.9019 | **0.9281** | 0.8600 | 0.9209 | 172/28/23/297 |
| XGBoost | 0.9610 | 0.9767 | 0.0749 | 0.2447 | 0.8923 | 0.9125 | 0.8600 | 0.9125 | 172/28/28/292 |

Interpretation: excellent internal grouped discrimination, but high prevalence, symptom enrichment, small N and repeated profiles limit transportability. CatBoost is numerically strongest, yet corrected pairwise evidence does not prove it superior.

## Full BRFSS development holdout (`brfss_development_holdout_56407ef53bba`)

The raw cohort has 429,360 retained respondents. The deterministic seed-42 manifest assigns 343,488 rows (45,805 positives) to development and 85,872 rows (11,451 positives; prevalence 13.3350%) to a development-test role. The entire cohort was used (`sample_limit_per_partition=null`). This is the current authoritative BRFSS **full development** study, not a final locked study: the test outcomes have been inspected and `test_access=development_test_previously_accessed_not_final_eligible`.

Calibrated probabilities at fixed threshold 0.5:

| Model | Calibrator | AUROC (95% bootstrap CI) | AP (95% CI) | Brier (95% CI) | Log loss (95% CI) | Sensitivity | Specificity | TN/FP/FN/TP |
|---|---|---:|---:|---:|---:|---:|---:|---|
| XGBoost | identity | **0.8430** (0.8397–0.8463) | **0.4436** (0.4344–0.4519) | **0.09150** (0.09082–0.09222) | **0.29581** (0.29346–0.29798) | 0.1783 | 0.9802 | 72,949/1,472/9,409/2,042 |
| CatBoost | sigmoid | 0.8430 (0.8394–0.8463) | 0.4421 (0.4346–0.4507) | 0.09153 (0.09083–0.09222) | 0.29584 (0.29370–0.29826) | 0.1791 | 0.9807 | 72,982/1,439/9,400/2,051 |
| LightGBM | identity | 0.8428 (0.8391–0.8463) | 0.4432 (0.4342–0.4519) | 0.09154 (0.09082–0.09225) | 0.29599 (0.29366–0.29838) | 0.1773 | 0.9804 | 72,964/1,457/9,421/2,030 |
| Random Forest | sigmoid | 0.8396 (0.8364–0.8432) | 0.4371 (0.4292–0.4459) | 0.09207 (0.09136–0.09274) | 0.29810 (0.29566–0.30024) | 0.1621 | 0.9819 | 73,071/1,350/9,595/1,856 |
| Logistic Regression | isotonic | 0.8329 (0.8297–0.8364) | 0.4043 (0.3967–0.4124) | 0.09400 (0.09337–0.09464) | 0.30311 (0.30081–0.30529) | 0.1127 | 0.9865 | 73,419/1,002/10,160/1,291 |

The lowest development out-of-fold Brier was LightGBM 0.091391, narrowly ahead of XGBoost/CatBoost 0.091395, so LightGBM—not the slightly better development-test XGBoost—was the locked development champion. Forty paired model contrasts were computed with 500 individual bootstraps; 28 are Holm-significant, principally separating the leading tree models from Random Forest/Logistic Regression. None of the XGBoost/CatBoost/LightGBM contrasts survives Holm correction, so there is no defensible unique winner among the leading three.

At the development-selected sensitivity-constrained thresholds, XGBoost uses 0.136584 and yields sensitivity 0.8034/specificity 0.7250; LightGBM 0.136477 gives 0.8038/0.7258; CatBoost 0.138914 gives 0.8030/0.7233. This shows why the 0.5 classification table must not be treated as the screening operating point. These thresholds are still development-derived and not clinically authorized.

Survey sensitivity reweights the same 85,872 respondents. It contains 53 state/territory codes, 1,292 strata and 35 lonely strata; Kish effective N is about 21,165.5. Weighted prevalence is 10.9466%. Weighted XGBoost AUROC is 0.8707 (95% CI 0.8641–0.8766), AP 0.4480 (0.4285–0.4685), Brier 0.07517 (0.07303–0.07776), and log loss 0.24619. This is a design sensitivity analysis, not an official CDC variance estimate or a population-validated model.

Historical BRFSS smoke studies remain in `outputs/.../studies/brfss_smoke_*`. The most recent five-model smoke `brfss_smoke_holdout_b3a6ad2aa89e` had N=10,000 and CatBoost AUROC/AP/Brier 0.8316/0.4211/0.0936. It is superseded as the implementation snapshot by the full development study but remains useful execution provenance. Neither is final locked evidence.

## Hospital130 full development (`hospital130_development_holdout_c3aa5fb84a7a`)

The separate 30-day-readmission study retained 99,343 encounters from 69,990
patients, with 11,314 positives (11.39%). Patient-grouped splitting assigned
79,475 encounters to development and 19,868 encounters from 14,003 patients to
the development test role. No patient crossed the holdout boundary or a
development fold. All five benchmark families completed 30 tuning trials,
development-only calibration/threshold/champion selection, and 500 patient-
cluster bootstrap replicates.

| Model | AUROC | AP | Brier | Log loss |
|---|---:|---:|---:|---:|
| LightGBM | **0.6792** | **0.2288** | **0.09584** | **0.33271** |
| XGBoost | 0.6781 | 0.2269 | 0.09594 | 0.33308 |
| CatBoost | 0.6781 | 0.2287 | 0.09589 | 0.33305 |
| Random Forest | 0.6729 | 0.2281 | 0.09604 | 0.33393 |
| Logistic Regression | 0.6610 | 0.2007 | 0.09715 | 0.33769 |

Development OOF evidence selected sigmoid-calibrated LightGBM. Tree-family
differences did not survive Holm correction; every tree family did improve over
Logistic Regression in the prespecified four-metric artifact-ablation family.
Availability routing, matched-panel contrasts, selective prediction, age/sex/
race subgroups, held-out SHAP, and exact bundle replay are complete. Historical
study `hospital130_smoke_holdout_6640beff7a08` remains preserved as smoke-only
execution provenance and is not current evidence.

# 9. `summary_metrics.csv` AND RESULT ARTIFACTS

The nested runner's `summary_metrics.csv` groups fold metric rows by model, probability version and threshold policy, then averages scientific columns and adds `outer_evaluations`. Consequently `n`, `positives`, TN/FP/FN/TP may be fractional: they are means per outer validation fold, not whole-cohort counts. In a 5-fold PIDD study, mean N≈153.6. For repeated-CV primary inference, aggregate `participant_predictions.csv` and use `participant_confidence_intervals.csv` plus `participant_paired_model_comparisons.csv`; no literal `participant_metrics.csv` file is written.

The holdout runner's `summary_metrics.csv` is not an average: it is one sorted test metric row per model × probability version × threshold policy. Identity columns defined in `config/output_schemas.yaml` are experiment, dataset, task, endpoint, model, repeat/fold, evaluation role, probability version and threshold policy. Metric columns are N, positives, prevalence, discrimination/probability/calibration values and classification values. The code calculates additional metrics beyond the minimal schema.

Exact nested-summary columns are `model`, `probability_version`, `threshold_policy`; mean `n`, `positives`, `prevalence`, `threshold`; `auroc`, `average_precision`, `brier_score`, `scaled_brier_score`, `log_loss`; `calibration_intercept`, `calibration_slope`, `observed_expected_ratio`, `expected_calibration_error`; `accuracy`, `balanced_accuracy`, `sensitivity`, `specificity`, `false_positive_rate`, `false_negative_rate`, `ppv`, `npv`, `f1`, `mcc`, `youden_index`, `positive_likelihood_ratio`, `negative_likelihood_ratio`, `diagnostic_odds_ratio`, `tn`, `fp`, `fn`, `tp`; and `outer_evaluations`. `probability_version` distinguishes raw from calibrated estimates; `threshold_policy` identifies fixed/Youden/sensitivity rules; `threshold` is the mean learned cutoff in the nested summary; `outer_evaluations` counts contributing fold evaluations. All remaining names have the standard definitions described in Section 8.

The holdout header adds `experiment_id`, `dataset`, `task`, `endpoint`, `evaluation_role`, `calibration_method`, and `development_selected_champion`; it omits `outer_evaluations` because each row is one test evaluation. These fields specify study identity, endpoint, that the row is held-out test evidence, selected calibrator, and whether the family won the development-only champion rule.

Common artifacts and meaning (exact names differ by runner):

- `predictions.csv` (nested) or `test_predictions.csv` (holdout): row-level raw/calibrated probability and thresholded prediction with repeat/fold/provenance;
- `fold_metrics.csv` (nested) or direct rows in holdout `summary_metrics.csv`: evaluation metric rows;
- `summary_metrics.csv`: fold means for nested CV, direct test rows for holdout;
- `participant_predictions.csv` plus `participant_confidence_intervals.csv` and `participant_paired_model_comparisons.csv`: one inference unit after repeat aggregation and its inference; participant metrics are recomputed from the aggregated table rather than stored in a file literally named `participant_metrics.csv`;
- `confidence_intervals.csv`: fold/test bootstrap intervals with declared resampling unit;
- `paired_model_comparisons.csv` (nested) or `paired_bootstrap_model_comparisons.csv` (holdout): paired contrasts and Holm correction;
- `selected_thresholds.csv`: development-learned thresholds by policy;
- `calibration_selection.csv`: candidate/selected calibrators;
- `decision_curve*.csv`: threshold-specific net benefit and uncertainty;
- `models/*.joblib`: preprocessor, estimator, calibrator, thresholds, feature names and provenance;
- `explainability/*.csv` and plots: SHAP values, grouped importance, local contributors, dependence and stability;
- `availability_routing/**`: scenario model selection, routed predictions, router bundles and comparisons;
- ablation folders: matched panels, indicators, panel training, stress, selective/subgroups/leakage/reporting analyses;
- `experiment_metadata.json`: configuration, hashes, versions and sometimes machine-specific absolute paths.

Why versions disagree: pilots vs full development; one vs five repeats; fold means vs pooled predictions vs participant aggregation; four- vs five-model code; source/config hash changes; smoke subsampling; BRFSS endpoint/cohort revisions; and Hospital death/hospice correction. The unversioned aliases `outputs/publication_readiness_audit.md` and `outputs/.../<dataset>_audit.json` can be stale; prefer study-linked hashed audits, `config/authoritative_studies.yaml`, `evidence/study_registry.json`, and the current conference QA audit. The authoritative interpretation is not “choose the largest number”: identify the estimand and evidence tier. No file contains final locked results.

# 10. TP / TN / FP / FN ERROR ANALYSIS — FALSE-POSITIVE AND FALSE-NEGATIVE BEHAVIOR

`evaluation/metrics.py` converts calibrated probabilities to `prediction = probability >= threshold` and assigns counts conventionally: TP=(target 1,prediction 1), TN=(0,0), FP=(0,1), FN=(1,0). The threshold policy may be fixed 0.5, development-Youden, or development-sensitivity-constrained. Thresholds are fold-specific when learned.

The final active pipeline **does not perform the richer error-group analysis implied by some earlier discussion**. It saves row-level predictions and confusion counts, but it does not compare age/BMI/glucose distributions between TP/TN/FP/FN, run statistical tests between error groups, or produce SHAP summaries stratified by error type. `reporting/patient_results.py` can explain any supplied patient; it is not an automated false-negative cohort analysis. Historical legacy code selected representative TP/TN/FP/FN cases for waterfall-style inspection, but that code is outside the authoritative package.

Therefore no feature-pattern claims about “typical false negatives” are supported. The supported findings are quantitative:

- PIDD at 0.5: participant-aggregated FNs range from 107 to 119 of 268 positives depending on model; CatBoost has 110 FNs and 74 FPs.
- Sylhet at 0.5: 23–28 FNs of 320 positives; CatBoost has 25 FNs and 12 FPs.
- BRFSS full development-test at 0.5: XGBoost has 9,409 FNs and 1,472 FPs; CatBoost has 9,400 FNs and 1,439 FPs. The low sensitivity is a threshold consequence, not a failure of ranking discrimination.
- Hospital130 smoke at 0.5: XGBoost has 1,135 FNs and only four TPs because probabilities rarely exceed 0.5.
- Lower development-selected sensitivity thresholds reduce FNs but increase FPs; this is a policy trade-off, not a free accuracy gain.

False negatives matter because a missed positive could delay follow-up, but this retrospective label is not synonymous with an undiagnosed real patient. A proper extension would predefine error strata, use participant-level held-out data, compare distributions with uncertainty/multiplicity control, add subgroup intersections, and aggregate local SHAP within each error class without causal language.

# 11. EXPLAINABLE AI / SHAP

## Implementation contract

`explainability/shap_analysis.py -> _compute_shap()` uses:

- `shap.LinearExplainer` for Logistic Regression on raw log-odds;
- `shap.TreeExplainer` for Random Forest on raw positive-class probability;
- `shap.TreeExplainer` for XGBoost, LightGBM and CatBoost on raw margin.

Calibration is downstream, so SHAP reconstructs the **base model's raw output**, while saved rows also carry raw and calibrated probabilities. `_positive_class_values()` normalizes SHAP library output shapes. `_model_output()` independently computes the model output; reconstruction error checks additivity. `group_shap_by_original_feature()` sums one-hot and missing-indicator components to the original input feature.

For nested CV, each saved outer model explains only its held-out validation rows. Default maximum is 1,000 rows per fold, with a seeded stratified subsample if needed; background sample is 100. Holdout SHAP (`explainability/holdout_shap.py`) uses development rows for reference/background and test rows for reported explanations. It does not use test labels to fit the explainer.

Artifacts include long-form transformed and original-feature SHAP tables, mean-absolute global importance, local top contributors, dependence bins/transitions, reconstruction checks, between-fold rank stability, and PNG/SVG bar, beeswarm and dependence plots. There are no final force/waterfall plots and no formal SHAP interaction-value analysis.

## Findings

For full-development PIDD, Glucose ranks first and BMI second in all model families. Tree models generally rank Age third and DiabetesPedigreeFunction fourth; Pregnancies or Insulin follows. Higher Glucose and BMI have strong positive feature-value/SHAP associations; higher Age is positive in tree models. BloodPressure direction is weaker/mixed. Full-study fold-pair mean rank Spearman is approximately CatBoost 0.944, LightGBM 0.908, Logistic Regression 0.917, Random Forest 0.918 and XGBoost 0.898, with mean top-five Jaccard around 0.77–0.81.

For Sylhet, Polyuria and Polydipsia are the top two concepts in every family (order can reverse for Logistic Regression), followed commonly by Gender. Presence of polyuria/polydipsia generally raises the model output. Male=1 has a negative value-SHAP association in this cohort/model, which means female-coded 0 tends to contribute more positively relative to the model baseline; it is not a biological or causal conclusion. Itching is negative in several models; Irritability often positive.

Full BRFSS development-test SHAP explains a seeded stratified sample of 1,000 held-out respondents per model, with 100 development rows as background/reference. The original-feature top five are: CatBoost `GenHlth, Age, BMI, HighChol, HighBP`; LightGBM `GenHlth, HighBP, Age, BMI, HighChol`; Logistic Regression the same order as LightGBM; Random Forest `HighBP, GenHlth, HighChol, BMI, Age`; XGBoost `GenHlth, HighBP, Age, BMI, HighChol`. Maximum reconstruction error ranges from `2.22e-15` (LR) to `5.52e-6` (XGBoost), within the implemented tolerances. There is no fold-stability estimate for BRFSS because each family has one refitted development model and one development-test explanation, not repeated outer folds. Hospital smoke explanations emphasize prior inpatient use, discharge disposition, diagnosis count and utilization/care variables; those remain smoke findings.

Traditional Random-Forest impurity or boosting gain asks how often/how effectively features split training data. Global SHAP here is mean absolute contribution on held-out rows. Local SHAP is a signed contribution for one row relative to that model's baseline. SHAP direction is model- and encoding-specific; it does not show causal effects, treatment targets or clinical thresholds. Cross-family absolute magnitudes cannot be compared because explanation scales differ.

# 12. MULTI-DATASET GENERALISATION

The project trains separate models for each dataset. It does not concatenate PIDD, Sylhet, BRFSS and Hospital130. It does not train on one dataset and test on another. It does not construct a single common-feature cohort. It does not learn a harmonized cross-dataset representation. There is no matched patient cohort with all three screening schemas.

What is genuinely multi-dataset:

- a common software/evaluation contract runs on four adapters;
- endpoint and feature semantics are audited in one ontology;
- each dataset has predeclared availability panels and routing evaluation;
- namespaced input can be evaluated by more than one eligible screening expert, but final safe behaviour chooses an explicit environment or abstains;
- results are compared narratively as separate studies, not pooled statistically.

What this demonstrates is **engineering portability and within-dataset robustness to prespecified availability**, plus awareness of semantic incompatibility. It does not demonstrate external validation, cross-country generalisation, transportability from PIDD to BRFSS, or universal diabetes risk. Hospital130 provides no screening generalisation evidence because its endpoint differs.

# 13. AVAILABILITY ROUTING

## Meaning and training-time evaluation

Availability means which non-null dataset-native fields a request contains. Each `availability_scenarios.yaml` panel is a set of features evaluated during development. The routing evaluator (`routing/evaluator.py`) starts from a model trained on the full dataset schema and masks unavailable panel features to NaN in inner-development and outer-evaluation data. It selects a candidate model family for each panel using the lowest development Brier score, tie-breaking by log loss then negative AP. Four tree families are candidates. A robust single-model comparator uses the full-panel champion across all panels.

The router's learned metadata includes dataset/task/endpoint, scenario feature lists, candidate and selected models, calibration/thresholds, development quality values, source/profile/evidence tier and saved fold bundle references. Model selection uses development labels; outer labels measure performance only.

## Inference logic

`routing/inference.py -> route_patient()`:

1. derives the available feature set from non-null input fields;
2. if a scenario is explicitly requested, requires every scenario feature;
3. otherwise finds panels whose required features are a subset of available fields;
4. chooses the panel with the most features (tie: `full`, then deterministic name order);
5. loads the development-selected model for that panel;
6. orders all configured dataset features and masks every feature not in the selected panel to NaN;
7. applies the saved preprocessor, estimator and calibrator;
8. applies the stored threshold (usually the bundle's fixed 0.5 policy in current router studies);
9. returns status, scenario, model, calibration method, raw/calibrated probability, threshold/class, available/used/ignored fields and provenance;
10. abstains if no evaluated panel is supported.

Extra fields do not expand the panel ad hoc. Missing values are not “borrowed” from another dataset. A compatible panel is an experimentally evaluated schema, not merely a model that can technically accept NaN.

## Actual panels

- PIDD: full 8; no-insulin/skinfold 6; routine-clinic 5; core-metabolic 4; non-lab 4; glucose+age 2.
- Sylhet: full 16; core questionnaire 10; core symptoms 6; classic symptoms 4; polyuria+polydipsia 2.
- BRFSS: full 21; cardiometabolic 9; routine survey 12; health status 6; demographics/health 5; general-health+age 2.
- Hospital130: full 46; encounter/utilization 9; admission/clinical 9; prior utilization 5; age+prior-inpatient 2.

## Concrete examples

1. PIDD input `{Pregnancies, Glucose, BloodPressure, BMI, Age}` supports `routine_clinic` (five fields). It does not support `no_insulin_or_skinfold` because DiabetesPedigreeFunction is missing. The routine-clinic selected model is used; any supplied SkinThickness is ignored unless a larger complete panel becomes available.
2. PIDD `{Glucose, Age}` supports only `minimal_glucose_age`; it routes there. `{Age}` supports no two-field panel and abstains.
3. Sylhet `{Polyuria, Polydipsia}` routes to `minimal_polyuria_polydipsia`; adding `sudden weight loss` alone does not create a three-field panel, so it remains on the two-field panel.
4. BRFSS `{GenHlth, Age}` routes to `minimal_general_health_age`.
5. Hospital `{age, number_inpatient}` routes to a **readmission** model; it never enters a diabetes-screening mixed result.

## Empirical routing result

Full-development PIDD participant router AUROC/Brier is about 0.843/0.152; core metabolic about 0.839/0.154; glucose+age 0.809/0.166; non-lab 0.756/0.186. Sylhet full router is about 0.965/0.068; minimal symptom panel about 0.905/0.113. Full BRFSS development routing selected LightGBM for the 21-feature full panel and XGBoost for all five reduced panels. BRFSS full/routine-12/cardiometabolic-9/health-6/demographic-5/minimal-2 AUROC values are 0.8428/0.8388/0.8370/0.8286/0.7844/0.7794; corresponding Brier scores are 0.09154/0.09239/0.09269/0.09452/0.10155/0.10198.

Every one of the 80 same-model BRFSS full-versus-reduced point estimates has a degradation interval excluding zero, yet none of the metric-wise Holm-adjusted p-values is below 0.05 (minimum adjusted p about 0.07984 with 500 bootstraps). This apparent tension occurs because the implemented two-sided bootstrap p-value has a finite minimum of `2/(500+1)` and the Holm family is large; effect intervals and multiplicity-adjusted tests must both be reported. Router-vs-robust-fixed and selector-metric gains also did not survive correction. Panel-specific RF/XGBoost retraining was implemented for repeated-CV PIDD/Sylhet and did not show corrected benefit; that retraining engine does not support BRFSS holdout studies. The router is useful as an applicability and degradation mechanism, not a proven superior selection algorithm.

# 14. HOLDOUT ENGINE

`holdout_runner.py` is separate from `runner.py`. BRFSS uses a stratified 80/20 manifest; Hospital130 uses a patient-grouped approximate 80/20 split. Within development, model tuning, calibration selection, threshold selection and development-champion selection are completed using development folds. The champion rule is lowest Brier, then log loss, then higher AP. Only afterward is the test partition read for one evaluation. BRFSS uncertainty resamples individuals; Hospital resamples patient clusters. Metrics, predictions, choices, CIs, comparisons, decision curves, models and hashes are saved. The authoritative BRFSS study used all 343,488 development and 85,872 development-test rows; the authoritative Hospital130 study used all 79,475 development and 19,868 development-test encounters.

This is stronger than a casual `train_test_split` because it has stable row/group identity, stored roles, group isolation, cross-fitted development choices, reloadable artifacts, source/manifests checksums, test-access metadata, outcome-blind final manifests, and a fail-closed authorization layer in `splitting/concealment.py`. A non-smoke run cannot be unlocked casually.

The final guard requires a locked final profile, frozen protocol/analysis plan, completed prespecified gates, signed authorization, authorized seed, authorized raw-data and analysis-configuration hashes, and—for holdout datasets—a checksum-valid outcome-blind concealed manifest. Future split creation is deliberately authorized separately from execution. Immediately before final outcome loading, code claims a non-overwritable access receipt bound to dataset, experiment, raw data, manifest, configuration, seed, purpose and authorization record. Current values are unset/false; read-only preflight for all four datasets returns `authorized=false` and `outcome_accessed=false`. That guard reduces accidental researcher degrees of freedom but does not create external validity or substitute for an independent custodian. The full seed-42 BRFSS and Hospital130 development-test outcomes are permanently development evidence.

Current canonical BRFSS CSV/JSON artifacts have been migrated from the historical
`locked_test` string to explicit `development_test` semantics without rewriting
free-text provenance. Historical studies may retain their original label. Current
code and schema tests distinguish `development_test` from `locked_final_test`,
and neither authoritative holdout study is final eligible.

Scientifically, protected holdout discipline reduces optimistic bias from iterating on test feedback. It does not correct sampling bias, target mismatch, dataset shift, measurement error or lack of prospective validation.

# 15. PATIENT RESULT / INFERENCE PIPELINE

The actual single-dataset flow differs from the tempting ontology-first diagram:

`dataset-namespaced JSON` → `patient_results._coerce_patient()` validation/range checks → load compatible router bundles → `routing.inference.route_patient()` panel detection/selection → saved fold preprocessor → saved model → saved calibrator → calibrated probability → stored threshold/class → per-fold SHAP → normalized cross-fold factor aggregation → cohort context/provenance/applicability/disclaimer.

The ontology is **not called** to translate input. The user or caller must choose/provide a dataset schema. For mixed input, `mixed_patient_results.py` first evaluates namespaced dataset candidates and applies endpoint/environment safety; it never fuses probabilities.

`reporting/patient_results.py` requires bundles to agree on task, scenario contract, threshold policy and evidence metadata. Numeric input must be finite; out-of-observed-range values cause default abstention (an explicit option may downgrade this to a warning). Unknown fields are ignored and reported. All fold routers must agree on the selected scenario. It returns:

- schema/status, dataset/task/endpoint and evidence tier/profile;
- selected panel and used/ignored/unavailable/invalid information;
- mean calibrated probability, min/max/SD across fold models;
- stored threshold, number of folds above threshold, model/calibrator counts;
- leading original-feature SHAP factors with mean normalized importance, median rank and direction agreement;
- reference-cohort quantile context and unadjusted prevalence for numeric factors;
- applicability notes, provenance and research/non-diagnostic disclaimer.

The fold spread is model-fold variability, **not** a confidence interval or individualized uncertainty distribution. There is no risk category beyond thresholded class; no treatment advice; no diagnostic statement.

The synthetic PIDD example `examples/pidd_patient_synthetic.json` provides Pregnancies=2, Glucose=145, BloodPressure=80, SkinThickness=25, BMI=31.5, DiabetesPedigreeFunction=0.5 and Age=45, omitting Insulin. In its retained pilot demonstration, the largest supported panel was `no_insulin_or_skinfold` (which deliberately masks both Insulin and SkinThickness), mean calibrated probability 66.05%, range 59.54–78.38%, all five outer bundles above 0.5, with three CatBoost and two RF choices. Top factors were Glucose, Age, BMI, Pregnancies and pedigree score. This validates formatting/routing only.

Mixed input `examples/mixed_patient_synthetic.json` contains PIDD, Sylhet and BRFSS namespaces. A retained old output explicitly prefers PIDD and reports about 55.16%; candidate cohort estimates are not averaged. Under final default safety, if more than one cohort is eligible and no `preferred_dataset` is provided, the system abstains with `cross_dataset_environment_selection_not_validated`. Experimental priority/coverage auto-selection exists behind explicit opt-in and cannot support efficacy claims.

# 16. COMPLETE SYSTEM ARCHITECTURE

```text
Raw cohort files (ignored)                         Protocol/config contracts
PIDD | Sylhet | BRFSS | Hospital130               datasets | panels | ontology | schemas
          |                                                       |
          v                                                       v
Dataset adapters + validation  -----------------> audits + split manifests
          |                                         |            |
          |                          small cohorts --+-- large cohorts
          |                                |                 |
          v                                v                 v
Fold-local preprocessing         repeated nested CV    dev/holdout engine
median/indicators/scale/one-hot   PIDD, grouped Sylhet  BRFSS, grouped Hospital
          |                                |                 |
          +------------------------> Optuna model bank <-----+
                                   LR/RF/XGB/LGB/Cat
                                             |
                         inner OOF probabilities: calibrator + thresholds
                                             |
                            held-out probabilities, metrics, CIs,
                            paired tests, DCA, model bundles
                               /             |              \
                              v              v               v
                     Held-out SHAP    panel masking/routing   ablations/stress/
                     + stability      + abstention bundles    selective/subgroups
                              \             /
                               v           v
                          patient research report
                    probability + threshold + provenance + explanation
                               |
                       mixed namespaced gate
                 one explicit screening expert or abstain
                               |
                     publication-readiness audit
                 development evidence != final authorization
```

Layer responsibilities:

- `contracts.py` holds dataset/model data structures.
- `settings.py` loads config, derives roots and fingerprints the source tree.
- `data/*` loads, validates, audits and reports research data quality.
- `splitting/*` creates stratified/group manifests and final concealment controls.
- `preprocessing/builders.py` creates fold-fitted transformations.
- `models/*` creates estimators and Optuna search spaces.
- `training/tuning.py` performs inner optimization and out-of-fold prediction.
- `calibration/*` selects calibrators and thresholds.
- `runner.py` and `holdout_runner.py` orchestrate small/large cohort studies.
- `evaluation/*` provides metrics, uncertainty, comparisons, DCA and ablations.
- `artifacts/bundles.py` defines reloadable model bundles.
- `explainability/*` produces held-out SHAP evidence.
- `routing/*` evaluates panels, selects candidates, infers and compares.
- `reporting/*` creates patient, mixed-patient and readiness outputs.

# 17. REPOSITORY MAP

| Path | Purpose / major functions | Input → output | Status |
|---|---|---|---|
| `README.md` | overview/start links and evidence-tier warning | reader → navigation | Current working-tree documentation |
| `pyproject.toml`, `requirements.lock`, `.python-version` | package/CLI plus direct and resolved environment contracts | environment → install/verify | Active; lock resolved for macOS arm64/Python 3.12 |
| `config/datasets.yaml` | endpoint/feature/split contracts | YAML → loaders/splitters | Final/active |
| `config/availability_scenarios.yaml` | evaluated panels/router candidates | YAML → routing | Final/active |
| `config/feature_ontology.yaml` | semantic mappings/contracts | YAML → dictionary | Final/active |
| `config/publication_protocol.yaml` | claim/final-run gates | YAML → readiness/concealment | Final/active; intentionally unlocked |
| `config/output_schemas.yaml` | stable result columns | YAML → validation/reporting | Supporting |
| `config/data_sources.yaml` | official sources, licenses/DOIs, archive members and exact hashes | source contract → acquisition verification | Active/reproducibility |
| `config/authoritative_studies.yaml` | current study IDs, evidence tiers and regeneration commands | YAML → registry/package builders | Active/evidence routing |
| `src/diabetes_pipeline/cli.py` | all user commands | args → workflow | Final/active |
| `data/loaders.py`, `validators.py` | dataset adapters and constraints | raw CSV → `DatasetBundle` | Final/active |
| `data/manifests.py`, `research_audit.py` | audit/fingerprint/research issues | bundle → JSON/MD/CSV | Final/active |
| `splitting/strategies.py`, `registry.py` | deterministic stratified/group splits | bundle → manifest | Final/active |
| `splitting/concealment.py` | sanitized manifests, hash-bound final authorization and one-way access receipt | manifest+protocol+authorization → permit/refuse | Final/active; deliberately denies current final runs |
| `preprocessing/builders.py` | model-specific transformers | raw fold → fitted matrix | Final/active |
| `models/registry.py` | estimator factories/search spaces | trial/config → estimator | Final/active |
| `training/tuning.py` | inner CV/Optuna/OOF predictions | training fold → tuned model/OOF | Final/active |
| `calibration/*` | calibrator and threshold choice | dev OOF → fitted policy | Final/active |
| `runner.py` | PIDD/Sylhet nested studies | dataset/profile → study directory | Final/active |
| `holdout_runner.py` | BRFSS/Hospital studies | roles/profile → study | Final/active |
| `evaluation/*` | metrics, CIs, DCA, ablations | predictions → evidence tables | Final/active/supporting |
| `artifacts/bundles.py` | serializable pipeline objects | fitted components → joblib | Final/active |
| `explainability/*` | SHAP/stability/plots | study+raw rows → explanation artifacts | Final/active |
| `routing/evaluator.py` | nested-CV panel evaluation | study+panels → router artifacts | Final/active |
| `routing/holdout_evaluator.py` | holdout panel evaluation | holdout study → router | Final/active |
| `routing/inference.py` | panel compatibility and prediction | bundle+record → route result | Final/active |
| `reporting/patient_results.py` | single-schema research report | JSON+routers → JSON report | Final/active |
| `reporting/mixed_patient_results.py` | endpoint-safe mixed gate | namespaced JSON → one result/abstain | Final/active; heuristic experimental |
| `reporting/publication_readiness.py` | claim/final artifact audit | studies+protocol → PASS/FAIL | Final/active |
| `tests/` | 28 test modules, 100 tests plus seven adapter subtests | code/config → verification | Supporting/active |
| `docs/progress_reports/` | Blocks A–K evolution | prior checkpoints → history | Historical; some superseded |
| `docs/research/` | SAP, audits, novelty, execution status | evidence → governance | Documentation/supporting |
| `conference_package/` | development manuscript/supplement/tables/figures | studies → draft package | Generated development artifact |
| `evidence/study_registry.json` | tracked hashes/presence map for ignored authoritative artifacts | studies/config → lightweight evidence index | Current; not a substitute for large artifacts |
| `examples/` | synthetic PIDD/mixed JSON | demo input | Supporting |
| `outputs/` | local models/metrics/SHAP | workflows → evidence | Generated, mostly Git-ignored |
| `scripts/build_*` | render conference/system packages | docs/results → package | Supporting |
| `scripts/acquire_data.py` | download/reconstruct and hash-verify all four raw inputs | source manifest → `data/raw` | Active reproducibility helper |
| `scripts/verify_environment.py`, `verify_holdout_bundles.py`, `final_preflight.py` | verify environment, exact BRFSS bundle replay, and outcome-blind authorization state | local workspace → pass/deny evidence | Active safeguards |
| `.github/workflows/ci.yml` | clean automated environment/config/test checks | pushed revision → CI result | Active in working tree |
| `docs/DEFINITIVE_PROJECT_CONTEXT.md` | this self-contained engineering reconstruction | repository + artifacts → context transfer | Documentation/source of truth at audit date |

# 18. MODEL REGISTRY / MODEL METADATA

There are two mechanisms often called a registry:

1. `models/registry.py` is a **model-family registry**: names, estimator factories and trial search spaces.
2. Saved joblib `ModelBundle`/router bundles are the **fitted model registry** used by inference.

A model bundle links dataset/task/endpoint, experiment ID, model family, selected hyperparameters, outer repeat/fold or holdout role, fitted preprocessor, transformed feature names, estimator, calibrator/method, thresholds and provenance hashes. Router artifacts add scenario feature requirements, selected model by panel, development selection metrics, profile/evidence tier and publication eligibility. The actual joblib path is referenced in study/router metadata, but artifacts are ignored rather than committed.

Training writes the bundles after outer/holdout fitting. Routing evaluation refers to them while selecting a model per panel. Patient reporting reloads several outer router bundles and checks metadata consistency before any prediction. Thus preprocessing is inseparable from the estimator, feature order is explicit, threshold/calibrator travel with the model, and dataset provenance is reported. What is missing for production registry quality is an external immutable artifact store, signatures, lifecycle stage, access control, deployment monitoring and a committed manifest resolving every model URI from a clean clone.

# 19. RESEARCH NOVELTY

## Strongest potential novelty

The strongest candidate is the **combination** of endpoint-safe semantic contracts, prespecified feature-availability panels, calibrated degradation evaluation, provenance-preserving one-expert routing, paired uncertainty, explanations and explicit abstention across heterogeneous diabetes-screening cohorts. The contribution is methodological/application-system integration, not a new classifier.

One-sentence defensible claim:

> We implemented and development-evaluated an endpoint-safe, provenance-preserving framework that quantifies calibrated performance degradation across prespecified feature-availability environments and either routes to an evaluated cohort-specific expert or abstains without fusing semantically incompatible diabetes datasets.

## Moderate contributions

- complete 91-feature ontology with explicit “proxy/not comparable” policies;
- group-aware Sylhet duplicate control and patient-grouped Hospital evaluation;
- cross-fitted calibrator/threshold selection with participant-level repeated-CV inference;
- negative-result reporting for dynamic selection and panel retraining;
- integrated held-out SHAP, range checking, fold variability and cohort context in a research report;
- fail-closed publication/final-run guard and claim-to-evidence workflow;
- broad ablation suite: indicators, panel training, stress, selective prediction, subgroups, leakage demonstrations and heuristic/explanation reporting.

## Standard components, not novelty

Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost, Optuna, median imputation, one-hot encoding, nested CV, calibration, ROC/PR curves, Brier score, bootstrap CIs, SHAP plots, decision curves and an 80/20 split are established methods. Merely using four datasets is not novelty. A YAML feature map by itself is not clinical semantic validation.

## What must be proved

For the central claim to be convincing: freeze the protocol; create genuinely fresh authorized final evidence rather than relabeling the completed BRFSS development run; specify primary panels/metrics/margins; retain participant/cluster-level paired uncertainty and multiplicity correction; compare router, robust fixed model and simple baselines on matched people; validate abstention/risk-coverage and calibration; independently review ontology mappings; add an external or temporal cohort; examine subgroups and survey design; and demonstrate that the framework improves a prespecified utility or safety outcome, not merely that it runs. A matched multi-schema cohort would be required to validate automatic environment selection or probability fusion.

# 20. PUBLICATION PIPELINE

There is no tracked file literally named `PUBLICATION_PIPELINE.md`. The relevant sources are repository-root `PUBLICATION_ROADMAP.md` and `PIPELINE_IMPLEMENTATION_PLAN.md` in the parent project, plus T2DM `docs/NEXT_STEPS_PUBLICATION_ROADMAP.md`, `docs/research/*`, `config/publication_protocol.yaml` and `conference_package/*`. Any reference to a literal final pipeline file is a naming misconception.

The planned conference narrative focuses on availability-aware calibrated degradation and abstention in PIDD, grouped Sylhet and BRFSS, with Hospital130 as separate supporting engineering. Primary probability metric is Brier; AUROC/AP are primary discrimination measures; participant is the repeated-CV inference unit; Holm controls multiplicity; planned final bootstrap N is 2,000. Dynamic model selection is a secondary negative result. Mixed routing is software demonstration only.

| Planned element | Current classification | Evidence |
|---|---|---|
| Dataset/endpoint contracts and leakage audit | Implemented and development-validated | Block A, research audit, tests |
| Full PIDD and grouped Sylhet development studies | Implemented and development-validated | studies `072cd...`, `b524...` |
| Full BRFSS development study | Implemented and development-evaluated on all 429,360 retained rows | `brfss_development_holdout_56407ef53bba`; inspected development-test, never final |
| Fresh BRFSS final locked study | Engine/preflight implemented; execution prohibited | protocol/authorization/concealed-manifest fields unset |
| Hospital readmission support | Full-cohort grouped development study, separate endpoint; historical smoke retained | study `hospital130_development_holdout_c3aa5fb84a7a` |
| Calibration/threshold/DCA/paired uncertainty | Implemented and development-validated | evaluation/calibration modules |
| Ontology and panels | Implemented; mappings need independent review | config, generated dictionary |
| Router vs fixed comparison | Implemented; no corrected advantage | routing/contrasts |
| Missing-indicator/panel-training/stress/reporting ablations | Implemented and run for repeated-CV PIDD/Sylhet; not supported by BRFSS holdout runner | ablation directories/docs and `docs/REPRODUCIBILITY.md` |
| BRFSS artifact ablations, selective/subgroup/survey analyses | Implemented in full development; sign-off pending | authoritative BRFSS study artifacts |
| SHAP and patient report | Implemented as research prototype | explainability/reporting modules |
| Automatic cross-dataset selector | Experimental opt-in; unvalidated | mixed reporting/protocol |
| External/temporal validation | Not implemented | protocol flag false |
| Final protocol freeze/concealed run | Not implemented/authorized | final flags false |
| Manuscript/supplement/tables/figures | Development drafts generated | `conference_package/` |
| TRIPOD+AI/PROBAST+AI | Draft crosswalk/assessment, not signed complete | package/protocol |

## Proposed study logic and paper package

**Research question.** Across three intentionally separate diabetes-development cohorts, how much calibrated predictive performance is lost as clinically available inputs become progressively narrower, and can a prespecified availability-aware system preserve useful probability estimates or safely abstain without merging incompatible endpoints and schemas?

**Working hypotheses.** These remain development hypotheses, not confirmed claims: (1) evaluated reduced panels will degrade more gracefully than simplistic baselines on matched people; (2) compact, clinically plausible panels will retain useful discrimination but may lose calibration and positive-class precision; (3) selective prediction will improve performance among accepted cases only at the cost of coverage and potentially harmful case-mix selection; and (4) a dynamic per-person selector may not outperform a simpler robust fixed expert after paired multiplicity correction. Exact superiority/non-inferiority margins are not frozen, so no confirmatory hypothesis test may yet be claimed.

**Experiments already completed.** The repository contains full repeated nested-CV development studies for PIDD and grouped Sylhet, full BRFSS and patient-grouped Hospital130 development holdout studies, calibration and threshold analyses, participant/cluster bootstrap inference, paired Holm-corrected model and panel contrasts, decision curves, routing and robust-comparator analyses, held-out SHAP, reporting, missingness and panel-training ablations for the nested-CV cohorts, BRFSS survey-weighted sensitivity, and supported artifact/selective/subgroup analyses. The automatic mixed-dataset selector is only an opt-in software experiment; it is not clinical validation.

**Experiments still required.** Freeze the protocol and primary panels, estimands, margins and utility assumptions; obtain human authorization for genuinely fresh final runs; complete independent ontology and reporting review; add an external, geographic, prospective or temporal validation cohort; test transport and recalibration; prespecify and assess clinically meaningful subgroup intersections; and, if automatic schema/environment selection is retained as a claim, evaluate it on matched cases for which alternative feature environments are genuinely observed rather than simulated by masking.

**Validation and statistical plan.** Preserve dataset-specific endpoints and never pool cohorts. Use participant-level repeated-CV inference for PIDD and profile-cluster inference for Sylhet; use the immutable development-test role for the current BRFSS development study and a new concealed test only after authorization. Estimate paired bootstrap confidence intervals on identical units, apply metric-wise Holm correction, report AUROC, AP, Brier, log loss and calibration together, and treat threshold metrics and decision curves as policy-dependent. Planned final bootstrap count is 2,000. Survey-weighted BRFSS results are sensitivity evidence. Any final paper must explicitly distinguish descriptive development analyses, prespecified primary tests and post-hoc analyses.

**Intended main tables.** A defensible final package would contain: (1) cohort, endpoint, prevalence, grouping, split and missingness characteristics; (2) primary participant/cluster-level PIDD and Sylhet model performance with confidence intervals; (3) BRFSS model performance on its authorized evaluation role, including weighted sensitivity; (4) matched full-to-reduced panel degradation and robust-router contrasts; and (5) selective-prediction and subgroup results with coverage, accepted-case prevalence and uncertainty. The current conference Table 1/2 presentation uses means across outer-fold evaluations for PIDD/Sylhet, whereas the statistical plan identifies aggregated participant/profile inference as primary. That is a draft-package inconsistency: a submission should replace or clearly demote fold means and use the participant/cluster estimates and intervals as the main result.

**Intended figures.** The generated package currently provides PIDD model performance, PIDD risk-coverage/panel behavior, PIDD missingness stress, Sylhet performance/panels and BRFSS performance/panels. Dataset study directories additionally provide ROC, precision-recall, calibration, probability, decision-curve and SHAP graphics. A final paper should keep a compact data-flow/endpoint schematic and the primary matched panel/risk-coverage result in the main text; move model-by-model diagnostic curves, dependence plots, full threshold grids, subgroup details and ablations to the supplement.

**Possible paper structure.** Introduction: feature availability, endpoint heterogeneity and the danger of optimistic schema pooling. Methods: cohort contracts, leakage controls, splitting, preprocessing, model/calibration selection, availability panels, abstention, explainability and statistical analysis. Results: cohort audit, primary model performance, panel degradation, routing/selective prediction, robustness and subgroup/survey sensitivity. Discussion: negative selector result, case-mix effects, transport limits, clinical interpretation and non-deployment status. Conclusion: bounded development findings only. Supplement: protocol and tuning spaces, full fold and participant results, calibration/DCA, all ablations, SHAP QA, model cards, data dictionaries, TRIPOD+AI crosswalk, PROBAST+AI assessment and exact reproducibility manifests.

Machine-executable development work is complete for the supported paths, including the analyses Block K originally listed as incomplete. Scientifically, the project is a strong development prototype and a prepared draft package, not a submit-ready clinical prediction paper. Current authoritative conference QA verdict: NOT READY, 15 blocking checks and one external-validation warning. `PUBLICATION_READINESS.md` points to the registry-driven canonical audit so a stale root result cannot be mistaken for current evidence.

# 21. FINAL PROJECT STATUS

## Completed and working

- Four validated dataset adapters, audits and deterministic stratified/group splits.
- Five model families, Optuna tuning, cross-fitted calibration, three threshold policies and reloadable bundles.
- Repeated nested development studies for PIDD and grouped Sylhet at the full development budget.
- Full-cohort BRFSS development holdout plus a full-cohort patient-grouped Hospital130 development holdout on its separate readmission endpoint.
- Participant/cluster bootstrap CIs, paired contrasts, Holm correction and decision-curve uncertainty.
- Held-out SHAP, grouping, local explanations, dependence summaries and stability/reconstruction QA.
- Four-dataset 91-row ontology and availability-panel contracts.
- Availability routing, robust comparator, abstention, single/mixed patient research reports.
- Artifact, missing-indicator, panel-training, missingness-stress, selective-prediction, subgroup, leakage and reporting ablation engines; development executions are complete.
- Exact source/data/environment study registry, CI, final preflight/access-receipt safeguards, publication readiness gate, conference development package, and 107 passing tests plus seven subtests.

## Partially completed

- BRFSS has full-development evidence and all supported secondary analyses, but its inspected seed-42 development-test is not final evidence.
- Hospital130 is a technically complete smoke pathway but only supporting evidence and a separate task.
- Ontology mappings are internally validated, not independently clinically reviewed.
- Patient reporting is complete as a research artifact, not a refitted deployment model or UI/API.
- TRIPOD+AI/PROBAST+AI and claim crosswalks exist as drafts but protocol flags remain false pending review/sign-off.
- Source/config/data acquisition reproducibility is strong locally and documented for clean clones; large model/result artifact distribution is still incomplete on GitHub.

## Planned but not implemented/authorized

- frozen statistical protocol and signed final authorization;
- genuinely fresh, authorization-gated final studies under frozen profiles; BRFSS/Hospital holdout runs additionally require concealed manifests and one-way access receipts;
- external, geographic, prospective or temporal validation;
- matched cross-schema validation of automatic environment selection;
- probability fusion/harmonized universal model;
- onset-age/survival model (`onset_age` is explicitly reserved as not implemented);
- clinical workflow/usability/impact study, model monitoring or regulatory deployment.

## Abandoned or superseded

- legacy XGBoost-only/complete-case framing;
- combined BRFSS diabetes/prediabetes endpoint as primary analysis;
- ordinary Sylhet row split;
- small-sample isotonic calibration;
- headline dynamic-model-selection claim;
- automatic mixed-environment selection as default;
- pilot IDs/results as current full-development evidence.

# 22. LIMITATIONS AND SCIENTIFIC CRITIQUE

| Limitation | Status | Consequence / appropriate response |
|---|---|---|
| No external/temporal/prospective validation | Unaddressed | internal performance cannot establish transportability or clinical usefulness |
| PIDD N=768 and population specificity | Partly addressed by repeated nested CV | uncertainty/overfitting remain; results cannot generalize broadly |
| Sylhet N=520, 269 duplicate rows, symptom enrichment | grouping addressed; sampling bias unavoidable | grouped internal scores may still be optimistic for community screening |
| BRFSS self-report, survey nonresponse and unweighted training | weighted sensitivity partially addresses | endpoint is reported diagnosis; population estimates and individual risk may be biased |
| Hospital endpoint mismatch | addressed by hard separation | supporting readmission study cannot validate screening |
| Different labels/populations/prevalence | addressed semantically, not statistically | no pooling; metric comparison across cohorts is descriptive only |
| Missingness mechanisms | fold imputation/stress partially address | MCAR/block simulations do not validate real MNAR behaviour |
| Ontology validity | internal coverage checks only | mappings document judgment; clinical/domain review is needed |
| Panel choice | prespecified/configured but development-informed | panels may not reflect actual clinical workflows/costs |
| No proven router advantage | transparently reported | claim degradation/applicability, not superior switching |
| Threshold 0.5 often inappropriate | alternative development thresholds implemented | no clinically elicited harm ratio or prospective threshold validation |
| Calibration instability | cross-fitted selection and small-N isotonic ban | fold slopes can be unstable; external recalibration likely needed |
| Multiple comparisons | Holm correction implemented | low power and many secondary analyses remain; avoid fishing |
| Repeated development/test inspection | evidence tiers and final lockout address prospectively | full BRFSS seed-42 and Hospital smoke holdouts cannot become final unseen evidence |
| SHAP limitations | scale/additivity/causal warnings implemented | explains model output, not disease mechanism or counterfactual effect |
| Error analysis | confusion counts only | no supported phenotype characterization of FNs/FPs |
| No treatment/benefit data | unaddressed/out of scope | decision support and net benefit remain model-based, not patient-outcome evidence |
| Fairness/subgroups | development subgroup engine exists | small cells and limited protected attributes prevent strong fairness claims |
| Data age/geography | unavoidable in current scope | modern Indian/global deployment is unsupported |
| Reproducibility from GitHub | materially improved but incomplete | exact source/download/hash and environment contracts exist; ignored large models/results still require regeneration or external archive |
| Selective prediction confidence score | implemented but scientifically weak | `2*abs(p-0.5)` selects extreme probabilities, not calibrated epistemic uncertainty; at BRFSS 70% coverage it retained only 24.97% of positive events |

A noteworthy calibration contradiction illustrates why estimands matter: full Sylhet fold-summary CatBoost calibration slope averages about 12.65 because individual fold fits can be unstable, while participant-aggregated slope is near 1.01. Neither should be erased. The former reveals fold-level instability; the latter describes recalibration of aggregated repeated-CV probabilities. A paper must state which is primary and not call the system uniformly “well calibrated” based on one aggregation.

# 23. WHAT THE PROJECT CAN AND CANNOT CLAIM

## Claims we can safely make

- A modular, tested research pipeline was implemented for four diabetes-related cohorts with endpoint-specific models.
- PIDD and grouped Sylhet received full repeated nested **development** evaluation; BRFSS received a full-cohort development holdout evaluation; Hospital130 has smoke holdout evidence only.
- In PIDD development, the five families perform similarly; CatBoost participant AUROC is 0.844 and Brier 0.152, with no corrected universal winner.
- In grouped Sylhet development, internal discrimination is high; CatBoost participant AUROC is 0.970 and Brier 0.061, subject to severe cohort limitations.
- In full BRFSS development, the leading tree models have AUROC about 0.843 and Brier about 0.0915 on 85,872 development-test respondents; none of XGBoost, CatBoost and LightGBM is corrected-significantly superior to the others.
- Fold-fitted preprocessing, group isolation, development-only tuning/calibration/thresholding and participant/cluster inference reduce important leakage risks.
- Naïve Sylhet row splitting demonstrably inflates performance because identical feature profiles cross partitions.
- Prespecified feature removal degrades performance, especially severe/non-lab panels; the framework quantifies and reports this degradation.
- Dynamic model switching and panel-specific retraining did not establish multiplicity-corrected superiority in development.
- The ontology explicitly prevents unsafe equivalence and endpoint pooling; it covers all 91 configured inputs.
- The router can select a supported dataset-native panel or abstain; mixed probabilities are not fused.
- Held-out SHAP consistently ranks Glucose and BMI most strongly in PIDD and Polyuria/Polydipsia in Sylhet, as model associations rather than causes.
- The final repository is a serious development research prototype with a fail-closed publication gate.

## Claims we should NOT make

- **“It diagnoses diabetes.”** It predicts retrospective cohort labels; no clinician/lab confirmation workflow or prospective diagnostic study exists.
- **“Clinically validated/medically accurate.”** No external/prospective validation, impact trial or regulatory assessment exists.
- **“Universal/global/Indian generalisation.”** Datasets are specific, mostly US or small clinical cohorts; there is no Indian validation cohort.
- **“Multiple datasets prove robustness.”** They are separately analysed and have different endpoints/schemas; no cross-dataset transfer test exists.
- **“One universal model handles every patient.”** There are separate cohort experts and only evaluated panels.
- **“The ontology harmonizes the data.”** It documents exact/proxy/non-comparable relations; it does not transform cohorts into one table.
- **“The router finds the best model for any patient.”** It chooses by panel-level development evidence, not individualized counterfactual performance; automatic environment selection is unvalidated.
- **“SHAP finds causal risk factors.”** SHAP attributes model output under observed associations.
- **“The holdout proves real-world validity.”** Internal test separation only reduces development optimism.
- **“0.5 is a clinical cutoff.”** It is a generic fixed threshold and demonstrably poor for Hospital130.
- **“Production-ready/personalized medicine.”** No deployment security, monitoring, human factors, treatment link or prospective safety evidence.
- **“Publication-ready/final results.”** Protocol and final execution are explicitly unlocked; readiness audit fails.

# 24. MOST IMPORTANT RESULTS TO REMEMBER

1. **PIDD full development:** CatBoost participant AUROC 0.8444 and Brier 0.1517. It is numerically strongest on those metrics, but no corrected superiority is established. Source: `pidd_development_072cd2104089/participant_*`.
2. **PIDD false negatives at 0.5:** CatBoost misses 110/268 positives; Random Forest/LightGBM miss 107. This shows why a generic 0.5 threshold is not a clinical screening policy.
3. **Sylhet full grouped development:** CatBoost participant AUROC 0.9696, AP 0.9838, Brier 0.0609; internal performance is high but not population validation.
4. **Sylhet duplicate control:** 269 duplicate rows form 251 feature-profile groups. Invalid row splitting created 263 overlaps, AUROC 0.9735 vs grouped 0.9574 and Brier 0.0565 vs 0.0798 in the leakage demonstration.
5. **BRFSS full development:** N=85,872 development-test respondents/11,451 positives. XGBoost AUROC 0.8430, AP 0.4436, Brier 0.09150; CatBoost and LightGBM are essentially tied and no leading-three corrected comparison establishes a winner. This remains inspected development evidence.
6. **Hospital smoke:** XGBoost AUROC 0.6589, AP 0.2065, Brier 0.0973. At 0.5 it produced only 4 TP and 1,135 FN, demonstrating threshold/prevalence dependence, not a clinical result.
7. **PIDD SHAP:** Glucose #1 and BMI #2 in all five families; higher values generally raise raw model output. BRFSS full-development SHAP most consistently emphasizes GenHlth, HighBP, Age, BMI and HighChol. Both are non-causal, within-cohort findings.
8. **Sylhet SHAP:** Polyuria/Polydipsia dominate; group-aware validation is essential because symptom profiles repeat.
9. **Availability degradation:** PIDD full router AUROC/Brier ≈0.843/0.152, glucose+age ≈0.809/0.166, non-lab ≈0.756/0.186. Less information predictably weakens evidence.
10. **No dynamic-selection win:** router vs robust fixed model, selector alternatives and repeated-CV panel-specific training show no Holm-corrected advantage. BRFSS full-versus-reduced degradation intervals exclude zero, but none of 80 Holm-adjusted p-values is below 0.05 at 500 bootstraps. This negative/precision-limited result narrows the novelty claim.
11. **Missingness stress:** at 75% dropout, PIDD Brier rises to roughly 0.209–0.213 and named-panel coverage falls to 4–7%; Sylhet Brier roughly 0.246–0.295 with 4–6% coverage.
12. **Selective prediction trade-off:** at 70% nominal coverage, PIDD Brier improves about 0.152→0.110 but positive-event coverage falls to 55.6%; Sylhet 0.062→0.025 with positive-event coverage 76.9%. For the BRFSS full panel, 60,111/85,872 respondents are accepted, Brier improves to 0.0430, but only 2,859/11,451 positives remain (24.97% event coverage) and accepted prevalence falls to 4.76%. The implemented extremeness score is not a validated uncertainty measure.
13. **BRFSS survey sensitivity:** weighted prevalence is 10.95% versus 13.34% unweighted; weighted XGBoost AUROC/AP/Brier are 0.8707/0.4480/0.07517. This shows survey design changes the estimand, not that population validity is proven.
14. **Ontology:** 91/91 configured features covered; only 19 explicit shared/related rows and 72 dataset-specific. “Multi-dataset” is not “interchangeable.”
15. **Readiness:** 100 tests plus seven subtests pass, yet the current publication audit is NOT READY with 15 blockers and one warning. Software correctness and final scientific evidence are different gates.

# 25. PROFESSOR / VIVA QUESTIONS AND PROJECT-SPECIFIC ANSWERS

## Easy

1. **What exactly did you build?** A tested research pipeline that trains and evaluates separate calibrated models for four diabetes-related datasets, measures performance under prespecified missing-feature panels, produces held-out SHAP explanations and provenance-rich patient research outputs, and abstains when no validated schema applies.
2. **Why T2DM?** It is clinically important and supports preventive follow-up, while public datasets make retrospective ML research feasible. The project does not claim prevention or diagnosis; it studies prediction methodology.
3. **Which datasets?** PIDD (768), Sylhet (520), BRFSS 2015 (429,360 retained) and Hospital130 (99,343 retained encounters). Hospital130 predicts 30-day readmission, not diabetes.
4. **Which models?** Logistic Regression, Random Forest, XGBoost, LightGBM and CatBoost. The router candidate bank uses the four tree families.
5. **Why include Logistic Regression?** It is an interpretable, strong linear baseline. It remained competitive, preventing a misleading claim that complex boosting automatically wins.
6. **Why XGBoost?** It handles nonlinear/tabular relationships and was central to the original project, but the final system treats it as one candidate rather than the project itself.
7. **What is your best PIDD result?** Numerically CatBoost participant AUROC 0.8444 and Brier 0.1517 in full development; differences were not proven significant after correction.
8. **What is your best Sylhet result?** CatBoost participant AUROC 0.9696, AP 0.9838 and Brier 0.0609 under duplicate-profile-grouped full development.
9. **What is calibration?** Agreement between predicted probabilities and observed frequencies. The project selects identity/sigmoid/isotonic using cross-fitted development Brier/log loss, with isotonic prohibited below N=1,000.
10. **Why SHAP?** To attribute each held-out model output globally and locally, verify important features and produce patient explanations. It explains the model, not disease causality.
11. **What features mattered in PIDD?** Glucose and BMI were consistently first and second; Age and pedigree score were commonly next.
12. **What is the final output for a patient?** A research probability summary, threshold agreement, selected panel/model/calibrator counts, SHAP factor directions, cohort context, provenance, applicability warnings and disclaimer—or abstention.

## Medium

13. **Why multiple datasets?** To study different evidence environments and implement a reusable evaluation contract, not to claim they are interchangeable.
14. **Why not merge them?** Their labels, populations, units and features differ. Hospital130 even has a different endpoint. A merged label would be scientifically incoherent without a validated harmonization design.
15. **What is the feature ontology?** A 91-row semantic dictionary that labels exact, binned, proxy, non-comparable and dataset-specific features and enforces endpoint-first constraints.
16. **How do you know two features mean the same thing?** The code does not infer this from names. Mappings are manually declared with measurement scales/relations and validated against configured fields; independent clinical review is still needed.
17. **Does ontology mapping convert BRFSS Age to PIDD Age?** No. It records that one is a group code and one years. Runtime patient input remains dataset-native.
18. **What is availability routing?** Selection of the largest prespecified panel fully supported by the supplied fields, followed by the model family chosen for that panel from development Brier/log loss/AP.
19. **Why not just impute every missing patient feature?** Fold imputation handles missing values within an evaluated schema; it does not justify an arbitrary pattern never evaluated. Panels make applicability explicit and allow abstention.
20. **Why not one universal model?** There is no shared table/label or matched cohort. Separate experts preserve provenance and prevent false probability fusion.
21. **What if only Glucose and Age are supplied?** The PIDD router uses `minimal_glucose_age`; only Age yields no supported panel and abstains.
22. **Can several models be compatible?** Several families are evaluated, but each panel's selected family is determined from development evidence. Multiple dataset environments require an explicit preferred environment or safe abstention.
23. **How did you avoid preprocessing leakage?** All medians, scaling and category vocabularies are fitted inside training folds. Outer/test rows only receive transforms. Tuning/calibration/threshold selection use development predictions.
24. **Why group Sylhet?** 269 rows repeat predictor profiles. Naïve row splits allow identical vectors in train and validation and inflated AUROC/Brier in the explicit leakage demonstration.
25. **Why group Hospital130?** One patient can have multiple encounters; patient overlap would leak patient-specific history and underestimate uncertainty.
26. **Did you use SMOTE?** No. The pipeline uses model-specific class weighting options and reports threshold-free/imbalance-aware metrics.
27. **How were hyperparameters selected?** Seeded Optuna TPE inner CV optimized average precision. Choices differ per outer fold/model/dataset.
28. **What thresholds?** Fixed 0.5, development-Youden, and development threshold targeting at least 80% sensitivity. No threshold is clinically validated.
29. **Why AP in addition to AUROC?** In low-prevalence BRFSS/Hospital tasks, AP exposes positive retrieval/precision more directly; AUROC can look respectable despite low PPV.
30. **What is the holdout engine?** A manifest-driven development/test workflow where tuning, calibrator, thresholds and champion are fixed using development CV before test access, with grouping and authorization controls.
31. **Is an 80/20 split enough?** No. Its credibility depends on group protection, no repeated test iteration, frozen choices, adequate sample and representative external data. The engine adds discipline, but even the full BRFSS development holdout is not final because its outcomes were already inspected and the protocol was not frozen.
32. **Why are false negatives important?** Missing a positive may delay follow-up. At PIDD 0.5, models miss roughly 107–119/268 positives. Lower thresholds trade fewer FNs for more FPs.

## Difficult

33. **Does high Sylhet AUROC prove generalisation?** No. It is internal grouped performance in a small symptom-enriched cohort with many repeated profiles. It requires independent external validation.
34. **Why are fold-summary and participant metrics different?** Fold summary averages 25 validation-fold estimands; participant analysis first averages five held-out repeat probabilities per person and then evaluates 520/768 unique units. They answer related but non-identical questions.
35. **Why can calibration slope be 12.65 in folds but near 1 aggregated?** Small fold calibration regressions can be unstable/extreme. Averaged repeated-CV probabilities have different variance and yield a different participant-level recalibration fit. Both estimands must be labelled.
36. **Did routing outperform a fixed model?** Not after Holm correction. The router's valid value is evaluated fallback/degradation/provenance/abstention, not proven predictive superiority.
37. **Does feature count explain panel degradation?** Only partly in PIDD (R² roughly 0.18 for Brier and 0.08 for AP); strongly in Sylhet (about 0.89–0.91) but based on only five panels, so composition still matters and inference is weak.
38. **Can SHAP values be averaged across models?** Not in raw magnitude: LR is log-odds, RF probability and boosted trees margins. Patient reporting normalizes within fold and summarizes ranks/directions instead.
39. **Does SHAP show that glucose causes diabetes?** No. It shows higher Glucose is associated with higher model output in held-out PIDD rows. Confounding, selection and measurement processes remain.
40. **What does selective prediction show?** Rejecting uncertain estimates can improve metrics among accepted cases, but coverage—especially positive-event coverage—falls. It is not automatically safer.
41. **Does the survey-weighted BRFSS analysis validate population risk?** No. It tests sensitivity to weights/PSU resampling and shows prevalence/performance can shift. The fitted model is still unweighted and the endpoint self-reported.
42. **Can this generalise to India?** Not from present evidence. Sylhet is Bangladesh-based but small/clinical; geographic proximity is not Indian validation. A representative Indian cohort and local recalibration/impact study are required.
43. **What is the biggest reproducibility flaw?** Model bundles and underlying result CSVs are Git-ignored and no immutable external artifact archive is configured. Raw-data acquisition and exact hashes are now specified, so a fresh clone can rebuild development evidence, but cannot instantly inspect or byte-for-byte restore the local evidence state.
44. **What is the strongest contribution?** Endpoint-safe, availability-aware calibrated degradation evaluation with provenance and abstention across incompatible diabetes cohorts.
45. **What negative result should you volunteer?** Dynamic model selection and panel-specific retraining did not show multiplicity-corrected gains. This improved the scientific framing rather than invalidating the system.
46. **What would you do with another semester?** Complete the literature/novelty and clinical-threshold reviews, freeze the protocol, independently review ontology/panels, acquire an external Indian/temporal cohort, run only newly authorized final analyses, and archive every final artifact immutably. BRFSS computation is no longer the main gap; final evidence validity is.
47. **How would you clinically validate it?** Retrospective external validation with prespecified inclusion/endpoint, calibration and subgroup/DCA; silent prospective validation; clinician workflow/usability study; prospective impact trial; monitoring and governance before any action support.
48. **What ethical risks exist?** Biased sampling, false reassurance from FNs, unnecessary follow-up from FPs, opacity, misuse as diagnosis, privacy leakage, subgroup harm and automation bias. Abstention/disclaimers help but do not remove them.
49. **Is the project complete?** The minor-project implementation and development analysis are complete and on GitHub. A final locked publication study and clinical validation are explicitly not complete.
50. **Why should a professor trust the result?** They should trust the traceable development result within its scope because preprocessing/splits/artifacts/tests are controlled and negative results disclosed; they should not extend trust to external clinical claims absent validation and committed evidence.

# 26. EXPLANATIONS AT DIFFERENT DEPTHS

## A. 30-second explanation

I built a diabetes-related ML research system, not just one classifier. It evaluates five models separately on PIDD, Sylhet and BRFSS, keeps Hospital readmission separate, calibrates probabilities, checks leakage and explains predictions with SHAP. Its key feature is availability routing: when some patient fields are missing, it uses only a feature panel that was actually evaluated, or abstains. The development results are strong internally, but it is not a diagnostic or clinically validated tool.

## B. 1-minute professor explanation — “What exactly did you build?”

I built an end-to-end, configuration-driven Python research pipeline for heterogeneous diabetes datasets. Each dataset has an explicit endpoint, feature schema and leakage-safe split: repeated nested CV for PIDD, duplicate-profile-grouped nested CV for Sylhet, a stratified holdout for BRFSS and a patient-grouped holdout for Hospital130 readmission. Within training folds it imputes/encodes, tunes five model families, selects calibration and thresholds, evaluates discrimination, probability accuracy, calibration, decision utility and paired uncertainty, and saves reloadable bundles. A semantic ontology prevents false equivalence across datasets. Prespecified feature panels are evaluated so an inference router can select a supported panel or abstain. Held-out SHAP and a patient-report layer add provenance and explanations. The strongest finding is not that one algorithm wins; it is that performance degradation and applicability can be measured safely under incomplete features. Final clinical/publication validation remains pending.

## C. 5-minute walkthrough

Start with the problem: four datasets called “diabetes” do not represent one task. PIDD has labs, Sylhet symptoms, BRFSS self-reported survey status, and Hospital130 predicts readmission. The project first encodes those distinctions in dataset and ontology contracts. It then creates deterministic split manifests: ordinary stratification for PIDD, profile groups for duplicated Sylhet rows, and patient grouping for Hospital encounters.

Inside every training partition, numeric values are median-imputed with missing indicators; Logistic Regression is scaled; categoricals are constant-imputed and one-hot encoded. Five models are tuned with inner CV on AP. Inner out-of-fold probabilities choose the calibrator and development thresholds. Outer folds or the holdout are evaluated once, with AUROC, AP, Brier, log loss, calibration, confusion metrics, decision curves and participant/cluster bootstrap comparisons.

The full development results are about AUROC 0.84 for PIDD, 0.97 for grouped Sylhet and 0.843 for BRFSS, but no single universal model winner exists. A deliberately invalid Sylhet row split inflates performance, demonstrating why grouping matters. SHAP shows Glucose/BMI dominate PIDD, Polyuria/Polydipsia dominate Sylhet, and general health/high blood pressure/age/BMI/cholesterol dominate BRFSS, without causal claims.

The distinctive system component is availability routing. Each dataset has panels from full features down to two-field severe-degradation panels. Models are evaluated with unavailable fields masked. At inference, the router selects the largest supported evaluated panel, applies its saved model/calibrator/threshold and reports provenance; if none applies it abstains. Dynamic switching did not beat a fixed comparator significantly, so the contribution is degradation/applicability rather than a “smart router wins” claim.

The patient report aggregates several outer-fold research models, shows probability spread, threshold agreement and normalized SHAP factors. Mixed dataset input is namespaced and never fused; multiple eligible environments cause default abstention unless explicitly selected. Finally, a publication gate makes it impossible to call smoke/development results final: protocol freeze, final authorization and external validation remain absent.

## D. Deep technical explanation

The system is a manifest-driven supervised-learning experimentation framework. A `DatasetBundle` carries dataset-native X/y, stable row IDs, optional groups and a registry contract. Deterministic adapters perform outcome-blind parsing and cohort exclusions. `ColumnTransformer` instances are cloned inside nested loops, preventing global estimation. Seeded Optuna optimizes AP with stratified or group-aware inner splits. Cross-fitted candidate calibration is selected lexicographically by Brier/log loss with an isotonic eligibility floor. Operating thresholds are learned from the same development OOF layer, never the evaluation labels.

Small cohorts produce repeated outer OOF predictions and unique-participant primary inference; Sylhet resamples profile groups. Large cohorts use immutable holdout roles, development OOF selection, a full-development refit and individual/patient-cluster uncertainty. Paired comparisons reuse identical evaluation units and apply metric-wise Holm adjustment. SHAP is computed only on outer/test rows and checked against raw estimator output; transformed components are grouped to source fields.

Availability studies do not retrain by default: full-schema models are evaluated after deterministic feature-panel masking, matching inference semantics. Panel-specific retraining is a separate controlled ablation. Scenario selection is development-Brier-first. Runtime compatibility is subset inclusion, followed by maximum panel cardinality and stored model selection. Mixed routing adds an endpoint/environment gate rather than treating compatibility as validity. Governance metadata differentiates smoke, pilot, development and final-locked tiers; the final guard validates protocol flags, authorization and concealed-manifest checksums before a non-smoke holdout can execute.

# 27. DEMO FLOW

## 2-minute emergency demo

1. Open `README.md` and say: “This is one pipeline for separate cohort experts, not one merged diabetes model.”
2. Open `config/datasets.yaml`; point to the three screening endpoints and Hospital readmission separation.
3. Open `config/availability_scenarios.yaml`; show PIDD full, routine and glucose+age panels.
4. Show `conference_package/generated/development_model_performance.csv` (or the performance table in `Conference_Manuscript_Development_Draft.md`) and quote PIDD participant 0.844 AUROC/0.152 Brier, Sylhet participant 0.970/0.061, and BRFSS XGBoost 0.843/0.0915, explicitly calling all of them development results and noting their different estimands.
5. Show the synthetic patient JSON and retained report; explain panel selection and fold spread, then state “research demonstration, not diagnosis.”
6. Finish with `conference_package/qa/Publication_Readiness_Audit.md`: 100 tests plus seven subtests can pass while the scientific gate remains NOT READY. Do not use the stale root audit as the current blocker count.

Do not spend the two minutes scrolling model code, every metric, Hospital features or every plot.

## 10-minute proper demo

1. **Problem (1 min):** README + four dataset endpoints. Explain why merging is invalid.
2. **Data discipline (1 min):** `BLOCK_A_REPORT.md` audit table; emphasize PIDD zeros, Sylhet groups and Hospital patients.
3. **Pipeline (1.5 min):** architecture diagram in this document; show `runner.py` and `holdout_runner.py` entry functions.
4. **Evaluation (1.5 min):** participant PIDD/Sylhet table plus full BRFSS development table; explain AP/Brier/calibration, different estimands and no universal model winner. Mention Hospital only as smoke/readmission support.
5. **Ontology (1 min):** `config/feature_ontology.yaml`; contrast PIDD BloodPressure with BRFSS HighBP and PIDD Insulin with Hospital insulin.
6. **Routing (1.5 min):** `availability_scenarios.yaml` + `routing/inference.py`; walk Glucose+Age and unsupported Age-only examples. State negative dynamic-selection result.
7. **Patient/SHAP (1.5 min):** synthetic PIDD report and SHAP bar/beeswarm; explain raw-scale direction and non-causality.
8. **Scientific honesty (1 min):** readiness audit; list no final locked/external validation and strongest defensible novelty.

Avoid showing raw CSVs, Optuna logs, every SHAP plot, cache files or legacy headline scores. The best demo story is semantic safety → leakage control → calibrated evidence → availability degradation → abstention → honest limitations.

# 28. REPRODUCING THE PROJECT

## What a clean clone needs first

Clone the repository, use Python 3.11+ (the audited environment is Python 3.12), then obtain the exact raw files and place them at:

- `data/raw/pidd.csv` (SHA-256 `6bfe5d0f...`);
- `data/raw/sylhet.csv` (`7889d9d0...`);
- `data/raw/brfss.csv` (`a7d3380a...`);
- `data/raw/hospital130.csv` (`0689e7ec...`).

Exact sources, download URLs, archive members, known license/DOI information and full hashes are in `config/data_sources.yaml` and `docs/DATA_ACQUISITION.md`. PIDD is deterministically reconstructed from OpenML dataset 37 because the historical UCI URL is unavailable; its original licensing record remains less explicit than the current UCI datasets. Do not proceed if hashes differ without documenting a new data version.

## Environment and verification

```bash
python3.12 -m venv .venv-pipeline
source .venv-pipeline/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python scripts/verify_environment.py
python scripts/acquire_data.py --dataset all
export MPLCONFIGDIR=outputs/.matplotlib
python -m pytest -q
python -m diabetes_pipeline.cli --help
```

## Audits, manifests and ontology

```bash
python -m diabetes_pipeline.cli block-a --dataset all --seed 42
python -m diabetes_pipeline.cli research-audit --seed 42
python -m diabetes_pipeline.cli feature-map
python -m diabetes_pipeline.cli test-concealment --dataset brfss --seed 42
python -m diabetes_pipeline.cli test-concealment --dataset hospital130 --seed 42
```

The concealment commands test format on known development splits; they do not create final evidence.

## Safe execution-scale workflow

```bash
python -m diabetes_pipeline.cli benchmark --dataset pidd --profile smoke
python -m diabetes_pipeline.cli benchmark --dataset pidd --profile development_pilot
python -m diabetes_pipeline.cli benchmark-holdout --dataset brfss --profile smoke
python -m diabetes_pipeline.cli benchmark-holdout --dataset hospital130 --profile smoke
```

Use the emitted study directory in subsequent commands:

```bash
python -m diabetes_pipeline.cli explain --dataset pidd --study-dir <STUDY_DIR>
python -m diabetes_pipeline.cli evaluate-routing --dataset pidd --study-dir <STUDY_DIR>
python -m diabetes_pipeline.cli matched-panel-contrasts --study-dir <STUDY_DIR>
python -m diabetes_pipeline.cli artifact-ablations --study-dir <STUDY_DIR>
python -m diabetes_pipeline.cli selective-prediction --study-dir <STUDY_DIR>
python -m diabetes_pipeline.cli subgroup-analysis --study-dir <STUDY_DIR>
python -m diabetes_pipeline.cli reporting-ablations --study-dir <STUDY_DIR>
```

Other justified commands and options are in `docs/RUNBOOK.md`, including missing indicators, panel training, missingness stress, leakage demonstration and holdout SHAP. For patient inference after routing:

```bash
python -m diabetes_pipeline.cli patient-result \
  --dataset pidd \
  --routing-dir <STUDY_DIR>/availability_routing \
  --patient-file examples/pidd_patient_synthetic.json \
  --format markdown
```

There is no notebook order. Do **not** run or invent a final profile: `config/publication_protocol.yaml` deliberately blocks it until protocol freeze and signed authorization. Exact historical result reproduction additionally needs the ignored study artifacts or substantial compute and the matching source revision/config. Generated conference tables on GitHub are insufficient to regenerate underlying probabilities.

For exact authoritative development reproduction rather than a short demonstration, use the `development` PIDD/Sylhet commands and the full BRFSS command in `docs/REPRODUCIBILITY.md`; expect substantial compute. Always run `scripts/final_preflight.py --dataset <name>` only as a read-only check. Its expected current result is denial without outcome access.

# 29. CODE QUALITY / RESEARCH ENGINEERING REVIEW

## Overall assessment

For a university minor project, structure and methodological care are unusually strong: clear package boundaries, declarative configuration, type hints/docstrings, deterministic IDs/hashes, testable pure functions, fold-safe pipelines, reload checks, explicit negative evidence and governance. Error handling commonly fails closed for unsupported datasets/panels, non-finite/out-of-range patient values, group overlap, SHAP reconstruction and final authorization.

Weaknesses include ignored primary artifacts; no approved code license or
immutable external artifact archive; a few old absolute paths in generated
metadata; potentially expensive monolithic orchestration; no formal static
typing/coverage report; and no independent data custody. The repository now has
a CPU container recipe, canonical audit runner/pointer, explicit development-test
labels, and a hash-verified external-archive manifest, but the container cannot
be runtime-verified on this host and no external archive has been uploaded. Some
robustness/ablation engines support repeated-CV studies only, so “all analyses
completed” must be qualified by dataset/runner support.

## Improvements for the minor-project handoff

1. Commit the audited hardening/current documentation as one reviewed checkpoint so the source of truth is no longer a dirty working tree.
2. Obtain independent review of the canonical publication-readiness audit and
   artifact manifest before release.
3. Upload the hash manifest and required artifacts to an approved immutable
   archive without placing large outputs in Git.
4. Approve a software license and replace the explicit no-license status.
5. Validate the container on a Docker-capable host and record platform details.
6. Add formal typing or coverage only if it offers maintainable value beyond the
   current test and configuration checks.

## Before serious publication/open source

Extend CI across supported Python versions; add a container, SPDX license/citation file, immutable release tags/DOIs, off-device artifact store with checksums, data cards/model cards, code coverage/static typing/linting, independent statistical and ontology review, documented compute/hardware, and final protocol registration. Separate development and final data custody.

## Before anything resembling clinical deployment

Acquire representative external/prospective data; define intended use/users and clinical reference standard; validate calibration/thresholds/subgroups/shift; conduct silent and impact studies; establish privacy/security/consent, audit logs, human override, abstention escalation, monitoring/recalibration/rollback, quality management, regulatory review and incident response. Replace CV ensembles with a frozen deployment model and independent validation. The current repository should not be deployed clinically.

# 30. CONTRADICTION / CONSISTENCY AUDIT

| Sources in tension | Why they differ | Authority/action |
|---|---|---|
| Authoritative study registry names local studies; Git tracks no large study outputs | `.gitignore` excludes outputs by design | registry/hashes identify evidence but regeneration/archive is required after clone |
| README/progress pilot IDs vs later full-development IDs | pilots preceded Aug-24 full runs | `Execution_Status.md` + current conference tables/full studies supersede |
| Block K says ablations/selective/subgroups incomplete; Aug-24 Execution Status says machine work complete | later commits finished them; flags await human review | later status is implementation truth; flags remain governance truth |
| Top-level BRFSS audit previously reported 437,050/combined endpoint; current loader reports 429,360 diagnosed-only | endpoint/loader revision and stale audit | current `datasets.yaml`, loader and hashed audit authoritative |
| Top-level Hospital audit may say 101,766; current cohort 99,343 | death/hospice exclusion added | current loader/config/hashed audit authoritative |
| Legacy metrics much higher/different | old complete-case endpoints/splits/XGBoost-only | historical only; never compare as model progress |
| `experiment_metadata.json` absolute XGBoost paths | artifacts generated before move | hashes/study IDs matter; paths are stale provenance |
| No `PUBLICATION_PIPELINE.md` though planning language cites it | actual plan split across roadmap/protocol/research docs | cite real paths; create index if desired |
| “Calibrated” narrative vs Sylhet fold slope 12.65 and participant slope ~1.01 | different unstable/aggregated estimands | report both and define primary estimand |
| Earlier conference Table 1/2 fold means vs protocol participant/profile-level primary inference | the earlier draft summarized outer evaluations, while the inferential unit is the aggregated person/profile | resolved in the current package: participant/profile estimates and CIs are primary; fold summaries are secondary |
| Block J describes priority auto-selection; Block K/final code defaults to abstain | safety hardening after Block J | final code/protocol authoritative |
| Patient synthetic probability 66.05% vs mixed example PIDD ~55.16% | different input JSON, pilot bundles and routing context | both demos only; label exact artifact/source |
| `pyproject` description says diabetes screening while Hospital supported | primary topic vs secondary endpoint | clarify package description |
| Historical root readiness audit reported 16 blockers/BRFSS smoke; conference QA reported 15/full BRFSS development | the root audit was not regenerated after the authoritative BRFSS study | resolved: `PUBLICATION_READINESS.md` points to the registry-driven conference QA audit; historical audits remain provenance only |
| BRFSS canonical artifact rows previously said `locked_test`; study metadata said full development/non-final | artifacts predated the explicit development/final role split | resolved in current canonical CSV/JSON artifacts by migration to `development_test`; historical prose is unchanged |
| Earlier context used base commit `9b15b26`; this audit uses `99ff8fa` plus intentional changes | the repository advanced while development work remained uncommitted | the header now identifies the exact base and dirty working-tree status; create a reviewed checkpoint before external handoff |

# 31. THINGS I MAY HAVE MISUNDERSTOOD ABOUT MY OWN PROJECT

1. **“Completed” has two meanings.** The minor-project software/development analysis is complete; the protocol-gated final paper experiment is deliberately incomplete.
2. **It is not primarily an XGBoost project anymore.** Five families are evaluated, and no universal winner exists.
3. **Multi-dataset does not mean pooled or cross-dataset.** The commonality is pipeline/semantic governance; models remain separate.
4. **Availability routing is not individualized oracle selection.** It selects a pre-evaluated panel/model using population development performance.
5. **Missing values and missing concepts differ.** An imputer can fill a missing value within a known schema; it cannot turn BRFSS HighBP into PIDD diastolic pressure.
6. **The ontology is a warning system, not a harmonizer.** It records relationships and prohibitions; patient inference does not call it to translate fields.
7. **The mixed router does not combine evidence.** It uses one explicitly selected cohort expert or abstains; candidate probabilities are audit-only.
8. **Hospital130 is not another diabetes classifier.** It predicts 30-day readmission among encounters involving diabetes.
9. **A high AUROC is not a useful threshold.** Hospital demonstrates that 0.5 can yield nearly zero sensitivity despite AUROC ~0.66.
10. **High Sylhet performance is not necessarily “better data/model.”** Spectrum enrichment and repeated profiles make the task different/easier; grouping reduces but does not erase this.
11. **Calibration is not one number.** Fold, pooled and participant aggregation give different slopes; deployment populations may require recalibration.
12. **SHAP direction is relative to a model baseline.** It is neither a clinical cutoff nor causal explanation.
13. **Fold probability spread is not confidence.** The patient report correctly calls it model-fold variability.
14. **A protected internal holdout is not external validity.** It controls iteration bias inside one cohort only.
15. **Abstention can hide events.** Better metrics among accepted cases must be reported alongside positive-event coverage.
16. **No significant model difference does not prove equivalence.** It means the analysis did not establish a difference under its power/multiplicity design.
17. **Tests passing does not make claims publishable.** The readiness gate separates software correctness from protocol/evidence/reporting validity.
18. **GitHub is authoritative for code but incomplete for artifacts.** Most raw data, models and results are local ignored state.

# PROJECT MEMORY — COPY THIS INTO ANOTHER CHATGPT

## Project identity and objective

This is Pranav Prabhu's completed university Minor Project on Type 2 Diabetes Mellitus prediction, implemented in the repository `OppositeExpert/T2DM`. The audited workspace is dated 30 August 2026 and is based on `main`/`origin/main` commit `99ff8fa`, with intentional uncommitted Hospital130, registry, release, documentation, CI, and conference-package changes; do not pretend that one Git revision captures the whole state. The implementation is a Python research prototype for **calibrated, explainable and availability-aware evaluation across heterogeneous diabetes-related datasets**. It is not simply an XGBoost classifier and is not a clinical diagnostic tool.

The final research problem is: how can separate cohort-specific diabetes models preserve endpoint/feature semantics, avoid leakage, quantify discrimination/calibration/utility degradation when only prespecified feature panels are available, route a dataset-native patient input to an evaluated panel/model, and abstain when no scientifically supported route exists? The strongest defensible contribution is an endpoint-safe, provenance-preserving framework for calibrated feature-availability degradation and abstention across incompatible diabetes-screening cohorts. Dynamic model switching is a secondary negative result.

Three datasets have related but non-identical diabetes-screening/status endpoints: PIDD, Sylhet and BRFSS. Hospital130 is a strictly separate 30-day readmission endpoint among hospital encounters involving diabetes. The system never pools these outcomes or averages their probabilities. It does not diagnose, predict onset age, prescribe treatment, prove clinical usefulness, provide external validation, or implement a universal model.

## Final architecture and data flow

Raw dataset-native CSVs are loaded and validated by `src/diabetes_pipeline/data/loaders.py` and `validators.py` using `config/datasets.yaml`. Stable row/group IDs feed audits and deterministic split manifests in `data/manifests.py`, `data/research_audit.py`, and `splitting/strategies.py`. PIDD uses repeated nested stratified CV; Sylhet uses repeated nested stratified-group CV based on identical feature profiles; BRFSS uses a stratified 80/20 holdout with development CV; Hospital130 uses patient-grouped holdout and development CV.

Inside training partitions, `preprocessing/builders.py` median-imputes numeric fields with missing indicators, scales only Logistic Regression, and constant-imputes/one-hot-encodes categoricals. `models/registry.py` creates Logistic Regression, Random Forest, XGBoost, LightGBM and CatBoost plus Optuna search spaces. `training/tuning.py` performs seeded inner-CV AP optimization. Inner out-of-fold predictions choose identity/sigmoid/isotonic calibration by Brier then log loss; isotonic is ineligible when calibration N<1,000. Fixed 0.5, development-Youden and development ≥0.80-sensitivity thresholds are learned without outer/test labels.

`runner.py` executes PIDD/Sylhet nested studies. `holdout_runner.py` completes all BRFSS/Hospital tuning/calibration/threshold/champion choices from development data before test access. `evaluation/*` calculates metrics, bootstrap uncertainty, paired comparisons with Holm correction, decision curves and ablations. `artifacts/bundles.py` stores preprocessor+estimator+calibrator+threshold+feature/provenance metadata in joblib bundles. `explainability/*` creates held-out SHAP evidence. `routing/*` evaluates prespecified missing-feature panels and performs inference. `reporting/patient_results.py`, `mixed_patient_results.py` and `publication_readiness.py` create research reports and enforce scientific claim gates.

The active package is `src/diabetes_pipeline`. The CLI is `python -m diabetes_pipeline.cli` or installed `diabetes-pipeline`. There are no Jupyter notebooks. The audited code has 107 passing tests plus seven adapter subtests; three warnings are third-party SHAP/Matplotlib pending deprecations.

## Development history

- **Legacy/pre-Block:** an XGBoost-oriented multi-dataset project used simpler preprocessing/evaluation and a combined diabetes/prediabetes BRFSS complete-case cohort. It is backed up outside the final repository and is historical.
- **Block A:** created dataset contracts, current cohorts, audits, hashes, group identities and deterministic leakage-aware splits. It changed BRFSS to diagnosed-diabetes target-valid records with missing predictors retained.
- **Block B:** PIDD smoke execution existed but has no standalone report; it proved the path, not performance.
- **Block C:** five-model PIDD pilot added nested tuning, calibration, thresholds, bootstraps, paired comparisons and reloadable bundles. Models were close, so “XGBoost wins” became indefensible.
- **Block D:** held-out PIDD SHAP added global/local explanations, reconstruction and fold stability. Missing-Insulin importance motivated availability work.
- **Block E:** grouped Sylhet pilot addressed 269 duplicate rows/251 feature profiles and added a small-sample isotonic ban after unstable probabilities.
- **Block F:** PIDD availability panels/router evaluated masked feature environments. Dynamic switching did not significantly beat robust fixed models.
- **Block G:** patient research result added range/schema validation, fold probability spread, thresholds, SHAP factors, cohort context, provenance and abstention.
- **Block H:** separate large-cohort holdout engine added BRFSS and patient-grouped Hospital130, with development-only choice locking before test access.
- **Block I:** 91-row feature/endpoint ontology documented direct, binned, proxy, non-comparable and dataset-specific semantics.
- **Block J:** routing expanded across four datasets; namespaced mixed input and reserved `onset_age: not_implemented` were added.
- **Block K:** claim control made automatic mixed-environment selection opt-in/experimental, made default multiple-environment behaviour abstain, narrowed novelty, and added publication readiness.
- **After Block K:** participant-level inference, DCA uncertainty, matched panels, ablations, missingness stress, selective prediction, subgroups, leakage demonstrations, resumable checkpoints and a conference development package were completed; then the full 429,360-row BRFSS development study, survey sensitivity, BRFSS routing/SHAP/secondary analyses, exact environment/data acquisition, CI, study registry, bundle verification and stronger final authorization/access receipts were added. Human review, freeze and final run remain blocked.

## Datasets

**PIDD/Pima Indians Diabetes Database:** local `data/raw/pidd.csv`, 768 rows, eight predictors plus `Outcome`; 268 positive/500 negative, prevalence 34.90%. Predictors: Pregnancies count 0–17; Glucose 44–199 after 5 zero sentinels become missing; diastolic BloodPressure 24–122 after 35 zeros missing; SkinThickness 7–99 after 227 zeros missing; Insulin 14–846 after 374 zeros missing; BMI 18.2–67.1 kg/m² after 11 zeros missing; DiabetesPedigreeFunction 0.078–2.420; Age 21–81 years. Used for repeated nested development, SHAP, routing, patient demo and ablations. `config/data_sources.yaml` records exact reconstruction from OpenML dataset 37 because the historical UCI URL is unavailable. Population-specific and small.

**Sylhet Early Stage Diabetes Risk Prediction:** UCI source; `data/raw/sylhet.csv`; 520 rows; 320 positive/200 negative, prevalence 61.54%; 16 inputs plus class. Age 16–90; Gender Male=1/Female=0; fourteen Yes/No→1/0 symptoms/indicators: Polyuria, Polydipsia, sudden weight loss, weakness, Polyphagia, Genital thrush, visual blurring, Itching, Irritability, delayed healing, partial paresis, muscle stiffness, Alopecia, Obesity. No missing values. It has 251 unique feature profiles and 269 duplicate rows (largest group 16); identical profiles must stay together. Used for grouped nested development, SHAP, routing and ablations. Symptom-enriched/high-prevalence cohort limits population generalisation.

**BRFSS 2015:** CDC survey; raw `data/raw/brfss.csv` has 441,456 rows/330 columns. Current loader retains 429,360 target-valid records, 57,256 positive/372,104 negative, prevalence 13.34%. Endpoint is self-reported diagnosed diabetes: raw DIABETE3 1 positive, 3 negative; pregnancy-only, prediabetes/borderline, unknown/refused/missing codes 2/4/7/9 excluded. Twenty-one inputs: HighBP, HighChol, CholCheck, BMI, Smoker, Stroke, HeartDiseaseorAttack, PhysActivity, Fruits, Veggies, HvyAlcoholConsump, AnyHealthcare, NoDocbcCost, GenHlth, MentHlth, PhysHlth, DiffWalk, Sex, Age, Education, Income. BMI is kg/m²; GenHlth 1–5; mental/physical unhealthy days 0–30; Age is ordered 1–13 age-group code; Education 1–6; Income 1–8; most others binary. Predictor missingness is retained (Income 77,130; HighChol 61,201; etc.) and fold-imputed. Survey weight/strata/PSU exist for sensitivity, not fitting. Used for the full 343,488-development/85,872-development-test study plus routing, SHAP, survey, ablation, selective and subgroup analyses. No authorized final locked study exists.

**Hospital130/Diabetes 130-US Hospitals:** UCI; raw 101,766 encounters/50 columns. Loader excludes 2,423 death/hospice dispositions, retaining 99,343 encounters from 69,990 patients. Target is `<30` readmission=1 vs `>30`/`NO`=0: 11,314 positive/88,029 negative, prevalence 11.39%. Nine numeric inputs: age bracket 0–9, time_in_hospital 1–14, num_lab_procedures 1–132, num_procedures 0–6, num_medications 1–81, number_outpatient 0–42, number_emergency 0–76, number_inpatient 0–21, number_diagnoses 1–16. Thirty-seven categorical inputs cover admission/discharge/source, race/gender/payer/specialty, three grouped diagnoses, glucose/A1C result categories, medication change categories, `change`, and `diabetesMed`. Race/payer/specialty/glucose/A1C have heavy missingness; categories are constant-imputed and one-hot encoded. Patient groups prevent encounter leakage. This is supporting readmission engineering, never diabetes detection or mixed screening.

No dataset is used as external validation for another. No model is trained on Dataset A and tested on Dataset B. Multi-dataset means a shared framework with endpoint-safe separate models.

## Preprocessing, leakage and reproducibility

PIDD physiological zeros are converted to NaN before split because conversion is deterministic/outcome-blind; medians are learned within folds. Sylhet strings are deterministically encoded and profile IDs created before split. BRFSS target filtering/recode happens before split; missing predictors remain. Hospital death/hospice exclusion, age parsing and ICD grouping happen before patient-grouped splitting. No SMOTE, global scaling, learned whole-data feature selection, PCA or outlier clipping exists. Model-specific class weights may be tuned; XGBoost balance weight is derived from training labels only.

All learned preprocessing/tuning/calibration/threshold selection is inside development. Sylhet profile groups and Hospital patient groups are isolated in inner/outer/test partitions. A deliberate invalid Sylhet row split had 263 profile overlaps and misleadingly improved AUROC ~0.9574→0.9735 and Brier ~0.0798→0.0565. The full seed-42 BRFSS development-test and Hospital smoke outcomes have been inspected; they can never become final unseen evidence.

The reference environment is Python 3.12.0 with 48 distributions locked in `requirements.lock`; standard seed is 42 and raw-data, config, source, manifest and artifact hashes are recorded. `config/data_sources.yaml` and `scripts/acquire_data.py` acquire/verify all four datasets, including PIDD reconstruction from OpenML; `.github/workflows/ci.yml` checks installation/config/tests. A fresh clone can regenerate development evidence, but large models, predictions, metrics and SHAP artifacts are Git-ignored, no container guarantees cross-platform byte identity, and no immutable external artifact store exists.

## Models and tuning

Five benchmark families: Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost. LR tunes C 1e-3–100, L1/L2 option and class weight. RF tunes 200–800 trees, depth, split/leaf size, feature fraction and weight. XGBoost tunes 200–800 trees, depth 3–8, LR .01–.2, child weight, row/column sampling, gamma and L1/L2/balance. LightGBM tunes leaves/depth/child count/learning/sampling/regularization. CatBoost tunes 200–800 iterations, depth 3–9, LR .01–.2, L2/random strength and balance. Exact selected hyperparameters vary per fold and are stored per bundle. There is no universal/final deployed model.

Seeded Optuna TPE optimizes inner-CV AP. PIDD/Sylhet full development is 5 repeats × 5 outer folds × 5 inner folds, 30 trials/model/fold and 500 bootstrap resamples. BRFSS full development is 30 trials/model over five development folds followed by one full-development refit and 500 development-test bootstraps. Pilot is one repeat/5 trials/200 bootstraps. Planned final is 75 trials/2,000 bootstraps but has not run.

## Metrics and actual results

Calculated metrics: N/positives/prevalence, AUROC, average precision, Brier/scaled Brier, log loss, calibration intercept/slope, observed:expected ratio, 10-bin ECE, accuracy/balanced accuracy, sensitivity/specificity/FPR/FNR, PPV/NPV, F1, MCC, Youden, likelihood ratios, diagnostic odds and TN/FP/FN/TP; plus decision-curve net benefit, bootstrap CIs and paired Holm-corrected contrasts.

Full-development participant-aggregated PIDD at calibrated 0.5:

- CatBoost AUROC .8444, AP .7092, Brier .1517, log loss .4620, sensitivity .5896, specificity .8520, TN/FP/FN/TP 426/74/110/158.
- RF AUROC .8395, AP .7095, Brier .1539, sensitivity .6007, specificity .8480, 424/76/107/161.
- LightGBM .8387/.7132/.1539, sensitivity .6007; LR .8376/.7117/.1557; XGB .8383/.7059/.1540. No corrected winner.

Full-development grouped Sylhet at calibrated 0.5:

- CatBoost AUROC .9696, AP .9838, Brier .0609, log loss .2133, sensitivity .9219, specificity .9400, TN/FP/FN/TP 188/12/25/295.
- RF AUROC .9682, AP .9812, Brier .0674, sensitivity .9281; other AUROCs .955–.961. No corrected winner; internal only.

Authoritative full BRFSS development-test N=85,872/11,451 positives: XGBoost AUROC .8430, AP .4436, Brier .09150, log loss .29581; CatBoost .8430/.4421/.09153/.29584; LightGBM .8428/.4432/.09154/.29599; RF .8396/.4371/.09207/.29810; LR .8329/.4043/.09400/.30311. The leading XGB/Cat/LGB pairwise differences do not survive Holm correction. At development-selected ~0.136–0.139 sensitivity thresholds the leading models achieve about 0.803 sensitivity and 0.723–0.726 specificity. This is full development, not final locked evidence.

Hospital smoke N=10,000/1,139 positives: XGB AUROC .6589, AP .2065, Brier .0973; RF .6584/.2040/.0973; Cat .6516/.2003/.0976; LGB .6334/.1874/.0984. At 0.5 XGB has TN/FP/FN/TP 8857/4/1135/4; threshold choice is crucial.

Nested `summary_metrics.csv` averages fold metrics, so N/confusion counts may be fractional fold means. Primary repeated-CV inference is computed from `participant_predictions.csv` with participant confidence/contrast files; there is no literal `participant_metrics.csv` artifact. Holdout `summary_metrics.csv` contains direct test rows. Pilot/full/smoke, different code hashes, fold means/pooling/participant aggregation and endpoint revisions explain apparently inconsistent numbers. No final locked result exists.

## Ontology and availability routing

`config/feature_ontology.yaml` plus `features/ontology.py` generate a 91-row dictionary: 19 explicit shared/related mappings and 72 dataset-specific fields. Canonical concepts are age, body_mass_index, sex_gender, blood_pressure, glycemia, insulin, physical_activity and healthcare_utilization. Examples: PIDD Age/Sylhet Age are years, BRFSS Age a 5-year code, Hospital age a 10-year code; PIDD BMI/BRFSS BMI are quantitative but Sylhet Obesity only a proxy; PIDD BloodPressure is diastolic mmHg while BRFSS HighBP is binary status; PIDD Insulin is a lab while Hospital insulin is medication change. Dataset-specific fields, including PIDD pedigree and most symptoms, are not falsely harmonized. The ontology documents constraints; it does not transform input or directly drive inference.

`config/availability_scenarios.yaml` defines evaluated panels. PIDD has full8, no-insulin/skinfold6, routine5, core4, non-lab4, glucose+age2. Sylhet has full16, questionnaire10, symptoms6, classic4, polyuria/polydipsia2. BRFSS has full21, routine12, cardiometabolic9, health6, demographic-health5, GenHlth+Age2. Hospital has full46, two 9-field panels, prior-use5 and age+inpatient2.

Routing evaluates full-schema tree models with features outside the panel masked to NaN. Per panel, development Brier selects the model, with log loss/AP tie-breaks. Runtime finds panels contained in the non-null fields, takes the largest, applies its saved preprocessor/model/calibrator/threshold, and reports used/ignored fields/provenance. No supported panel means abstention. PIDD full router AUROC/Brier ≈.843/.152; glucose+age .809/.166; non-lab .756/.186. BRFSS full/routine12/cardio9/health6/demographic5/minimal2 AUROC is .8428/.8388/.8370/.8286/.7844/.7794 and Brier .09154/.09239/.09269/.09452/.10155/.10198. Dynamic routing, selector changes and repeated-CV panel-specific training did not show Holm-corrected superiority over robust comparators.

Mixed input is namespaced by dataset. Hospital is excluded from screening. If several screening cohorts qualify, final default behaviour abstains unless `preferred_dataset` is explicit; an experimental priority heuristic exists but is unvalidated. Probabilities are never averaged.

## Holdout, patient inference, SHAP and error analysis

The holdout engine fixes development tuning/calibration/threshold/champion selection before test prediction, preserves Hospital patient groups, bootstraps individuals/clustered patients and saves hashes/access metadata. `splitting/concealment.py` requires a locked profile, frozen plan, completed gates, authorized seed, exact raw/config/signed-record hashes and checksum-valid outcome-blind manifest for a final holdout run, then writes a non-overwritable access receipt before outcomes load. All authorizations are currently false/unset; preflight denies all four datasets without outcome access. This is stronger internal discipline than casual `train_test_split`, but not external validity and not yet tested as a genuinely new final evaluation.

Patient inference validates finite/range-compatible dataset-native input, loads multiple outer router bundles, requires panel agreement, aggregates calibrated probabilities by mean/min/max/SD, reports fold threshold agreement/model/calibrator counts, computes per-fold SHAP, normalizes within fold because scales differ, and adds cohort-relative observational context plus disclaimers. The spread is not a CI. Synthetic PIDD missing Insulin demonstrated `no_insulin_or_skinfold`, mean 66.05%, range 59.54–78.38%, all 5 folds positive; this is a pilot demo, not a real person.

SHAP uses LinearExplainer raw log-odds for LR, TreeExplainer raw probability for RF and raw margins for boosted trees. Calibration happens after the explained model. Only outer/test rows are reported; development provides holdout background. Glucose/BMI lead PIDD; Polyuria/Polydipsia lead Sylhet. Full BRFSS development explains 1,000 development-test rows/model and most consistently ranks GenHlth, HighBP, Age, BMI and HighChol; full Hospital130 development explains 1,000 development-test rows/model and emphasizes prior inpatient use, discharge disposition, diagnosis count and related utilization fields. SHAP is associative, model-relative and non-causal; cross-family raw magnitudes are incomparable.

The final pipeline calculates and saves TP/TN/FP/FN but does **not** compare feature profiles/statistics across error groups or generate SHAP-by-error-class findings. Do not invent false-negative characteristics. Supported error conclusions are counts and threshold trade-offs only.

## Novelty, negative results and publication status

Strongest novelty is the integrated endpoint-safe availability/degradation/abstention framework with calibration, provenance, uncertainty and explanations. Moderate contributions include the ontology, grouped leakage controls, participant-level inference, patient reporting and governance. Standard classifiers, SHAP, calibration, nested CV and metrics are not individually novel.

Important negative/cautionary results: no universal corrected model-family superiority; no corrected router-vs-fixed advantage; no indicator-on advantage in PIDD/Sylhet; no panel-specific RF/XGB training advantage; severe dropout destroys named-panel coverage; and selective prediction improves accepted-case Brier while losing event coverage. In BRFSS at 70% coverage, only 24.97% of positive events are retained. These narrow and strengthen the paper claim.

Supported machine development work, the full BRFSS and Hospital130 development analyses, and conference drafts are complete. `config/publication_protocol.yaml` remains unlocked; the current conference QA audit is NOT READY with 15 blockers and one warning. No authorized final profile, fresh locked study, signed protocol, independent novelty/ontology review or external/temporal validation exists. Hospital130 remains supporting full-development evidence on a separate readmission endpoint. The project is complete as a minor-project implementation, not as a final clinical/publication validation.

## Safe and unsafe claims

Safe: the framework is implemented/tested; full PIDD, grouped Sylhet and full-cohort BRFSS development results exist; fold-safe/group-safe controls address key leakage; feature availability causes measurable degradation; routing can use an evaluated panel or abstain; no universal model/router superiority was established; held-out SHAP identifies model associations; datasets/endpoints remain separate.

Unsafe: diagnoses diabetes; is medically/clinically validated; generalizes to India/world; is robust/production-ready/universal; ontology makes fields interchangeable; router chooses the best model for an individual; SHAP proves causes; holdout proves real-world performance; 0.5 is clinical; multiple datasets prove external generalisation; current results are final/publishable.

## Most important repository paths

- `README.md`, `pyproject.toml`, `requirements.lock`, `docs/RUNBOOK.md`: entry/setup/environment.
- `config/data_sources.yaml`, `docs/DATA_ACQUISITION.md`: exact sources, acquisition, licenses/DOIs and hashes.
- `config/authoritative_studies.yaml`, `evidence/study_registry.json`: current study identity and ignored-artifact registry.
- `config/datasets.yaml`: authoritative cohorts/endpoints/features/splits.
- `config/availability_scenarios.yaml`: all evaluated panels/router bank.
- `config/feature_ontology.yaml`: semantic contracts.
- `config/publication_protocol.yaml`: final/claim locks.
- `src/diabetes_pipeline/data/loaders.py`: current cohort definitions.
- `splitting/strategies.py`, `concealment.py`: group splits/final protection.
- `preprocessing/builders.py`, `models/registry.py`, `training/tuning.py`: ML core.
- `runner.py`, `holdout_runner.py`: study orchestration.
- `evaluation/metrics.py` and other `evaluation/*`: results/uncertainty/ablations.
- `explainability/shap_analysis.py`, `holdout_shap.py`: SHAP.
- `routing/evaluator.py`, `holdout_evaluator.py`, `inference.py`: routing.
- `reporting/patient_results.py`, `mixed_patient_results.py`, `publication_readiness.py`: outputs/safety.
- `docs/progress_reports/BLOCK_A...K`: development history, not always final truth.
- `docs/research/Execution_Status.md`: latest development completion status.
- `conference_package/`: development draft/crosswalks/tables/figures, not final.
- `conference_package/qa/Publication_Readiness_Audit.md`: current registry-driven 15-blocker audit; `PUBLICATION_READINESS.md` is its root pointer.
- `outputs/publication_pipeline/studies/`: local ignored evidence/models; unavailable in clean clone.

## Demo memory

Best professor demo: show `datasets.yaml` endpoint separation; Block A audit/grouping; PIDD/Sylhet participant results and full BRFSS development results; ontology examples BloodPressure vs HighBP and lab insulin vs medication insulin; PIDD availability panels; a Glucose+Age route and Age-only abstention; synthetic patient probability/SHAP with “not diagnosis”; finish on the current publication readiness audit. Emphasize PIDD .844 AUROC/.152 Brier, grouped Sylhet .970/.061, BRFSS .843/.0915, Sylhet leakage inflation, panel degradation and the negative router result. Do not lead with legacy metrics or Hospital as diabetes prediction.

## Important terminology

- **Development pilot/full development/final locked:** increasing evidence tiers; final locked does not exist.
- **Outer fold:** untouched evaluation partition for one nested-CV fit.
- **Participant aggregation:** average repeated held-out probabilities per unique person before primary metrics.
- **Profile group:** identical Sylhet feature vector kept in one split; not proven patient identity.
- **Calibration:** mapping base scores to probabilities; selected from development OOF predictions.
- **Panel/scenario:** prespecified dataset-native feature subset evaluated by masking.
- **Availability router:** panel compatibility plus development-selected model; not cross-dataset fusion.
- **Robust single model:** full-panel champion used as fixed comparator across panels.
- **Mixed router:** namespaced screening candidates; explicit environment or abstain.
- **Evidence tier:** smoke, pilot, development or final-locked metadata controlling claims.
- **Fold spread:** variation across CV research models, not confidence interval.
- **Ontology:** semantic mapping/prohibition dictionary, not learned harmonizer.
- **Hospital130:** readmission endpoint, never diabetes status.
- **SHAP scale:** raw log-odds/probability/margin depending on family, before calibration.
- **Publication gate:** fail-closed audit separating working software from final scientific evidence.

## Current final status and open questions

As of the 29 August audited working tree based on commit `9b15b26`, the intended development software, full PIDD/Sylhet/BRFSS studies, supported development analyses, reproducibility controls, conference package and tests exist. Large data/models/results are not carried by Git; the workspace changes themselves are not yet captured in a single commit. The protocol is not frozen and no final run is authorized. Do not describe a “final trained model”; only repeated-CV or holdout development artifacts exist.

Genuinely open questions: Will the project owner approve a code license, and is PIDD's original data-use provenance adequate for publication? Which ontology/panels will independent clinicians approve? What final primary comparisons/non-inferiority margins and action thresholds will be signed off? What genuinely fresh final evaluation design can avoid reuse of the already inspected seed-42 evidence? Which external/Indian/temporal cohort is appropriate? Will calibration and degradation reproduce externally? Does abstention improve clinically meaningful utility without excluding disproportionate positives/subgroups? Is automatic environment selection ever justifiable without a matched multi-schema cohort? Where will immutable final data/artifacts be archived? These gaps must be answered rather than filled with assumptions.
