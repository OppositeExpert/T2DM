# Locked Final Run Checklist

This checklist is the human and machine gate for a future final execution. It
does not authorize a run. The repository currently remains deliberately locked
out: `protocol_frozen=false`, `config/experiments/final.yaml` has
`locked=false`, and `final_execution_authorized=false`.

The seed-42 BRFSS partition and every existing BRFSS study are development
evidence. They have already been inspected and can never become final evidence.

## A. Human scientific review before freeze

- [ ] Independently complete and approve the structured novelty review.
- [ ] Approve the endpoint and claim hierarchy; keep Hospital130 readmission
      separate from diabetes screening.
- [ ] Approve the SAP, model bank, search spaces, panels, calibration candidates,
      thresholds, bootstrap unit, comparison families, Holm correction, practical
      margins, selective-prediction policy, and subgroup suppression rules.
- [ ] Review all development ablation, routing, selective-prediction, subgroup,
      survey-sensitivity, and explanation evidence.
- [ ] Complete and sign the claim-evidence, TRIPOD+AI, and PROBAST+AI reviews.
- [ ] Record authorship, affiliation, declarations, venue, repository/archive,
      data-use, and code-license decisions.
- [ ] Define an immutable backup, log, and recovery location.

Only after those reviews may the corresponding completion flags be changed.
Passing code or the existence of an artifact is not sufficient evidence for a
human-review flag.

## B. Freeze code, data, and analysis configuration

1. Create a reviewed commit and immutable release candidate tag. Do not include
   ignored raw datasets, model outputs, credentials, or unrelated folders.
2. Archive the source and record its SHA-256 in the completed authorization
   record.
3. Set a new prespecified final holdout seed. It must not be 42.
4. Update `config/experiments/final.yaml` with that seed and the reviewed final
   budget, then set `locked: true`.
5. Set `analysis_plan.status: frozen`, `protocol_frozen: true`, and only the
   reviewed completion flags in `config/publication_protocol.yaml`.
6. Set `analysis_plan.final_split_creation_authorized: true` while keeping
   `analysis_plan.final_execution_authorized: false`.
7. Run the complete test suite and archive the output before creating a split.

Any later change to source code, the dataset configuration, the final profile,
or `requirements.lock` changes the analysis-configuration fingerprint and
requires a new review and authorization record.

## C. Create and register the concealed final manifest

Run exactly once from the frozen checkout:

```bash
python -m diabetes_pipeline.cli create-final-concealment --dataset brfss
```

The command refuses seed 42, refuses an unlocked profile, refuses overwrite,
and writes only row identity and split-role information. It does not persist
labels, event counts, or prevalence and it does not authorize test access.

- [ ] Have a second person verify that the CSV contains no outcome field.
- [ ] Independently verify the emitted manifest SHA-256 and metadata.
- [ ] Record the manifest path and hash in `analysis_plan.final_holdout_manifest`
      and `analysis_plan.final_holdout_manifest_sha256`.
- [ ] Set `analysis_plan.final_split_creation_authorized: false` after creation.
- [ ] Record the exact raw-data SHA-256 under
      `analysis_plan.final_raw_data_sha256.brfss`.

Do not inspect final event counts, prevalence, model predictions, metrics, or
figures during this stage.

## D. Complete the authorization record and machine bindings

1. Complete a versioned copy of
   `conference_package/Final_Authorization_Record_Template.md` and obtain the
   named approvals.
2. Record its path and SHA-256 in
   `analysis_plan.final_authorization_record` and
   `analysis_plan.final_authorization_record_sha256`.
3. Run the read-only preflight for each authorized dataset to obtain the current
   executable fingerprint. PIDD and Sylhet do not require a concealed holdout
   manifest, but their final repeated-CV runs remain authorization-gated:

```bash
python scripts/final_preflight.py --dataset brfss
python scripts/final_preflight.py --dataset pidd
python scripts/final_preflight.py --dataset sylhet
```

4. Record each emitted `analysis_configuration_sha256` under the matching key in
   `analysis_plan.final_analysis_configuration_sha256`.
5. Set `analysis_plan.final_execution_authorized: true` only after the completed
   record authorizes that exact raw hash, manifest hash, seed, profile,
   configuration fingerprint, command, operator, and one execution.
6. Run the preflight again. It must report `authorized: true` and
   `outcome_accessed: false`.

The preflight and both benchmark runners independently reject a mismatched data
hash, altered required manifest or metadata, wrong dataset, wrong holdout seed,
non-final manifest purpose, changed executable configuration or model bank,
changed authorization record, unlocked profile, or incomplete protocol flag.

## E. One-time execution

Use a fresh log and do not run the final command until the operator and reviewer
are present:

```bash
python -m diabetes_pipeline.cli benchmark-holdout \
  --dataset brfss --profile final \
  --models logistic_regression random_forest xgboost lightgbm catboost
```

Immediately before test prediction, the runner creates
`FINAL_TEST_ACCESS_STARTED.json` using exclusive creation. Its presence blocks
automatic re-execution for the same study even if the first process later
fails. Never delete or edit that receipt.

- [ ] Archive stdout/stderr, environment verification, preflight output, and
      start/end timestamps.
- [ ] Verify row flow, group leakage checks, finite probabilities, calibrated
      probability range, model-bundle reloads, artifact checksums, and expected
      artifact inventory before interpreting results.
- [ ] Run only prespecified dependent analyses.
- [ ] Record every deviation without changing the frozen primary analysis.

## F. Post-run review and release

- [ ] Independently reproduce reported tables from prediction artifacts.
- [ ] Review paired uncertainty, decision curves, calibration, thresholds,
      subgroup suppression, event retention, survey sensitivity, and SHAP scope.
- [ ] Replace development estimates only where locked final evidence exists;
      retain explicit development labels elsewhere.
- [ ] Re-run publication readiness, tests, bundle-reload verification, data and
      environment verification, document accessibility checks, and page renders.
- [ ] Rebuild the package checksum manifest last.
- [ ] Obtain author and independent reviewer sign-off before submission.
- [ ] Create the immutable release/archive and record its DOI or archive ID.

## Recovery rule

A disappointing result is never grounds for a rerun. If an implementation or
infrastructure failure invalidates the run, stop; preserve the receipt and all
partial artifacts; document the cause and affected evidence; repair and
re-freeze the code; obtain a separate signed rerun authorization; then create a
new immutable execution identity. No automated cleanup or overwrite is allowed.
