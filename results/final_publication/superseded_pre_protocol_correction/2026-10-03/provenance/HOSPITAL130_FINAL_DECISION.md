# Hospital130 Final Decision

**Decision:** `HOSPITAL130_FINAL_STRATEGY = COMPLETE_FULL_INTERNAL_VALIDATION`

**Decision date:** 10 September 2026

## Scope and endpoint

Hospital130 remains a separate hospital-readmission analysis. The endpoint is
`readmission_within_30_days` among eligible diabetes-related hospital
encounters. It is not diabetes detection, is not pooled with the three screening
cohorts, and cannot validate screening performance.

## Feasibility determination

The current loader retains 99,343 eligible encounters from approximately 69,990
patients after the prespecified death/hospice exclusions. The implemented split
is patient grouped: encounters for one patient cannot cross the development and
evaluation partitions or prohibited development folds. The existing complete
development study demonstrated that all five model families, fold-local
preprocessing, calibration, thresholds, decision curves, patient-cluster
bootstrap inference, routing, and held-out SHAP can execute on the full cohort.
It was not limited to the earlier 10,000-row smoke path.

The finalized execution therefore uses the complete eligible cohort, all five
models, 75 Optuna trials per model, five patient-grouped development folds, and
2,000 patient-cluster bootstrap resamples. No sample limit is permitted.

## Evidence classification

The historical seed-42 evaluation partition and its outcomes were previously
inspected. Hospital130 can therefore support a complete finalized internal
validation, but not a genuinely untouched final-test claim. The required
evidence tier is `final_internal_validation` and the evaluation role is
`locked_internal_validation`.

## Fail-closed rule

Only complete-cohort artifacts that match the frozen raw-data, split,
configuration, source-tree, dependency-lock, protocol, trial-budget, and
bootstrap-budget hashes may enter the publication package. Smoke artifacts and
the earlier 30-trial/500-bootstrap development study are automatically excluded
from final numerical tables.

If the complete run or its verification fails, Hospital130 numerical evidence
must be omitted rather than replaced with smoke or development numbers. Any
methodological mention must continue to identify it as a distinct secondary
30-day-readmission task.
