# Manuscript review and unresolved decisions

The target is Discover Computing. Current estimates and claim boundaries come
from `results/final_publication/`, the results guide and the frozen protocol.
This file preserves useful review work from the archived conference package;
its development-era checklist assessments below are preparation records, not
current compliance or final statistical sign-off. Re-map them to the approved
journal manuscript and use separate Hospital130 30-day-readmission assessment.

PIDD calibrated participant-level and Sylhet calibrated participant-level
probabilities mean one average held-out probability per participant across
repeats. Sylhet uncertainty preserves identical-predictor-profile clusters.
Do not present fold-level descriptive threshold estimates as this estimand.
The historical estimand regression table/provenance is retained under
`evidence/development_reference/`; its development estimates are not final ones.

## Current review queue

- Recover the exact executed training-source closure and deposit permitted
  artifacts in an approved immutable restricted archive; no DOI is established.
- Reconcile the approved manuscript against current tables, correction records,
  endpoints, uncertainty units and negative switching results.
- Complete independent literature extraction and novelty review using the
  retained literature matrix/search protocol and provisional novelty assessment.
- Resolve the September integrity findings against the final source/artifacts;
  `audits/2026-09-05/FINAL_REPOSITORY_AUDIT.md` is dated evidence, not a statement
  that every finding remains open or has been fixed. No blanket closure is claimed.
- Plan mentor analyses with successor output paths, particularly panel-specific
  retraining across all cohorts, dedicated alternative-imputation comparisons,
  calibration/model-family ablations, routing summaries and actual fallback.
  See CONTRIBUTING.md for implementation and completion limits.
- Obtain all four researchers' approved author order, affiliations, contact and
  CRediT roles; corresponding author; ethics/exemption, funding, conflicts, data
  terms, license, acknowledgements and any AI-use declarations. Leave unknown
  values unfilled. Reconcile the historical journal name without editing the
  frozen protocol. Complete venue template, word limits and checklist mapping.

## Preserved review scaffolds

The following source sections are carried forward without changing their
reported development findings. Original documents and all conference outputs
are also checksummed in the local archive. References to development studies
require approved private artifact restoration; replace manuscript page/section
locations during final author review.


## Claim-to-Evidence Development Crosswalk

**State:** Complete for the current development manuscript; must be revalidated
against locked final artifacts before submission

This table prevents a polished sentence from outrunning its evidence. “Supported”
means supported as a development finding, not authorized as a final claim.

