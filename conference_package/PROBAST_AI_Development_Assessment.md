# PROBAST+AI Preliminary Development Assessment

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
