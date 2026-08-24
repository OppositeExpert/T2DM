# TRIPOD+AI Development Crosswalk

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

