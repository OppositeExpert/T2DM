# Literature and Novelty Matrix

**Status:** Initial seed records only; full-text extraction and systematic search pending

**Search started:** 23 August 2026

The entries below establish the first evidence set. `Abstract screened` means the
record is relevant, but absence of a method or metric in the row must not yet be
interpreted as proof that the full paper omitted it.

| ID | Record | Type/data | Endpoint/design visible at seed screen | Reliability/utility visible at seed screen | Relevance and unresolved extraction | Stage |
|---|---|---|---|---|---|---|
| M-001 | [TRIPOD+AI statement, BMJ 2024](https://www.bmj.com/content/385/bmj-2023-078378) | Reporting standard | Prediction-model development/evaluation reporting, regression and ML | Requires transparent performance, subgroup/fairness and open-science reporting | Controls manuscript crosswalk; extract all applicable checklist subitems | Included guidance |
| M-002 | [PROBAST+AI, BMJ 2025](https://www.bmj.com/content/388/bmj-2024-082505) | Risk-of-bias/applicability tool | Prediction models using regression or AI | Structured quality, bias, and applicability assessment | Controls pre-final bias audit and journal-readiness judgment | Included guidance |
| M-003 | [Evaluation of clinical prediction models, part 2, BMJ 2024](https://www.bmj.com/content/384/bmj-2023-074820) | Methodological guidance | External validation and performance evaluation | Overall fit, Brier, discrimination, calibration curves/intercept/slope/O:E, subgroup checks, net benefit | Supports complete metric taxonomy and external-validation requirement | Full-text available; extract |
| M-004 | [Vickers and Elkin 2006](https://pubmed.ncbi.nlm.nih.gov/17099194/) | Original method | Prediction-model clinical utility | Introduces decision-curve net benefit over threshold probabilities | Supports DCA; extract uncertainty and comparison recommendations from later methodological work | Full-text included |
| M-005 | [UCI Sylhet dataset record](https://archive.ics.uci.edu/dataset/529/early%2Bstage%2Bdiabetes%2Brisk%2Bprediction%2B) | Official dataset source | 520 questionnaire records, 16 features, Sylhet Diabetes Hospital | Dataset page, not a full validation study | Confirms source and introductory paper; reconcile page missingness metadata with local file audit | Included source |
| M-006 | [Early Diabetes Prediction: comparative ML study](https://pubmed.ncbi.nlm.nih.gov/35773898/) | Sylhet model study | Questionnaire prediction; LR, SVM, KNN, NB, RF, neural network; information-gain feature selection | Abstract reports RF accuracy of 100% | Closest benchmark; must extract split, duplicate grouping, calibration, uncertainty, and leakage controls | Abstract screened |
| M-007 | [Efficient early-stage diabetes prediction with RF feature selection and XGBoost](https://pmc.ncbi.nlm.nih.gov/articles/PMC10043839/) | Sylhet model study | 520 records, RF-based feature selection, XGBoost | Reports accuracy 99.2% and AUC 99.3% | High result needs duplicate/group-split audit; extract sampling order, calibration, intervals, and code | Full-text available; extraction pending |
| M-008 | [Integrated statistical and ML analysis of Sylhet symptoms](https://pmc.ncbi.nlm.nih.gov/articles/PMC9676132/) | Sylhet model study | 520 individuals, multi-k-fold analysis, 10 methods | Abstract emphasizes misclassification/error and feature influence | Extract exact CV design, repeated-person handling, calibration, uncertainty, and availability analysis | Full-text available; extraction pending |
| M-009 | [PIDD preprocessing and ML framework](https://pubmed.ncbi.nlm.nih.gov/35429810/) | PIDD plus external LMCH dataset study | Feature selection, imputation, RF/SVM/deep model, repeated stratified CV | Abstract reports very high classification metrics | Extract whether external LMCH is true external validation, preprocessing isolation, AP/calibration/utility, and sampling | Abstract screened |
| M-010 | [PIDD interpretable classifier comparison](https://pubmed.ncbi.nlm.nih.gov/35345556/) | PIDD model study | Naive Bayes, RF, J48 | Accuracy/precision/sensitivity/specificity visible | Establishes benchmark saturation; extract split/tuning, zero handling, uncertainty and calibration | Abstract screened |
| M-011 | [Tennessee BRFSS 2023 explainable ML study](https://pubmed.ncbi.nlm.nih.gov/41324206/) | BRFSS model study | 5,634 adults; seven algorithms; stratified 5-fold CV; self-reported diabetes | Accuracy, precision, recall, balanced accuracy, F1, AUROC, PR-AUC; SHAP | Recent close dataset family; extract survey weights, calibration, DCA, missingness and validation scope | Abstract screened |
| M-012 | [Selective prediction for clinical data abstraction](https://pmc.ncbi.nlm.nih.gov/articles/PMC10746316/) | Clinical selective-prediction study | Multiple clinical note abstraction outcomes and selective classifiers | Abstention rate, error/cost trade-off, sensitivity/specificity/PPV/NPV | Directly supports cost-aware deferral but not diabetes risk; extract coverage and threshold-selection design | Full-text available; extraction pending |

## Initial novelty signal

The seed set shows a crowded algorithm-comparison literature for PIDD and Sylhet,
including extremely high reported accuracy on Sylhet, plus recent BRFSS work with
explainability and PR-AUC. The initial records do not yet show a directly matched
study combining prespecified availability panels, calibration selection,
degradation uncertainty, endpoint-safe routing, and abstention. That is a working
hypothesis, not a novelty conclusion.

The literature already makes clear that “we compared five algorithms” or “we used
SHAP” is not a defensible primary novelty claim. The project must differentiate
itself through the availability/reliability evaluation and must directly audit
why reported benchmark accuracy is non-comparable when endpoints, duplicates,
sampling, or validation designs differ.

## Required next records

- Original PIDD source/introductory study and strongest external-validation papers.
- Original BRFSS 2015 source/codebook plus nationally representative diabetes-model studies.
- Original Hospital130/Strack paper and strongest patient-grouped readmission models.
- Missing-predictor model families and feature-set-flexible prediction.
- Mixture-of-experts/dynamic routing studies with held-out routing evaluation.
- Selective prediction in tabular clinical risk models.
- Calibration and decision-curve studies in diabetes screening.
- Repeated cross-validation inference and cluster-bootstrap methodological papers.

## Extraction cautions

- Verify full text before recording an omission.
- Separate diabetes status/diagnosis from future incidence.
- Separate balanced derivative BRFSS datasets from the configured full cohort.
- Record whether resampling or feature selection occurred before splitting.
- For Sylhet, determine whether identical profiles crossed evaluation folds.
- For Hospital130, determine whether encounters from one patient crossed partitions.
- Do not compare accuracy across different prevalences or endpoint encodings.
