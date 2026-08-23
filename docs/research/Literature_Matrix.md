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
| M-013 | [Handling missing predictor values when validating and applying a prediction model](https://pmc.ncbi.nlm.nih.gov/articles/PMC7586995/) | Clinical prediction methodology | Compares observed-data submodels, marginalization, and chained-equation approaches for one new patient | Evaluates methods in an internal-validation setting intended to transfer to practice | Direct closest work: proves that prediction from variable subsets is established; our novelty must be evaluation/routing design rather than the general idea | Full-text screened |
| M-014 | [Missing data and prediction: the pattern submodel](https://pmc.ncbi.nlm.nih.gov/articles/PMC7868046/) | Prediction methodology | Fits pattern-specific submodels and selects the submodel matching an incomplete predictor profile | Focuses on efficient prediction under missing patterns | Strongest conceptual overlap with panel-specific routing; must be cited and contrasted directly | Full-text screened |
| M-015 | [Real-time imputation of missing predictor values in clinical practice](https://pmc.ncbi.nlm.nih.gov/articles/PMC9707891/) | Cardiovascular prediction methodology | Compares mean and patient-specific joint-model imputation across missing-predictor scenarios and cohorts | Reports prediction error, discrimination, calibration intercept/slope, and decision-curve net benefit | Establishes a strong imputation alternative; our panel routers need explicit comparison/limitation language | Full-text screened |
| M-016 | [Explanation-guided dynamic feature selection for medical risk prediction](https://openreview.net/pdf?id=1itfhff53V) | Medical ML workshop study | Fixed model plus conditional imputation and local explanations; recommends which unobserved feature to acquire next | Evaluates flexible risk prediction and feature acquisition on UK Biobank myocardial-infarction risk | Closest dynamic-availability method; workshop rather than diabetes study, but narrows novelty substantially | Full-text screened |
| M-017 | [AutoPrognosis 2.0](https://pmc.ncbi.nlm.nih.gov/articles/PMC10287005/) | Clinical AutoML system | Automates imputation, processing, model selection, fitting, explanation, and demonstrator generation | General clinical modelling platform | Shows automated model selection and demonstrators are not novel alone; lacks our exact prespecified-panel claim | Full-text screened |
| M-018 | [Building type 2 diabetes prediction models using 2014 BRFSS](https://pmc.ncbi.nlm.nih.gov/articles/PMC6795062/) | BRFSS diabetes study | Two-thirds training/one-third imbalanced test; training-only SMOTE; multiple classical ML models; weighted regression also reported | Accuracy, sensitivity, specificity, AUROC; 95% CIs for association analysis | Strong BRFSS benchmark and survey-design precedent; does not establish availability routing | Full-text screened |
| M-019 | [Comprehensive BRFSS diabetes prediction: performance, explainability, fairness, and calibration](https://jurnal.polibatam.ac.id/index.php/JAIC/article/download/12740/3644/42124) | BRFSS 2015 model study | Logistic Regression, RF, XGBoost, CatBoost; includes feature and misclassification analyses | Balanced/classification metrics, AUROC, PR-AUC, MCC, Brier, calibration, SHAP, fairness, ablation | Direct 2026 overlap: removes metrics, calibration, fairness, SHAP, and ordinary ablation from our novelty claim | Full-text screened |
| M-020 | [Tennessee BRFSS 2023 explainable ML study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12669510/) | State BRFSS diabetes study | 5,634 adults, survey-weighted descriptions, MICE, training-only SMOTE, seven models, stratified CV | Accuracy, balanced accuracy, precision, recall, F1, AUROC, PR-AUC, SHAP | Confirms modern BRFSS studies already combine survey methods, imbalance handling, ML comparison, and explanation | Full-text screened |
| M-021 | [Original Hospital130/Strack analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC3996476/) | Original data/association study | Nearly 70,000 qualifying encounters; logistic model of HbA1c measurement and early readmission | Adjusted estimates and 95% intervals; explicitly non-causal observational limitations | Establishes the dataset's original purpose and reinforces that readmission is a separate endpoint | Full-text screened |
| M-022 | [Original PIDD ADAP study](https://pmc.ncbi.nlm.nih.gov/articles/PMC2245318/) | Original Pima study | Early neural-network forecasting in a high-risk Pima population | Historical classification/forecasting evaluation | Essential provenance; does not justify transport to current mixed populations | Full-text screened |
| M-023 | [Developing models with systematically missing predictors across studies](https://pubmed.ncbi.nlm.nih.gov/36755407/) | Multi-study prediction methodology | Compares common-predictor restriction, clustered/non-clustered imputation, and multi-study prediction ensembles | Simulation plus real 12-trial illustration | Related to heterogeneous feature sets, but targets study-level missingness and continuous outcomes rather than our within-environment named panels | Abstract/full metadata screened |
| M-024 | [Imputation and missing indicators for clinical model development/deployment](https://pmc.ncbi.nlm.nih.gov/articles/PMC10515473/) | Simulation methodology | Compares MI/regression imputation and missing indicators across development and deployment missingness mechanisms | Emphasizes matching validation and deployment handling | Supports our requirement that panel/missingness behavior be evaluated exactly as deployed | Full-text screened |

## Initial novelty signal

The expanded seed set shows a crowded algorithm-comparison literature for PIDD,
Sylhet, and BRFSS. A 2026 BRFSS paper already combines tree-model comparison,
calibration, fairness, SHAP, and ablation. Separate methodological work already
covers pattern-specific submodels, real-time imputation, automated model selection,
and dynamic feature acquisition. Therefore none of those elements is novel alone.

The current defensible novelty candidate is narrower: a prespecified and
endpoint-safe evaluation of calibrated performance degradation across clinically
interpretable feature-availability panels, coupled with evaluated abstention and
complete prediction provenance across several separately analysed diabetes-status
environments. No screened record yet matches that exact combination. This remains
a provisional conclusion until database-complete searching and independent review.

The literature already makes clear that “we compared five algorithms” or “we used
SHAP” is not a defensible primary novelty claim. The project must differentiate
itself through the availability/reliability evaluation and must directly audit
why reported benchmark accuracy is non-comparable when endpoints, duplicates,
sampling, or validation designs differ.

## Required next records

- Strongest PIDD external-validation papers.
- Official BRFSS 2015 source/codebook and nationally representative validation work.
- Strongest patient-grouped Hospital130 prediction models.
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
