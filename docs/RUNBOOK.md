# Publication Pipeline Commands

Run commands from the `XGBoost` directory.

## Environment

```bash
source .venv-pipeline/bin/activate
export MPLCONFIGDIR=outputs/.matplotlib
```

The project-local Matplotlib cache is required in restricted or clean execution
environments where the default user cache is not writable. Keep this variable
set for tests, benchmarks, routing evaluation, explanations, and reporting.

## Master feature and endpoint dictionary

```bash
python -m diabetes_pipeline.cli feature-map
```

This validates and writes a 91-row dictionary covering every configured input
in all four datasets. It distinguishes direct measurements, binned forms,
proxies, non-comparable fields, and dataset-specific inputs. Routing must choose
the endpoint before dataset or algorithm: Hospital130 is a separate readmission
task, and probabilities from different cohorts are not pooled without a
separately validated harmonized model.

## Tests

```bash
python -m pytest -q
```

## Dataset audits and split manifests

```bash
python -m diabetes_pipeline.cli block-a --dataset all --seed 42
```

## Research data and leakage audit

```bash
python -m diabetes_pipeline.cli research-audit --seed 42
```

This records outcome-specific missingness, duplicate/profile and patient-group
integrity, BRFSS survey-design availability, and the fact that ordinary seed-42
manifests expose outcomes and are development-only.

## Outcome-blind manifest control test

```bash
python -m diabetes_pipeline.cli test-concealment --dataset brfss --seed 42
python -m diabetes_pipeline.cli test-concealment --dataset hospital130 --seed 42
```

These commands test the concealment format on already-known development splits.
They do not create a final holdout. Scientific holdout execution additionally
requires a frozen protocol, locked final profile, authorized seed, checksum-locked
manifest, and signed authorization record.

## PIDD smoke benchmark

```bash
python -m diabetes_pipeline.cli benchmark --dataset pidd --profile smoke
```

Smoke results verify the execution path and must not be used as final paper estimates.

## PIDD five-fold development pilot

```bash
python -m diabetes_pipeline.cli benchmark --dataset pidd --profile development_pilot
```

This profile runs five outer folds, five inner folds, five tuning trials per
model/fold, and 200 stratified bootstrap resamples. It is suitable for checking
the complete evaluation design, but its reduced tuning and resampling budgets
mean it is still not the locked final paper experiment.

Each study directory contains:

- Held-out raw and calibrated probabilities.
- Fold metrics and pooled bootstrap confidence intervals.
- Cross-fitted calibration-method selection evidence.
- Fixed, development-Youden, and sensitivity-constrained thresholds.
- Decision-curve data and ROC, precision-recall, calibration, probability, and
  decision-curve figures in PNG and SVG.
- Paired fold comparisons with Holm-adjusted Wilcoxon p-values.
- Complete preprocessor/model/calibrator/threshold bundles.
- Participant-aggregated repeated-CV predictions, confidence intervals, and paired
  comparisons; Sylhet uses complete identical-profile cluster resampling.
- Dataset, split, source-code, and raw-file checksums.

Latest verified development pilot:
`outputs/publication_pipeline/studies/pidd_development_pilot_27b9bc88b493/`.

## Held-out SHAP explanations

```bash
python -m diabetes_pipeline.cli explain \
  --dataset pidd \
  --study-dir outputs/publication_pipeline/studies/pidd_development_pilot_27b9bc88b493
```

The explanation command uses only each bundle's outer-fold validation patients
for reported SHAP values. It writes global and fold-specific importance,
patient-level top contributors, fold-to-fold stability, exploratory dependence
bins, additivity checks, and PNG/SVG figures under the study's `explanations/`
directory. Exploratory contribution transitions are relative to a model
baseline and must not be presented as clinical cutoffs.

## Feature-availability routing evaluation

```bash
python -m diabetes_pipeline.cli evaluate-routing \
  --dataset pidd \
  --study-dir outputs/publication_pipeline/studies/pidd_development_pilot_27b9bc88b493

python -m diabetes_pipeline.cli evaluate-routing \
  --dataset sylhet \
  --study-dir outputs/publication_pipeline/studies/sylhet_development_pilot_ed7c05460503

python -m diabetes_pipeline.cli evaluate-routing \
  --dataset brfss \
  --study-dir outputs/publication_pipeline/studies/brfss_smoke_holdout_1f1344dceb63

python -m diabetes_pipeline.cli evaluate-routing \
  --dataset hospital130 \
  --study-dir outputs/publication_pipeline/studies/hospital130_smoke_holdout_6640beff7a08
```

This evaluates Random Forest, XGBoost, LightGBM, and CatBoost under predeclared
feature panels. PIDD and Sylhet use their repeated outer-fold design, including
fixed-model baselines, bootstrap intervals, and paired comparisons. BRFSS and
Hospital130 use development-fold selection followed by one locked test
evaluation, matching their holdout contracts. Both paths save reloadable
routing bundles, supported-panel inference metadata, and explicit abstention
when no panel matches.

## Detailed patient research result

Use a local JSON file for patient input so values are not placed directly in
shell history. The command does not persist the input or output unless
`--output` is supplied.