| Claim ID | Proposed manuscript claim | Evidence artifact | Current disposition | Final action |
|---|---|---|---|---|
| C01 | The pipeline evaluates five model families with leakage-controlled nested or grouped validation. | PIDD and Sylhet experiment metadata, split manifests, tuning tables, saved outer models | Supported | Confirm hashes and final-profile metadata |
| C02 | PIDD model-family performance is tightly clustered rather than dominated by one complex learner. | `pidd_development_072cd2104089/participant_confidence_intervals.csv` and participant comparisons | Supported | Replace with locked estimates and intervals |
| C03 | The full PIDD router and robust fixed baseline have nearly identical probability performance. | PIDD `availability_routing/summary_metrics.csv` and paired contrasts | Supported; no superiority claim | Retain negative result unless the frozen comparison changes it |
| C04 | Reduced panels show measurable descriptive degradation, but no matched PIDD comparison survives Holm correction. | PIDD `matched_panel_contrasts/paired_contrasts.csv` | Supported | Confirm the frozen comparison family |
| C05 | PIDD panel-specific retraining does not establish corrected superiority over masked full-panel inference. | PIDD `ablations/panel_specific_training/paired_contrasts.csv` | Supported | Recheck after protocol freeze |
| C06 | PIDD missingness indicators do not establish corrected benefit. | PIDD `ablations/missing_indicator_retraining/paired_contrasts.csv` | Supported | Recheck after protocol freeze |
| C07 | Certainty-based selective prediction improves retained-case metrics while disproportionately excluding positive events. | PIDD and Sylhet `selective_prediction/risk_coverage_metrics.csv` | Supported and qualified | Always report positive-event coverage and accepted prevalence |
| C08 | Severe simulated missingness sharply reduces supported-panel coverage and worsens probability loss. | PIDD and Sylhet `missingness_stress/summary_metrics.csv` | Supported as sensitivity analysis | Do not describe as real-world MNAR validation |
| C09 | Sylhet participant-level internal discrimination is high, but the small symptom-enriched cohort limits transportability. | `sylhet_development_b52477910fe6/participant_confidence_intervals.csv` with identical-profile cluster inference | Supported and cautionary | Preserve transportability qualification in abstract and discussion |
| C10 | No completed Sylhet routing, artifact-ablation, or panel-retraining family supports a Holm-corrected superiority claim. | Sylhet routing, matched-panel, and ablation contrast tables, including `ablations/panel_specific_training/paired_contrasts.csv` | Supported | Preserve the negative/inconclusive result in the locked analysis |
| C11 | Mixed namespaced input never fuses probabilities across datasets and abstains when the environment is ambiguous or unsupported. | Routing contracts, patient report schema, tests | Supported as engineering behavior | Keep outside efficacy claim |
| C12 | Returned percentages estimate the configured recorded status label, not future incidence or age at onset. | Dataset contracts, endpoint hierarchy, patient-report wording | Supported boundary | Preserve verbatim meaning in all submission material |
| C13 | The full BRFSS development study shows near-identical boosted-tree performance, panel degradation, and a materially different survey-weighted estimand. | `brfss_development_holdout_56407ef53bba` metrics, intervals, routing, and survey-sensitivity artifacts | Supported as full development only | Replace or explicitly retain as development after an authorized one-time final holdout execution |
| C14 | Hospital130 full-development evidence evaluates a separate 30-day readmission endpoint with patient-grouped inference and is excluded from diabetes-status efficacy claims. | `hospital130_development_holdout_c3aa5fb84a7a` metadata, metrics, intervals, routing, and explanation artifacts | Supported as full development only | Retain endpoint and evidence-tier separation in supplement and code release |
| C15 | The work is not externally or temporally validated and is not clinically deployable. | Protocol flags and blocker register | Supported limitation | Remove only after independent compatible validation |

## Claim rules

- No abstract, table, caption, conclusion, cover letter, or presentation may use a
  stronger interpretation than the corresponding row above.
- Development point estimates must not be relabelled as locked or final.
- “No corrected difference detected” must not be rewritten as equivalence.
- AUROC must be accompanied by probability/calibration evidence and applicability.
- Selective-prediction gains must be accompanied by overall coverage and positive-
  event coverage.
- Every numerical claim must be regenerated from an immutable artifact rather than
  manually copied from terminal output.


## TRIPOD+AI Development Crosswalk

**State:** Main-item development crosswalk prepared; author review, final page
references, and the official 52-subitem checklist remain required

The official TRIPOD+AI statement contains 27 main items and 52 subitems. This
crosswalk follows the 7 February 2024 expanded checklist and the separate
TRIPOD+AI for Abstracts checklist. It is a preparation artifact, not a signed
declaration of compliance.

