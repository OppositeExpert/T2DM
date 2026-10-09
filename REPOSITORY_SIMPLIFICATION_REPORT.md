# Repository simplification report

9 October 2026. Repository: [OppositeExpert/T2DM](https://github.com/OppositeExpert/T2DM).
Branch: `chore/repository-cleanup`; existing [PR #1](https://github.com/OppositeExpert/T2DM/pull/1).
This second cleanup changes active Git tracking. No valuable local file was
permanently deleted, no training was rerun, no locked result was rewritten,
and cleanup was not merged into `main`.

## 1. Verified starting state and preservation

The clean starting branch/PR head was `fb1e35d9df1113bc82fd75f9c0c640932735c87d`. The prior
cleanup report and branch history were inspected. Live GitHub verification and
the connector confirmed PR #1 open/unmerged, base `main`, head
`chore/repository-cleanup`.

- `main` and `backup/pre-repository-cleanup` both target
  `0a389237bfaf8fd62f35bcdae394b630418a4309`.
- Annotated `pre-cleanup-research-snapshot` tag object:
  `bf204775cd547ec0dbe7d5f7e8ddf07cf85ad58d`; peeled commit is the same preservation commit.
- The old private full archive still exists at
  `../T2DM-preservation/2026-10-09/complete-local-state.tar`. Its complete SHA-256
  was rechecked: `3e8477959fbcb7c990b36932207efe367b2b748a14464fcaa43c9ad5518e5f5f`.

Before untracking anything, two new archives were created **outside the Git
repository** under `../T2DM-local-archives/2026-10-09-simplification/`:

| Archive | Files verified | Compressed bytes | SHA-256 |
|---|---:|---:|---|
| pre-simplification-tracked-state.tar.gz | 465 | 18,601,679 | `7f5155e38697cb1999ff45bcc1cc206abd2e0007356b5dfda202962d68f02bd6` |
| conference_package.tar.gz | 49 | 9,969,396 | `5c5ce2f37c13035e056e5a766055c95cc64aa5c42a59d9e3ea17369034c22203` |

Every archive member was read back and compared with the original path's size
and SHA-256. The complete conference archive includes all 49 actual files, not
just a presumed filename subset. The two archives overlap: **465 unique original
tracked files** are preserved, including all **192 paths untracked** below.
All 192 original files also remain present and byte-identical locally.
`archive_verification.json` beside the archives records every original fingerprint.
These backups are local, not an off-site/immutable deposit; archives are not committed.

## 2. Original and final active structure

The original tree had 465 tracked files: 49 conference-package files, 57 docs,
204 publication-package files, 19 scripts, 68 source files, 33 test files,
13 configurations, four evidence files and supporting root/example/workflow files.
It mixed current results with progress reports, superseded exports, Word drafts,
rendered conference QA and first-cleanup bookkeeping.

The final active tree contains:

```text
src/diabetes_pipeline/          # complete research implementation
scripts/                       # acquisition, execution, export and verification
config/                        # unchanged contracts, profiles and protocols
tests/                         # original checks plus publication fingerprint regressions
examples/                      # synthetic inputs
.github/workflows/             # portable CI
results/final_publication/      # unchanged current frozen aggregate package
evidence/                      # scientific inventories, correction/reference evidence
  publication_correction/      # unique original derivatives and executed code
  development_reference/       # historical estimand test table and provenance
docs/                          # focused contributor guides and manuscript-review queue
  research/                    # scientifically relevant plans/decisions/literature
  audits/2026-09-05/            # integrity findings and evidence retained for review
README.md, CONTRIBUTING.md, pyproject.toml, requirements.lock,
Dockerfile, CITATION.cff, LICENSE_STATUS.md, final decision/checklist files
```

The [project structure guide](docs/PROJECT_STRUCTURE.md) maps all research stages.
The architecture, model logic, public APIs and configuration keys were not changed.

## 3. Untracked paths and removed active directories

**192 original paths, 31,802,374 bytes, removed from active tracking; zero local
files permanently deleted.** Exact paths, original hashes, reasons and 17
byte-identical active promotion mappings are in
[evidence/repository_simplification_manifest.json](evidence/repository_simplification_manifest.json).

| Group | Original paths untracked |
|---|---:|
| Block progress reports | 10 |
| Complete superseded publication package | 102 |
| Conference/Word report builders and renderer | 5 |
| First-cleanup audit bookkeeping | 10 |
| Historical diagnostic probes/instructions | 6 |
| Previous root cleanup report | 1 |
| Superseded project/baseline/status documents | 9 |
| conference_package/ | 49 |

Every directory that no longer contains active tracked material is listed here
(including nested historical directories; original directories remain local):

- `conference_package/`
- `conference_package/generated/`
- `conference_package/generated/figures/`
- `conference_package/qa/`
- `conference_package/qa/a11y/`
- `conference_package/qa/rendered/`
- `conference_package/qa/rendered/manuscript/`
- `conference_package/qa/rendered/supplement/`
- `docs/audits/2026-09-05/probes/`
- `docs/audits/repository-cleanup-2026-10-09/`
- `docs/progress_reports/`
- `results/final_publication/superseded_pre_protocol_correction/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/audits/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/executed_correction_code/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/figure/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/figure/data/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/original_study_derivatives/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/original_study_derivatives/pidd/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/original_study_derivatives/pidd/availability_routing/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/original_study_derivatives/sylhet/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/original_study_derivatives/sylhet/availability_routing/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/provenance/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/provenance/execution/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/provenance/execution/brfss/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/provenance/execution/hospital130/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/provenance/execution/pidd/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/provenance/execution/sylhet/`
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/tables/`

The prior root `REPOSITORY_CLEANUP_REPORT.md` and its large per-file audit are
historical records in the verified archive and Git history. This report replaces
them for active navigation. `git rm --cached` removed index entries only;
`.gitignore` alone was not relied on to untrack existing files.

## 4. Unique scientific material retained before untracking

- The conference's 20-row development primary-estimand CSV and source provenance
  were copied byte-for-byte to `evidence/development_reference/`. The existing
  participant-mean estimand/sample-count test still uses the same real data and
  assertions; its reporting-language checks now target the active manuscript guide.
- Claim-to-evidence, TRIPOD+AI and preliminary PROBAST+AI review work was
  consolidated in [MANUSCRIPT_REVIEW.md](docs/MANUSCRIPT_REVIEW.md), with explicit
  development status and a current unresolved-review queue. No compliance,
  authorship or current final sign-off was invented.
- The blank scientific authorization template was copied byte-for-byte to
  `docs/research/Execution_Authorization_Template.md`; it does not authorize a run.
- Ten original PIDD/Sylhet panel derivatives, two unique executed correction-code
  snapshots, the unchanged original 87-entry checksum list and the supersession
  mapping were copied byte-for-byte into `evidence/publication_correction/`.
  Its separate 14-entry support fingerprint index does not replace or alter the
  original publication checksum list.
- The complete current **102-file publication package** (101 registered files plus
  its checksum index) remains unchanged, including machine-readable metrics,
  CSV/Markdown/TeX tables, PNG/PDF/SVG figure and source data, calibration,
  comparisons, panel/routing, statistical, subgroup/selective and correction evidence.
- Final and development artifact manifests remain unchanged: 1,304 and 1,962
  private artifact/input/split/execution fingerprints. Development negative
  findings and mentor-analysis dependencies were not discarded.

Hospital130 remains separate patient-grouped 30-day readmission. Cross-cohort
probabilities are not pooled. Internal validation is not external/clinical
validation, SHAP is not causal, and retrospective DCA is not clinical benefit.

## 5. Documentation, script and reference changes

Current setup/acquisition/license/results/structure/contribution guides remain.
The runbook now maps actual commands without an old hard-coded study catalogue.
Superseded context/roadmap/baseline/status documents, block reports, Word report
copies and old cleanup bookkeeping are locally archived. Unique unresolved
scientific decisions remain in the manuscript queue and retained research records.

Four conference/Word report Python builders and one Word automation renderer were
untracked because their only outputs are archived packages/reports. Active
training, tuning, calibration, thresholding, inference, routing, abstention,
explainability, all statistical analyses, final orchestration/export/correction
and mentor-analysis code remain.

Corrected active references/dependencies:

- Release-governance tests use the promoted estimand CSV and current manuscript guide.
- Readiness-audit output now goes to ignored
  `outputs/publication_pipeline/reports/publication_readiness/`.
- Docker no longer copies the conference package and now includes the current
  publication package required by portable fingerprint tests. Its ignore rules
  exclude historical local material while preserving the required final figure PDF.
- Current documentation links lead to this report, active scientific records and
  archive restoration instructions. The retained September audit links its
  diagnostic instructions to the exact previous Git commit.
- Publication verification always checks the unchanged current manifest plus
  retained correction support. `--historical-results-root` explicitly verifies
  a restored full historical package and fails if requested files are absent or
  changed. No implicit success is claimed for an unavailable historical package.

No locked provenance path string was rewritten. Historical absolute/relative
paths retain their original meaning and resolve through the archive/promotion
mapping. They are not promises of a private artifact download in a fresh clone.

## 6. TeX investigation and GitHub Linguist

The reported GitHub 91.2% TeX signal is explained by verbose **generated tabular
exports**, particularly superseded confidence-interval tables, rather than a
large handwritten manuscript. Unfiltered Python/TeX suffix bytes before cleanup
imply 91.03% TeX; GitHub's selected ref, classification and cache can differ.

| Tracked language suffix | Before files | Before bytes | After files | After bytes |
|---|---:|---:|---:|---:|
| TeX | 43 | 9,872,978 | 23 | 4,713,875 |
| Python | 126 | 973,079 | 118 | 870,034 |

The 20 superseded table TeX files account for **5,159,103 bytes** and are locally
archived. All 23 retained TeX files are generated current tables with corresponding
CSV sources; they total **4,713,875 bytes**. No tracked handwritten manuscript TeX
was found. Current exports are retained because the locked publication index
binds them and manuscript review uses them. Removing them would break that
unchanged verification contract.

Largest TeX files originally:

- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/tables/model_performance_confidence_intervals.tex`: 2,077,807 bytes.
- `results/final_publication/tables/descriptive_threshold_confidence_intervals.tex`: 904,987 bytes.
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/tables/decision_curves.tex`: 857,289 bytes.
- `results/final_publication/tables/decision_curves.tex`: 857,289 bytes.
- `results/final_publication/superseded_pre_protocol_correction/2026-10-03/tables/decision_curve_paired_contrasts.tex`: 664,782 bytes.

Largest retained TeX files:

- `results/final_publication/tables/descriptive_threshold_confidence_intervals.tex`: 904,987 bytes.
- `results/final_publication/tables/decision_curves.tex`: 857,289 bytes.
- `results/final_publication/tables/decision_curve_paired_contrasts.tex`: 664,782 bytes.
- `results/final_publication/tables/model_performance_confidence_intervals.tex`: 483,513 bytes.
- `results/final_publication/tables/subgroup_confidence_intervals.tex`: 349,728 bytes.

`.gitattributes` marks only `results/final_publication/tables/*.tex` as
`linguist-generated=true`, tracing them to `publication/exporter.py::_write_table`.
Source code and handwritten manuscripts are not matched. This is accurate
classification of generated outputs, not removal to reach a desired percentage.
Unfiltered retained Python/TeX byte shares remain 15.58% / 84.42%.
GitHub's eventual displayed percentages are not asserted.

## 7. Tracking, size, ignore and dependency hygiene

| Measure | Before | After |
|---|---:|---:|
| Tracked files | 465 | 296 |
| Tracked logical payload bytes | 58,243,815 | 27,161,301 |
| Decimal MB | 58.243815 | 27.161301 |

Payload reduction: **53.37%**. Counts include this report and its provenance
ledger. They exclude `.git`, ignored data/artifacts/environments and external
local archives; retained Git history means total clone/history size does not
shrink by the same amount. No history rewrite or garbage collection was used.

Exact ignore rules protect the conference package, superseded full exports,
progress/cleanup/probe directories, archived individual documents/builders and
local archive directories. Raw data, private outputs/models/checkpoints,
environments, secrets and caches remain ignored. There is no global `*.tex`,
`*.csv`, `*.log` or experimental-result exclusion added. No archive is staged.

The obsolete optional `conference` dependency extra was removed. The exact
48-distribution `requirements.lock` and core dependencies remain unchanged;
legacy document packages in the frozen environment lock are retained for
provenance rather than silently rewriting its bound hash. No license was assigned.

## 8. Executed validation

| Check | Result |
|---|---|
| Full local suite with available raw/private study artifacts | **132 passed, 0 failed, 7 subtests passed**; 3 upstream SHAP warnings |
| Separate staged-source copy without conference/raw/private artifacts | **125 passed, 0 failed, 7 deselected, 7 subtests passed**; same 3 warnings |
| Original test coverage | All original 129 tests retained; three fingerprint integrity tests added; existing estimand assertions preserved |
| Package source imports / Python syntax | **67 modules imported / 118 tracked Python files compiled** |
| Configurations / CLI | YAML configurations and all five profiles valid; **26 subcommand help definitions** checked |
| Installation / packaging | Separate editable install, correct source binding, wheel build and `pip check` passed |
| Reference environment | All 48 locked distributions matched in the separate environment |
| Current publication fingerprints | **101/101** unchanged |
| Promoted correction-support fingerprints | **14/14** unchanged |
| Full locally retained historical publication fingerprints | **87/87** unchanged |
| Final private artifact inventory | **1,304/1,304** matched |
| Development private artifact inventory | **1,962/1,962** matched |
| Master-result source artifacts | **28/28** matched |
| Protected original active files | **189** source/config/result/governance/manifest files unchanged |
| Promoted originals / untracked local originals | **17 / 192** byte-identical |
| Archive member verification | **465/465** tracked snapshot members and **49/49** conference members matched |
| Internal Markdown links | **41** checked; zero broken links |
| Privacy/credential patterns | No matches in proposed active files; no raw/private/model/environment/archive path staged |
| Fingerprint failure behavior | Changed, missing, escaping and empty-manifest cases rejected by passing regression tests |
| Feature dictionary | Generated successfully in the isolated copy under ignored outputs |

Fresh Git-clone validation will be recorded after the validated simplification commit; the separate staged-source copy has already passed every portable check.

The isolated environments reuse the verified local dependency distributions while
installing a fresh editable package; a fresh network install of all dependencies
was not performed. Docker was unavailable, so no container build/run is claimed.
No expensive training, final evaluation, calibration or SHAP export was rerun,
and no locked output was overwritten. Help/config/hash checks do not establish
scientific validity or prove exact retraining.

## 9. Retained uncertainty and remaining concerns

The following remain active because their scientific importance or unresolved
review cannot be dismissed:

- September integrity findings and machine-readable audit evidence: individual
  closure against final code/artifacts still requires review; probes are archived.
- `docs/research/Decision_Log.md`, the draft statistical/endpoint/threshold plans
  and `config/publication_protocol.yaml`: preserve unresolved/historical design
  decisions and legacy guard contracts; final protocol takes precedence for
  completed internal validation, without changing old flags.
- Literature matrix/search protocol and novelty assessment: unique extraction
  work and unfinished independent novelty review.
- Development ablation findings, leakage/applicability audit, final audit protocol
  and execution deviations: preserve negative results, limitations and run history.
- The development artifact manifest: mentor analyses still need its provenance;
  it is not replaced by the final-study inventory.
- Generated current table/figure exports: retained under frozen fingerprints and
  current manuscript-review needs, even when their content overlaps CSV sources.

Exact frozen training-source recovery and approved external immutable archival
remain outstanding. The sibling `journal_readiness_revision/` manuscript package
was not changed or fully re-audited. Author-approved manuscript/metadata,
reporting and statistical review, authorship/license/data-use decisions and the
mentor-analysis completion gaps remain explicit in current guides. Hospital130,
BRFSS internal-validation and noncausal/nonclinical claim boundaries remain intact.

## 10. Collaboration conclusion and review references

Teammates can work on source/configuration/tests, inspect final findings and run
portable verification **without historical conference artifacts**. Full private
artifact replay and exact final retraining require additional approved materials;
no such completeness is inferred from portable tests. Use the cleanup branch
while PR #1 is under review. `main` was not modified by this second cleanup.

- Starting cleanup commit: `fb1e35d9df1113bc82fd75f9c0c640932735c87d`.
- Required simplification subject: `chore: streamline research repository for collaboration`.
- Branch: `chore/repository-cleanup`; [existing PR #1](https://github.com/OppositeExpert/T2DM/pull/1).
- Preservation branch/tag remain as recorded in section 1. No force push, merge,
  history rewrite, deletion of datasets/checkpoints or frozen-guard bypass occurred.
- Resolve the current reviewed tip with `git rev-parse chore/repository-cleanup`.
