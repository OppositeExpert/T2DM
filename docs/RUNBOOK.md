# Execution command map

Run from the source checkout after editable installation. Use
[REPRODUCIBILITY.md](REPRODUCIBILITY.md) for setup, data/artifact restoration and
verification limits. Existing final studies and canonical publication outputs
are preserved evidence. Writing commands belong in a separate working checkout
with a reviewed successor analysis and fresh output paths. No command here
authorizes replay of the frozen final evaluation.

## Read-only checks

```bash
python scripts/verify_environment.py
python -m pytest -q -m "not local_research_data"
python scripts/verify_publication_results.py
python -m diabetes_pipeline.cli --help
python scripts/run_final_internal_validation.py --help
```

After permitted raw data and private historical artifacts are available, run
`python -m pytest -q` for all tests. `python scripts/acquire_data.py --dataset all`
verifies existing raw fingerprints; acquisition instructions are in
[DATA_ACQUISITION.md](DATA_ACQUISITION.md).

## Implementation commands

Inspect the selected command's `--help` for required options. The following names
are actual CLI entrypoints; a command map is not evidence that an expensive
analysis was executed or that a final result exists.

| CLI subcommand | Purpose / required scope |
|---|---|
| `feature-map` | Generate the feature/endpoint dictionary under ignored outputs |
| `block-a`, `research-audit`, `test-concealment` | Dataset/split audits, survey/missingness/group controls, outcome-blind manifest tests |
| `benchmark` | Nested/grouped model tuning, training, calibration and thresholds |
| `benchmark-holdout` | Large/patient-grouped cohort evaluation with profile/authorization controls |
| `explain`, `explain-holdout` | Held-out SHAP with the matching dataset/study |
| `evaluate-routing`, `evaluate-runtime-policy` | Fixed panels versus actual eligibility/fallback policy; distinct estimands |
| `matched-panel-contrasts` | Paired participant/group-preserving reduced-panel comparisons |
| `artifact-ablations` | Calibration, selector and model-family contrasts using study artifacts |
| `missing-indicator-ablation`, `panel-training-ablation` | Independently tuned unlocked nested-CV development variants; locked/holdout profiles unsupported |
| `selective-prediction`, `subgroup-analysis` | Coverage, positive-event retention, subgroup intervals and suppression |
| `missingness-stress`, `leakage-demonstration`, `reporting-ablations` | Prespecified development sensitivity/diagnostic analyses |
| `brfss-survey-sensitivity` | BRFSS survey-weighted estimand and uncertainty |
| `patient-result`, `mixed-patient-result` | Synthetic/research inference examples; no clinical use or cross-cohort fusion |
| `publication-readiness` | Governance/readiness audit; passing software checks do not close human decisions |

For example, inspect options without running training:

```bash
python -m diabetes_pipeline.cli benchmark --help
python -m diabetes_pipeline.cli panel-training-ablation --help
python -m diabetes_pipeline.cli evaluate-runtime-policy --help
```

## Script entrypoints

- `scripts/acquire_data.py`: official-source acquisition/conversion and hashes.
- `scripts/verify_environment.py`, `verify_artifact_release_manifest.py`,
  `verify_publication_results.py`, `verify_holdout_bundles.py`: verification.
- `scripts/run_final_internal_validation.py`: final orchestration; `--study-dir`
  performs writing analyses and is not a read-only verifier.
- `scripts/export_final_publication_results.py`,
  `correct_publication_protocol_summaries.py`, `plot_consolidated_results.py`:
  writing export/correction tools; preserve existing locked outputs.
- `scripts/build_study_registry.py`, `build_artifact_release_manifest.py`:
  build inventories from restored artifacts; do not regenerate frozen evidence
  merely to make path/configuration changes appear consistent.
- `scripts/run_publication_readiness_audit.py`: writes an audit under ignored
  `outputs/publication_pipeline/reports/publication_readiness/`.
- `scripts/final_preflight.py`: legacy concealed-final profile guard check.
- `scripts/migrate_development_evaluation_roles.py`: exact legacy-role migration,
  retained for research traceability and regression tests.

`config/final_publication_protocol.yaml` and current frozen provenance govern
completed internal validation. The older `config/publication_protocol.yaml` and
`final` profile remain distinct draft/concealed-profile controls. Do not change
flags, raw/split/source hashes or one-way receipts to bypass those guards.