| Item | Topic | Current location or evidence | State / required revision |
|---:|---|---|---|
| 1 | Informative title | Manuscript title | Partial: add final target population/outcome wording if venue length permits |
| 2 | Abstract checklist | Abstract | Partial: add final sample flows, intervals, availability statement, and venue word-limit edit |
| 3 | Background, intended use, inequalities | Introduction; subgroup methods/results | Partial: intended use is bounded; add cited diabetes inequality context |
| 4 | Objectives | Abstract and Introduction | Present |
| 5 | Data sources and dates | Methods 2.1; supplement S1-S2 | Partial: add complete dataset provenance and collection dates |
| 6 | Setting, eligibility, treatment context | Methods 2.1; dataset audit artifacts | Partial: add participant-flow/eligibility table; treatment not applicable should be explicit |
| 7 | Data preparation and quality checks | Methods 2.2 and 2.6; data audit | Present in outline; expand reproducible cleaning details in supplement |
| 8 | Outcome definition and assessment | Methods 2.1; endpoint hierarchy | Partial: add source-specific assessment details and explicit assessor/blinding applicability |
| 9 | Predictor selection and measurement | Methods 2.2; feature dictionary and ontology | Partial: add units/codings and measurement timing table |
| 10 | Study size | Limitations; participant counts | Partial: all available records used; add formal adequacy justification and event counts |
| 11 | Missing data | Methods 2.2 and 2.6; missing-indicator and stress reports | Present in outline; add per-feature missingness table |
| 12 | Analytical methods | Methods 2.3-2.6; SAP; run metadata | Strong development coverage; add final software versions and complete tuning spaces |
| 13 | Class imbalance | Model configuration and metric rationale | Partial: specify weighting choices and recalibration sequence per model |
| 14 | Fairness | Subgroup and suppression methods; limitations | Partial: add explicit bias-mitigation decisions and unsupported attributes |
| 15 | Model output and thresholds | Methods 2.2, 2.4-2.5; patient-report contract | Present; preserve distinction between probability and thresholded label |
| 16 | Development/evaluation differences | Dataset-specific environments and split contracts | Partial: add a compact environment-comparison table |
| 17 | Ethics | Declarations; public dataset provenance | Pending author/institution determination and approved wording |
| 18 | Open science, funding, conflicts, protocol, registration, data/code | Declarations; package manifest; author input sheet | Partial: URLs, archive DOI, funding/conflicts, registration decision, licences pending |
| 19 | Patient and public involvement | Not yet reported | Pending: state none or describe actual involvement; do not infer |
| 20 | Participant flow and characteristics | Audit outputs; supplement placeholders | Pending final consolidated flow and characteristics tables |
| 21 | Analysis sample/event counts | PIDD/Sylhet metadata and predictions | Partial: add final counts for every analysis and BRFSS after authorization |
| 22 | Full model availability | Saved bundles, code, feature contracts | Partial: public release URL/tag/licence and stable inference example pending |
| 23 | Performance, subgroups, heterogeneity | Main Tables 1-2; figures; intervals; subgroup outputs | Strong development coverage; add frozen intervals/plots and BRFSS evidence |
| 24 | Model updating | Calibration described; no external updating study | Clarify not applicable beyond development-selected calibration |
| 25 | Interpretation | Discussion | Present and appropriately conservative |
| 26 | Limitations | Discussion | Present; retain calibration, transportability, benchmark reuse, and missingness limits |
| 27 | Usability, unavailable inputs, interaction, future work | Routing/abstention methods; Discussion | Present in outline; add concise user workflow and implementation requirements |

## TRIPOD+AI for Abstracts completion check

The final abstract must explicitly cover: study type and target/outcome; context;
objective; data sources; eligibility/setting; outcome; model-building and internal
validation; performance measures; sample size and event counts; principal results
with intervals; conclusions consistent with evidence; model/code availability;
and registration/funding where required. The current abstract is structurally
close but cannot be completed until BRFSS/final evidence and venue limits are known.

## Sign-off procedure

1. Rebuild the final DOCX/PDF and assign stable page or line numbers.
2. Complete every applicable official subitem using `Yes`, `No`, or `Not
   applicable`, with a page/line reference and rationale.
3. Have a second reviewer check the crosswalk against the manuscript and supplement.
4. Archive the signed checklist, then—and only then—change
   `tripod_ai_checklist_complete` to true.

Official sources: TRIPOD+AI, BMJ 2024;385:e078378,
doi:10.1136/bmj-2023-078378; expanded checklist version 7 February 2024.



## PROBAST+AI Preliminary Development Assessment

**State:** Structured preliminary assessment; not independently reviewed and not
eligible to close the PROBAST+AI gate

