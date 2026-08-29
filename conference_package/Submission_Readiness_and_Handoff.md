# Submission Readiness and Handoff

**Decision:** The engineering pipeline is close to conference-package complete,
but the scientific submission is not yet authorized. Development evidence may
guide decisions; it may not be relabelled as final evidence.

## 1. Completed engineering

- Dataset and endpoint contracts for PIDD, Sylhet, BRFSS, and Hospital130.
- Availability routers and reloadable panel/model bundles across all datasets.
- Namespaced mixed-input validation with explicit non-fusion and abstention.
- Probability-first patient output with provenance and future-compatible output
  schema; age-at-onset prediction remains out of scope.
- Nested/grouped validation, holdout manifests, calibration, thresholding,
  participant/cluster inference, decision curves, and paired comparisons.
- Artifact-based, retraining, leakage, panel, reporting, selective-prediction,
  subgroup, missingness-stress, and held-out explanation engines.
- Fail-closed publication readiness and final-execution authorization checks.
- Automated tests and reproducibility records.

## 2. Evidence completed at this cutoff

- Full-budget PIDD 5 x 5 nested development benchmark with five models.
- PIDD routing, matched panels, artifact ablations, missing-indicator retraining,
  selective prediction, age subgroups, missingness stress, leakage demonstration,
  held-out SHAP, and reporting ablations.
- PIDD panel-specific retraining is complete and validated across 25 outer
  folds, two model families, and five reduced panels.
- The full-budget grouped Sylhet benchmark is complete and validated; dependent
  routing, robustness, and panel-specific retraining analyses are complete.
- Full-sample BRFSS development study
  `brfss_development_holdout_56407ef53bba` contains the supported routing,
  robustness, survey-sensitivity, subgroup, selective-prediction, SHAP, and
  bundle-reload evidence. Its inspected seed-42 test role is permanently
  ineligible as a protected final holdout.

## 3. Remaining machine-executable work

No supported engineering or development analysis remains after the full BRFSS
run. The package has been regenerated from fixed development study identifiers,
structurally audited, and tested. The latest rendered page counts and visual QA
results are recorded in `qa/QA_REPORT.md`. Venue-template rendering must still be
repeated after the target format and final text are known.

## 4. Human authorization gates

The following cannot be completed automatically without author and supervisor
decisions:

- Verify the novelty search and approve the narrow contribution.
- Approve endpoints, practical panels, margins, subgroup thresholds, model bank,
  tuning spaces, and clinical threshold range.
- Complete and sign the TRIPOD+AI and PROBAST+AI reviews.
- Approve the protocol freeze and create the immutable authorization record.
- Authorize concealed final split creation and one-time final execution.
- Independently review final artifacts and approve claims.
- Supply authors, affiliations, contribution taxonomy, funding, conflicts,
  ethics wording, repository URL/DOI, and target-conference format.

## 5. Final-run sequence after authorization

1. Record the signed protocol artifact and hashes.
2. Set `protocol_frozen: true` only when the signed artifact exists.
3. Set a new non-42 seed and separately authorize concealed split creation.
4. Create the outcome-blind final manifest once; independently verify and record
   its hash without inspecting outcome performance.
5. Record raw-data, analysis-configuration, and signed-authorization-record hashes.
6. Run `scripts/final_preflight.py`; set `final_execution_authorized: true` only
   after independent approval and require the preflight to pass.
7. Run each final profile once; preserve the non-overwritable access receipt,
   logs, and immutable artifacts.
8. Run predefined analyses without adding post-hoc panels, models, or metrics.
9. Perform an independent artifact and claim audit.
10. Replace development placeholders in the manuscript and supplement.
11. Tag and archive code, configurations, manifests, and results.

## 6. Submission checklist

- [ ] Target venue and page/template rules confirmed.
- [ ] Author and affiliation block complete.
- [ ] Abstract within venue limit.
- [ ] Full-budget development decisions reviewed.
- [ ] Protocol frozen and signed.
- [ ] Final execution authorized and completed exactly once.
- [ ] All main claims trace to locked tables/figures.
- [ ] No cross-endpoint pooling or future-onset wording.
- [ ] Calibration, uncertainty, prevalence, and applicability accompany AUROC.
- [ ] Negative routing findings retained.
- [ ] Event and subgroup coverage accompany selective prediction.
- [ ] TRIPOD+AI checklist complete.
- [ ] PROBAST+AI assessment complete.
- [ ] References verified against full text and venue style.
- [ ] Repository release and archive DOI live.
- [ ] Manuscript and supplement rendered page-by-page without defects.
- [ ] Independent scientific and language review complete.

## 7. Go/no-go rule

**No-go today:** do not submit the current development package.  
**Go after gates:** submission is appropriate when the completed development
studies are reviewed, the protocol and novelty position are signed,
the concealed final run is complete, and independent review confirms that every
claim matches the locked evidence.
