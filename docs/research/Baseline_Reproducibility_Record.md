# Baseline Reproducibility Record

> Historical snapshot. The root, Git state, study IDs, and blocker descriptions
> below record 23 August 2026 and are superseded for current operation by
> `README.md`, `docs/REPRODUCIBILITY.md`, `docs/research/Execution_Status.md`,
> and `evidence/study_registry.json`.

**Baseline ID:** `baseline-2026-08-23-phase0`

**Recorded:** 23 August 2026, Asia/Kolkata

**Project root:** `/Users/pranavprabhu/Codex/Minor Proj/XGBoost`

**Evidence role:** Development control record; not a final-study result

## 1. Baseline verdict

The current software baseline is operational and internally testable. Dataset contracts, endpoint ontology, deterministic split generation, saved study artifacts, routing, patient reporting, and the publication-readiness gate are present. The automated tests pass.

The scientific study is not ready for final execution. The readiness gate reports 16 blockers and one journal-strength warning. Existing PIDD and Sylhet studies are development pilots. Existing BRFSS and Hospital130 studies are smoke runs. None may be used as a final paper estimate.

## 2. Version-control status

No `.git` directory is present in the project or its immediate parent directory. A commit identifier and immutable tag therefore cannot be recorded for this baseline.

This is a reproducibility blocker before protocol freeze. Until version control is initialized or the source tree is archived immutably, the pipeline's internal source hash is the only implementation identifier.

## 3. Implementation and configuration fingerprints

### Source package fingerprint

`source_tree_sha256()` covers all Python files under `src/diabetes_pipeline`.

- Source-tree SHA-256: `3d33b5d7539396c84aa46c692517241e2723af9b5362216bc94168989af0af17`

### File fingerprints

| File | SHA-256 |
|---|---|
| `pyproject.toml` | `f2608d9752a802865e7a358255a92af755acd298788d994f0220883d62020d7c` |
| `config/availability_scenarios.yaml` | `d767b80e15ced4c3b3201077c2736f559bc93b9a48fc8907435b0d30e5ff0288` |
| `config/datasets.yaml` | `eb5be0f09aeb1eaaf811a23a5a2ae5a631d9ec0670b66eaef080c4aecc2f68db` |
| `config/feature_ontology.yaml` | `8fc0db7300f5b253a05d8d89e1c25dab60f187ede92fe87e57bc12fa1ff95e26` |
| `config/output_schemas.yaml` | `8ec4900a402b2ff1806130b6974ab66bbfda0dfc6b64e57b8b7b211e1dd38379` |
| `config/publication_protocol.yaml` | `584743293e5e2ed39e1ff97dd22987d72b2720d831f10c3bc6c5c3b92dbcb5ae` |
| `config/experiments/development.yaml` | `8af81b19c56ba1f92cfab1ddddae8b904d4405e6825b0161f7624db0ecab3ae7` |
| `config/experiments/development_pilot.yaml` | `047ee371ab3916faca1d9fc210cd2d3ee9334daea53537f2503793b6b4f58e83` |
| `config/experiments/final.yaml` | `0032c7a773cf84ab602296d0697291a6e45c0f25052fd6e779f4423951b8a450` |
| `config/experiments/smoke.yaml` | `8d14e53f19de4f46ada64041871b4d6c35491b36ccbedf5360fcbc4493b63578` |

The final profile remains intentionally unlocked: `locked: false`.

## 4. Environment

| Component | Recorded value |
|---|---|
| Platform | macOS 26.4, arm64 |
| Python | 3.12.0 |
| NumPy | 2.5.2 |
| pandas | 3.0.5 |
| SciPy | 1.18.0 |
| scikit-learn | 1.9.0 |
| matplotlib | 3.11.1 |
| SHAP | 0.52.0 |
| Optuna | 4.9.0 |
| XGBoost | 3.4.1 |
| LightGBM | 4.7.0 |
| CatBoost | 1.2.10 |
| joblib | 1.5.3 |
| PyYAML | 6.0.3 |

