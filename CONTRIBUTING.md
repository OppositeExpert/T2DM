# Contributing to T2DM

Four student researchers share this implementation. Read the README,
reproducibility guide and results guide before editing. No contributor roles or
author order are assigned by this repository.

## Work on a review branch

Create a branch from the agreed base, install the package in that checkout and
keep changes focused. Explain the scientific question, affected evidence tier,
configuration/source changes, validation and any change to an estimand in the
pull request. Include a regression test when changing a research contract or
behavior. Run `python -m pytest -q -m "not local_research_data"` (and the full suite when
local data/artifacts are available) and
`python scripts/verify_publication_results.py` before review.

Never change a result to improve a claim. Preserve negative findings and failed
attempts. Do not edit frozen metrics, protocol bindings, split manifests or
single-use receipts. New scientific analyses need a documented plan, successor
study/output paths and appropriate approval; they must not overwrite locked
publication evidence. Do not bypass guards to reuse a final experiment.

Raw data, row-level predictions, patient/group identifiers, fitted artifacts,
credentials and private environment files must remain outside Git. Review new
aggregate exports for privacy and provenance before adding them. Do not globally
ignore research results or run broad cleanup commands on ignored directories.

Hospital130 is a separate readmission task. Preserve cohort-native feature
semantics; do not describe SHAP as causal, internal validation as external, or
retrospective decision curves as clinical validation.

## Mentor-requested work to plan

| Analysis | Retained implementation/evidence | Remaining boundary |
|---|---|---|
| Independently retrained panel models | `evaluation/panel_training_ablations.py`, panel-specific development outputs and checkpoints | Current runner rejects locked studies and supports nested-CV development only; it does not complete all four final-cohort analyses |
| Fixed-model imputation comparisons | Fold-fitted median/indicator preprocessing, masked stress predictions and robust-fixed comparators | Existing median-imputed masked-panel comparisons do not establish a dedicated alternative-imputation experiment; define strategies and comparison estimand |
| Calibration ablations | `evaluation/ablations.py::calibration_ablation`, raw/calibrated predictions and development outputs | Final artifact-ablation outputs are absent for declared final studies; plan successor analysis rather than assume completion |
| Model-family switching ablations | `evaluation/ablations.py::model_family_ablation`, fixed/champion/router contrasts | Preserve negative Holm-corrected switching findings; do not claim superiority |
| Detailed routing tables | `routing/policy_evaluator.py`, private `policy_decisions.csv` and `participant_policy_predictions.csv`, aggregate fallback table | Derive reviewed aggregate summaries without publishing participant rows |
| Runtime fallback evaluation | `routing/policy_evaluator.py`, final `runtime_policy_evaluation/` outputs | Keep actual eligibility/coverage separate from fixed masked-panel performance |

Licensing, the approved author list in `CITATION.cff`, declarations and immutable
artifact/source archival remain human release decisions. Current code remains a
research prototype; maintain the limitation record when reporting new results.