PROBAST+AI separates the quality of model development from risk of bias in model
performance evaluation. It contains four domains, 34 signalling questions (16
for development and 18 for evaluation), and six applicability items. The ratings
below are deliberately conservative and must be checked against the official tool
by a second assessor.

## Intended assessment scope (PICOTS)

- **Population:** people represented by each public PIDD, Sylhet, or BRFSS
  diabetes-status environment; no universal pooled population.
- **Index models:** five candidate model families plus within-environment
  availability routers and fixed-model comparators.
- **Comparators:** robust fixed model, full-panel family baseline, and prespecified
  reduced-panel/missingness variants.
- **Outcome:** each dataset's configured recorded diabetes-status label; not future
  incidence. Hospital130 readmission is excluded from the primary assessment.
- **Timing:** cross-sectional/status prediction using available measurements; no
  onset-time horizon.
- **Setting and use:** methodological screening research and software
  demonstration; not clinical deployment.

## Domain judgments

| Domain | Development quality | Evaluation risk of bias | Applicability | Rationale and unresolved work |
|---|---|---|---|---|
| 1. Participants and data sources | High concern | High concern | High concern | Small public convenience cohorts, benchmark reuse, uncertain representativeness, and no external/temporal cohort dominate. BRFSS is large but self-reported and survey-derived. Participant grouping is protected where identifiable. |
| 2. Predictors | Some concern | Some concern | High concern | Predictor definitions and panel contracts are explicit, preprocessing is fold-local, and unavailable input triggers abstention. Measurement procedures, units, timing, and cross-setting transportability require fuller source documentation. |
| 3. Outcome | High concern | Some-to-high concern | High concern | Endpoints are separated and leakage controls exist, but PIDD/Sylhet labels and BRFSS self-report are not a uniform clinical reference standard. The data cannot support incidence or age-at-onset claims. |
| 4. Analysis | Some concern | Some concern | Some concern | Nested/grouped validation, calibration, paired inference, multiplicity control, selective coverage, stress tests, and fail-closed final access are strengths. Remaining concerns include small effective sample sizes, unstable Sylhet calibration, protected BRFSS/final evidence not yet accessed, possible model instability, and no external evaluation. |

## Overall preliminary judgment

- **Model-development quality:** high concern overall because a high-concern domain
  cannot be offset by strong software engineering.
- **Performance-evaluation risk of bias:** at least some concern, with the final
  rating held open until the authorized evidence and official signalling questions
  are reviewed.
- **Applicability:** high concern for any clinical-generalization claim; narrower
  applicability is acceptable only for the methodological conference question.

This assessment means the paper may be conference-worthy as a transparent
methodological/reliability study, but it cannot be framed as a clinically ready
diabetes risk tool.

## Evidence that reduces concern

- Endpoint-specific analysis with no cross-cohort probability fusion.
- Group-preserving Sylhet validation and participant-level repeated-CV inference.
- Fold-local preprocessing, tuning, calibration, and held-out explanations.
- Confidence intervals, paired comparisons, multiplicity correction, calibration,
  and decision-curve evidence rather than accuracy alone.
- Prespecified panels, explicit applicability coverage, abstention reasons, and
  positive-event retention for selective prediction.
- Outcome-blind concealed-holdout mechanism and authorization guard.
- Negative and unstable findings retained in the manuscript.

## Required assessor actions

1. Complete all applicable official development and evaluation signalling
   questions separately for PIDD, Sylhet, and BRFSS.
2. Attach evidence and rationale to every `No`, `Probably no`, `No information`,
   and `Not applicable` answer.
3. Resolve any disagreement through a second independent assessor.
4. Preserve dataset-specific judgments; do not average ratings across cohorts.
5. Archive the reviewed form before changing `probast_ai_assessment_complete`.

Official source: PROBAST+AI, BMJ 2025;388:e082505,
doi:10.1136/bmj-2024-082505.