The complete environment snapshot is stored in `docs/research/requirements-baseline-2026-08-23.txt`.

### Environment warnings

- The default user Matplotlib directory is not writable in this execution environment. All research commands must set `MPLCONFIGDIR=outputs/.matplotlib` or use an equivalent project-controlled writable cache.
- The user pip cache is not writable. Package installation still works with caching disabled, but clean-environment reproduction should use a writable, project-specific cache or no cache.
- The package is installed editable from the local project and has no version-control identifier.

## 5. Capacity snapshot

| Item | Size/value |
|---|---:|
| Available filesystem space | 150 GiB |
| Raw data directory | 535 MiB |
| Current outputs | 643 MiB |
| Project virtual environment | 730 MiB |

The available space is sufficient for development work, but final-run preflight must estimate model, prediction, SHAP, plot, and bootstrap output growth before execution.

## 6. Verification results

### Automated tests

Command:

```bash
MPLCONFIGDIR=outputs/.matplotlib .venv-pipeline/bin/python -m pytest -q
```

Result:

- 36 tests passed.
- 5 subtests passed.
- 3 warnings from SHAP's use of Matplotlib color-map methods pending deprecation.
- Runtime: 4.07 seconds.
- No project test failed.

### CLI and feature ontology

- The CLI loaded successfully and exposed all expected commands.
- The feature ontology regenerated successfully.
- Dictionary rows: 91.
- Dictionary SHA-256: `ae80751c51e83e113a1d6867bcc64041064958c6012c8286e11a08bd622a9c40`.
- Endpoint pooling remains prohibited without a separately validated harmonized model.

### Dataset audits and deterministic splits

`block-a --dataset all --seed 42` completed successfully for all datasets.

| Dataset | Retained rows | Positives | Prevalence | Predictors | Key grouping/missingness fact |
|---|---:|---:|---:|---:|---|
| BRFSS | 429,360 | 57,256 | 13.335% | 21 | 182,289 rows have at least one missing configured feature |
| PIDD | 768 | 268 | 34.896% | 8 | 376 rows have at least one physiological zero converted to missing |
| Sylhet | 520 | 320 | 61.538% | 16 | 251 exact-profile groups; largest group 16; 269 duplicate rows |
| Hospital130 | 99,343 | 11,314 | 11.389% | 46 | 69,990 patient groups; largest group 40; all rows miss at least one configured feature |

## 7. Raw-data fingerprints

| Dataset | Raw rows | Excluded rows | Raw SHA-256 |
|---|---:|---:|---|
| PIDD | 768 | 0 | `6bfe5d0f379d17a0e0819b996407e3c09bf80febd4287f2ed212190dfff154af` |
| BRFSS | 441,456 | 12,096 | `a7d3380aca5aeae94186770983c3089fb6c4b2074aa112418112c11891d16420` |
| Sylhet | 520 | 0 | `7889d9d0beb7dd1ccc58da99f72763f16afb259b5dbbaa086f8195366ff66137` |
| Hospital130 | 101,766 | 2,423 | `0689e7ec031237dc63031b938805c48377748761a3b26acab621567afa24df97` |

## 8. Split fingerprints and status

| Dataset | Strategy | Manifest SHA-256 | Scientific status |
|---|---|---|---|
| PIDD | Five repeats of five-fold stratified outer evaluation | `774f1aa295d71e607b555247543a8761662be7ab31ca03db43c355b2ed18d87d` | Valid development split; pilot results not final |
| Sylhet | Five repeats of five-fold identical-profile-grouped outer evaluation | `1c5e2f18959d00d947ebf0248399566cc9535a7307e6692992c8408f8196f496` | Valid development split; pilot results not final |
| BRFSS | Stratified holdout plus development CV | `047d0a8ad36f229ff1d74c8a2f5531f3123aee9cc480f708287ad2fa4265be1e` | Seed-42 test partition is development-contaminated by prior smoke evaluation and audit outcome summaries; do not use as fresh final test |
| Hospital130 | Patient-grouped holdout plus development CV | `6339ee87b228d61f351e56160591746448ed4052785ab8c035c7c42853371ca0` | Seed-42 test partition is development-contaminated by prior smoke evaluation and audit outcome summaries; do not use as fresh final test |

