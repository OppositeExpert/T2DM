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
- PIDD panel-specific retraining is an active full-budget job at this cutoff and
  must be marked complete only after artifact validation.
- Sylhet grouped pilots and BRFSS smoke studies exist but must not replace the
  planned full-budget development analyses.

## 3. Remaining machine-executable work

1. Validate the completed PIDD panel-specific retraining artifacts.
2. Run and audit the full-budget grouped Sylhet development benchmark.
3. Attach routing, matched panels, ablations, selective prediction, subgroups,
   missingness stress, leakage demonstration, and explanations to that study.
4. Review BRFSS compute requirements and run a protocol-consistent full
   development holdout; do not silently substitute the smoke sample.
5. Generate final development decision tables and figures from immutable study
   identifiers.
6. Run the complete test suite and publication-readiness audit.
7. Rebuild and render the DOCX manuscript and supplement after the development
   evidence tables stabilize.

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
3. Create concealed final manifests without inspecting outcome performance.
4. Record manifest hashes and the final authorization record.
5. Set `final_execution_authorized: true` only after independent approval.
6. Run each final profile once; preserve logs and immutable artifacts.
7. Run predefined analyses without adding post-hoc panels, models, or metrics.
8. Perform an independent artifact and claim audit.
9. Replace development placeholders in the manuscript and supplement.
10. Tag and archive code, configurations, manifests, and results.

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
**Go after gates:** submission is appropriate when the remaining full-budget
development studies are reviewed, the protocol and novelty position are signed,
the concealed final run is complete, and independent review confirms that every
claim matches the locked evidence.