```bash
python -m diabetes_pipeline.cli patient-result \
  --dataset pidd \
  --routing-dir outputs/publication_pipeline/studies/pidd_development_pilot_27b9bc88b493/availability_routing \
  --patient-file examples/pidd_patient_synthetic.json \
  --format markdown \
  --output outputs/pidd_patient_synthetic_result.md
```

The report uses all five outer-fold routers as a research ensemble and gives:

- Mean calibrated probability and model-fold spread, rather than only a class.
- The operating threshold and fold agreement without calling it a diagnosis.
- The selected feature panel, models, and calibrators.
- SHAP factor direction and normalized within-fold importance.
- Unadjusted reference-cohort context for available numeric factors.
- Explicit abstention for unsupported panels, invalid values, and numeric values
  outside the observed reference range.

The bundled models are cross-validation research artifacts, not a final
deployment model. The fold range is model variation, not a confidence interval.

## Mixed-source patient probability

Mixed input is namespaced by dataset so fields such as `Age` cannot silently be
confused: PIDD and Sylhet store years, while BRFSS stores an age-group code. See
`examples/mixed_patient_synthetic.json` for the input shape.

```bash
python -m diabetes_pipeline.cli mixed-patient-result \
  --routing-dir pidd=outputs/publication_pipeline/studies/pidd_development_pilot_27b9bc88b493/availability_routing \
  --routing-dir sylhet=outputs/publication_pipeline/studies/sylhet_development_pilot_ed7c05460503/availability_routing \
  --routing-dir brfss=outputs/publication_pipeline/studies/brfss_smoke_holdout_1f1344dceb63/availability_routing \
  --patient-file examples/mixed_patient_synthetic.json \
  --prefer-dataset pidd \
  --format markdown
```

The command accepts any number of supplied attributes per dataset and selects
the largest evaluated feature panel contained in those attributes. It never
averages probabilities. If more than one dataset expert is eligible, the
default behavior is now to abstain because no matched multi-environment cohort
exists to validate automatic selection. `--prefer-dataset` records an explicit,
population-appropriate environment choice. The old heuristic remains available
only through `--allow-experimental-auto-selection` and its result is marked
ineligible for paper or clinical claims. Supplied fields not used by the
selected expert are returned explicitly.

Hospital130 cannot be included in this mixed screening command: its endpoint is
30-day readmission among diabetes encounters. The result schema already has an
`onset_age` target with status `not_implemented`; a future age-at-onset model can
populate that target without changing or destabilizing the percentage output.

## Publication-readiness gate

Run the gate before describing any results as final or manuscript-ready:

```bash
python -m diabetes_pipeline.cli publication-readiness \
  --study-dir outputs/publication_pipeline/studies/pidd_development_pilot_27b9bc88b493 \
  --study-dir outputs/publication_pipeline/studies/sylhet_development_pilot_ed7c05460503 \
  --study-dir outputs/publication_pipeline/studies/brfss_smoke_holdout_1f1344dceb63 \
  --format markdown \
  --output outputs/publication_readiness_audit.md
```

The gate rejects smoke/pilot profiles, unlocked protocols, incomplete ablations,
missing selective/subgroup analyses, absent claim traceability, and incomplete
TRIPOD+AI or PROBAST+AI review. External/temporal validation is a conference
warning and becomes mandatory for journal-strength transportability or clinical
claims. Protocol flags live in `config/publication_protocol.yaml` and must be
changed only after the corresponding signed-off artifact exists.

## Large and patient-grouped holdout studies

BRFSS and Hospital130 use a separate runner because their test partitions must
remain untouched until all development choices are locked.

```bash
python -m diabetes_pipeline.cli benchmark-holdout \
  --dataset brfss \
  --profile smoke \
  --models random_forest xgboost lightgbm catboost

python -m diabetes_pipeline.cli benchmark-holdout \
  --dataset hospital130 \
  --profile smoke \
  --models random_forest xgboost lightgbm catboost
```

The smoke profile outcome-stratifies at most 10,000 rows from each partition and
uses only two tuning trials and 50 bootstrap resamples. It verifies code paths
and must not be cited as scientific evidence. Non-smoke test access is rejected
until the experiment profile is explicitly locked.

The holdout runner writes development-only tuning/calibration/threshold
evidence, test predictions and metrics, individual or patient-cluster bootstrap
intervals, paired bootstrap model comparisons with Holm adjustment, decision
curves, plots, checksums, and reloadable bundles.

## Test-only SHAP for holdout studies

```bash
python -m diabetes_pipeline.cli explain-holdout \
  --dataset brfss \
  --study-dir outputs/publication_pipeline/studies/brfss_smoke_holdout_1f1344dceb63 \
  --maximum-samples-per-model 500
```

The background sample comes only from development rows, while all reported SHAP
values come only from held-out test rows. Both transformed-component and grouped
original-feature tables are written. The original-feature version should be the
primary interpretation for one-hot encoded Hospital130 variables. A single
locked test has no fold-stability estimate, which is recorded explicitly rather
than fabricated.