### Holdout control decision

The seed-42 BRFSS and Hospital130 partitions are now formally classified as development-only. A different, prespecified final partition must be created after the statistical protocol is frozen. The final-test path must not print, audit, summarize, or expose final-test outcomes before the authorized run.

## 9. Existing study evidence tiers

| Study | Profile | Evidence tier | Allowed use |
|---|---|---|---|
| `pidd_development_pilot_27b9bc88b493` | development pilot | Development only | Pipeline and analysis-design decisions |
| `sylhet_development_pilot_ed7c05460503` | development pilot | Development only | Pipeline and grouping/calibration decisions |
| `brfss_smoke_holdout_1f1344dceb63` | smoke | Execution only | Holdout-path verification; never final inference |
| `hospital130_smoke_holdout_6640beff7a08` | smoke | Execution only | Holdout-path verification; never final inference |

## 10. Publication-readiness baseline

- Verdict: `NOT READY`.
- Blocking checks: 16.
- Warnings: 1.
- Mixed-router claim scope: pass because it remains a software demonstration.
- Dynamic-model-selection claim scope: pass because it remains a secondary negative result.
- External/temporal validation: warning for conference scope and required for journal-strength transportability claims.

The detailed owner/action mapping is maintained in `docs/research/Publication_Blocker_Register.md`.

## 11. Phase 0 issues requiring action

| ID | Severity | Issue | Required resolution |
|---|---|---|---|
| BASE-001 | High | No version-control metadata | Initialize or restore version control before protocol freeze; tag the frozen final source |
| BASE-002 | High | Existing seed-42 holdouts have been observed through smoke runs/audits | Treat them as development-only and implement a concealed fresh-final split workflow |
| BASE-003 | Medium | Final profile is unlocked | Keep it unlocked until all development analyses and signed protocol artifacts are complete |
| BASE-004 | Medium | Matplotlib default cache is unwritable | Standardize a project-local `MPLCONFIGDIR` in runbook/preflight commands |
| BASE-005 | Medium | Outputs are large and currently local | Define immutable archive and backup policy for final artifacts |
| BASE-006 | Low | Three SHAP/Matplotlib pending-deprecation warnings | Track upstream compatibility; do not treat as a scientific failure |
| BASE-007 | Low | Editable local package has no release identifier | Create a frozen package/version identifier at protocol lock |

## 12. Phase 0 acceptance status

- [x] Current environment recorded.
- [x] Source and configuration hashes recorded.
- [x] Raw-data and split hashes recorded.
- [x] Full automated tests passed.
- [x] Feature ontology regenerated and validated.
- [x] All dataset audits and splits regenerated deterministically.
- [x] Current evidence tiers recorded.
- [x] Publication-readiness status recorded.
- [x] Contaminated development holdouts explicitly identified.
- [ ] Version-control/archive strategy completed.
- [ ] Concealed fresh-final holdout workflow implemented and tested using synthetic/development data.
- [ ] Immutable final-artifact backup strategy completed.

Phase 0 documentation is established. The three unchecked operational controls must be completed before Phase 7 protocol freeze, not before drafting the Phase 1 statistical analysis plan.

## 13. Post-baseline control addendum

On 23 August 2026, a local Git repository was initialized at the project root and
the source/documentation baseline was committed as `750bcff` (`Establish
publication pipeline baseline`). Raw data, generated outputs, the virtual
environment, caches, and Office temporary files are excluded. This closes the
absence-of-version-control portion of BASE-001 for ongoing development. A frozen
tag and immutable archive are still required at protocol lock.

The concealed-final control has since been implemented and tested on the known
seed-42 development partitions. This does not make those partitions final; it
only verifies the outcome-blind format and authorization path.
