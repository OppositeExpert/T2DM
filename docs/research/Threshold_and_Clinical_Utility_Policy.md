# Threshold and Clinical-Utility Policy

**Status:** Draft, development-only

**Version:** 0.1, 23 August 2026

**Freeze state:** Unlocked; no threshold may be optimized on a final test set

## 1. Decision context

The diabetes-screening outputs are intended only as research estimates that may
identify people for further assessment or clinician review. They are not
diagnoses, treatment recommendations, or estimates of the age at which diabetes
will occur. Hospital130 has a separate readmission-review context.

Decision thresholds represent the relative cost of a false positive and a false
negative in a hypothetical further-assessment pathway. A threshold is not called
clinically optimal unless the action, harms, resource costs, and target setting
are independently justified.

## 2. Operating thresholds

| Policy | Role | Learning data | Final-test use |
|---|---|---|---|
| Sensitivity-constrained | Provisional primary screening operating point | Cross-fitted development predictions only | Apply the frozen development threshold unchanged |
| Youden development | Secondary statistical operating point | Cross-fitted development predictions only | Apply unchanged; never call clinically optimal |
| Fixed 0.5 | Descriptive benchmark | None | Report for comparability, not as the primary screening rule |

The provisional sensitivity target is 0.80. Before protocol freeze, Phase 2 must
either document why 0.80 is acceptable for each screening environment or replace
it with a better-supported common or dataset-specific target. A change after
viewing a fresh final outcome is prohibited.

For repeated nested evaluation, each outer-fold threshold is learned from that
fold's development predictions and applied only to its held-out patients. For a
locked holdout, one threshold is learned entirely within the development
partition and then applied unchanged to the concealed test partition.

## 3. Thresholded metrics

At every prespecified operating point, report:

- sensitivity and specificity;
- positive and negative predictive value;
- false-positive and false-negative rate;
- balanced accuracy, F1, and Matthews correlation coefficient;
- positive and negative likelihood ratios;
- the full confusion matrix;
- sample size, event count, prevalence, threshold source, and 95% confidence intervals.

PPV and NPV are cohort-prevalence dependent and will not be transported to a new
population without prevalence adjustment or direct external validation.

## 4. Decision-curve analysis

The model net benefit will be compared with treat-all and treat-none strategies.
Final curves must use held-out calibrated probabilities and must show 95%
bootstrap intervals or a clearly documented uncertainty band.

Provisional threshold ranges are:

| Environment | Draft range | Draft coverage | Reason for draft boundary |
|---|---:|---:|---|
| PIDD | 0.10–0.50 | increments of 0.01 | Screening/further-assessment range; excludes implausibly high intervention thresholds |
| Sylhet | 0.10–0.60 | increments of 0.01 | Higher-prevalence symptom setting; remains a questionnaire-cohort analysis |
| BRFSS | 0.02–0.30 | increments of 0.01 | Lower-prevalence status-screening environment |
| Hospital130, if retained | 0.02–0.30 | increments of 0.01 | Lower-prevalence readmission-review setting; separate endpoint |

These ranges are not yet frozen. Phase 2 must ground them in the intended action
and relevant clinical-prediction literature. The current generic software curve
of 0.01–0.80 is useful for diagnostics but is too broad to be the only paper
analysis.

Net benefit at threshold `p_t` is calculated as:

`TP / N - FP / N * p_t / (1 - p_t)`.

Clinical-utility wording requires that the model have positive net benefit and
compare favorably with the appropriate default strategy over a non-trivial,
prespecified threshold interval. An isolated crossing at one threshold is not
sufficient.

## 5. Calibration policy for percentage outputs

Calibration method selection is performed using cross-fitted development
predictions. Identity, sigmoid, and isotonic methods remain eligible; isotonic is
ineligible when the calibration sample has fewer than 1,000 observations.
Brier score is the selection criterion and log loss is the deterministic
tie-breaker.

Report raw and calibrated:

- Brier and scaled Brier score;
- log loss;
- calibration intercept and slope;
- observed/expected ratio;
- equal-frequency calibration curve with counts;
- expected calibration error as a secondary, bin-dependent summary.

Interpretation bands are diagnostics rather than formal hypothesis tests:

| Measure | Desirable | Caution | Unacceptable for an unqualified percentage claim |
|---|---:|---:|---:|
| Calibration intercept | -0.10 to 0.10 | -0.50 to 0.50 | outside -0.50 to 0.50 |
| Calibration slope | 0.80 to 1.20 | 0.50 to 2.00 | below 0.50 or above 2.00 |
| Observed/expected ratio | 0.90 to 1.10 | 0.75 to 1.33 | outside 0.75 to 1.33 |
| Scaled Brier score | above 0 | near 0 | below 0 |

Uncertainty and visual curves take precedence over a point estimate falling just
inside a band. If calibration is unacceptable, the result may still be reported
as a ranking model, but individual percentages must be qualified as unreliable
in that environment.

## 6. Multiplicity and uncertainty

- All final intervals are two-sided 95% intervals.
- Thresholded metrics use paired individual bootstrap for PIDD/BRFSS, identical-
  profile cluster bootstrap for Sylhet, and patient-cluster bootstrap for
  Hospital130.
- Decision-curve differences use the same paired resamples as model comparisons.
- Within each dataset, inferential comparisons across named panels for the
  primary Brier estimand form one Holm-corrected family.
- Discrimination and threshold-specific comparisons are secondary families and
  are labelled accordingly.
- No threshold is chosen because it appears favorable on a final curve.

## 7. Abstention and selective prediction

Contract failures always cause abstention: unsupported feature panel, invalid
type/category, value outside the reference applicability range, missing model or
calibrator artifact, ambiguous eligible environment, or endpoint mismatch.

Any optional graded acceptance score must be frozen before final evaluation. At
minimum, report 100%, 90%, 80%, 70%, and 50% nominal coverage where achievable,
plus actual coverage, accepted-case losses, discrimination, subgroup coverage,
and reason-specific rejection counts. Coverage points with fewer than 100
accepted observations or fewer than 20 events and 20 non-events are suppressed.

Improved retained-case performance is not considered useful if it is achieved by
disproportionately rejecting a protected or clinically important subgroup.

## 8. Freeze checklist

- [ ] Intended downstream action is stated for each retained dataset.
- [ ] Sensitivity target has a documented rationale or is revised.
- [ ] Decision-curve ranges have literature/clinical justification.
- [ ] Net-benefit uncertainty is implemented and tested.
- [ ] Calibration diagnostic bands are reviewed and justified.
- [ ] Subgroup suppression and coverage rules are finalized.
- [ ] Threshold learning is verified to exclude all final labels.
- [ ] Blank threshold and decision-curve tables are approved before final access.
