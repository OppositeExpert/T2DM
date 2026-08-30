# Reproducibility and Final-Run Handoff

**State:** Development commands recorded; final commands remain authorization-gated

Run from the repository root with the project virtual environment active. Use a
project-local Matplotlib cache:

```bash
export MPLBACKEND=Agg
export MPLCONFIGDIR=outputs/.matplotlib
```

## Verified development studies

```text
PIDD:   outputs/publication_pipeline/studies/pidd_development_072cd2104089
Sylhet: outputs/publication_pipeline/studies/sylhet_development_b52477910fe6
BRFSS:  outputs/publication_pipeline/studies/brfss_development_holdout_56407ef53bba
Hospital130: outputs/publication_pipeline/studies/hospital130_development_holdout_c3aa5fb84a7a
```

The immutable identity of a result is the study identifier plus the raw-data,
configuration, split-manifest, and source-tree hashes in its metadata. Do not
copy a directory and rename it as another profile.

## Package regeneration

```bash
.venv-pipeline/bin/python scripts/build_conference_package.py
.venv-pipeline/bin/python scripts/build_development_evidence_snapshot.py
.venv-pipeline/bin/python scripts/build_conference_manifest.py
.venv-pipeline/bin/python scripts/build_study_registry.py
.venv-pipeline/bin/python scripts/build_artifact_release_manifest.py
.venv-pipeline/bin/python scripts/verify_artifact_release_manifest.py
.venv-pipeline/bin/python -m pytest -q
.venv-pipeline/bin/python scripts/run_publication_readiness_audit.py
```

The checksum manifest must be generated last. A changed file after manifest
creation invalidates the package manifest and requires regeneration.

## Final authorization preconditions

Before any final-profile run or any access to a newly concealed final holdout:

1. Complete novelty, claim-evidence, TRIPOD+AI, PROBAST+AI, ablation, selective-
   prediction, and subgroup reviews.
2. Approve the SAP, panels, endpoints, model bank, tuning spaces, calibration,
   thresholds, comparison families, margins, and subgroup suppression rules.
3. Create a signed authorization record and immutable code/configuration tag.
4. Set the final seed and create a new outcome-blind concealed manifest without
   inspecting final outcome performance.
5. Record and independently verify the manifest SHA-256.
6. Set the final-profile lock and execution authorization only after sign-off.

The precise two-stage split-creation and execution procedure is maintained in
`FINAL_RUN_CHECKLIST.md`. Use `scripts/final_preflight.py --dataset brfss` to
compute the current raw-data and executable-analysis fingerprints without
loading outcomes; it must remain denied until every binding is present.

The runner is designed to fail closed if any prerequisite is absent. This is a
scientific safeguard, not an engineering defect.

## One-time final execution procedure

After authorization, an independent operator should:

1. Run the publication-readiness preflight and archive its output.
2. Execute each frozen final profile exactly once with complete logs.
3. Verify row flow, grouping, hashes, selected calibration, thresholds, model
   bundles, intervals, and non-finite-value checks before reading conclusions.
4. Run only prespecified dependent analyses; post-hoc exploration must be clearly
   separated and must not alter the primary claims.
5. Rebuild tables, figures, manuscript, supplement, checklists, and manifest.
6. Perform independent numerical, claim, accessibility, and page-render review.
7. Create the repository release tag and archive DOI.

## Recovery rule

Never rerun a final study merely because the result is disappointing. A rerun is
permitted only for a documented implementation or infrastructure failure that
invalidated the run, with the cause, affected artifacts, remediation, and new
authorization recorded before rerunning.
