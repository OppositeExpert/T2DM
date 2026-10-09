# Repository cleanup report

Audit and cleanup date: **9 October 2026 (Asia/Kolkata)**.
Repository: [OppositeExpert/T2DM](https://github.com/OppositeExpert/T2DM), private.
Cleanup branch: `chore/repository-cleanup`. Cleanup is prepared for review;
**it is not merged into main**.

## 1. Original condition

The checkout was on `main`, matching GitHub at
`c964664ddaa1e4a1fbc6dd72fde9dfb66fc88cfc`, with 15 commits. Its latest commit
was dated 30 August 2026. There were 216 tracked files, 34 modified tracked files,
30 untracked files and 27,424 ignored files. The only local branch was `main`;
the live remote advertised only `main` and no tags. `origin` used
`git@github.com:OppositeExpert/T2DM.git` for fetch and push.

Substantial later source, final-internal-validation, publication export and
October correction work was local. The broad `results/` ignore also excluded
valuable aggregate publication evidence. Ignored material included raw cohort
records, fitted models, row-level predictions, split manifests, trial ledgers,
failed-attempt logs, receipts, checkpoints and the local environment. Some
individual private files exceeded 500 MB. None was treated as disposable merely
because it was ignored or generated.

The initial working-tree file payload was **16,082,436,004 bytes** (16.082 GB,
14.979 GiB), excluding Git internals and the later backup. A compressed inventory
records every original local project file and its original fingerprint.

## 2. Preservation completed before cleanup

A complete private local tar snapshot was created before editing or deleting
anything, including `.git`, all raw/row-level artifacts, ignored files, the local
environment and caches. Symlinks were preserved as links. Location relative to
the repository:

`../T2DM-preservation/2026-10-09/complete-local-state.tar`

- Archive size: **16,156,211,200 bytes**.
- SHA-256: `3e8477959fbcb7c990b36932207efe367b2b748a14464fcaa43c9ad5518e5f5f`.
- Archive structure checked: 31,080 entries, 27,701 regular files, including Git
  index, raw data and final outputs. Initial Git status/branches/remotes/history
  and ignored paths are recorded beside the archive.
- This is a private local backup containing potentially sensitive records. It
  was **not uploaded**, and is not an off-site or immutable repository deposit.

The reviewed source changes and 204 aggregate publication files were committed
as `chore: preserve complete pre-cleanup research state`:

**`0a389237bfaf8fd62f35bcdae394b630418a4309`**.

Before cleanup began, an atomic, non-force push and subsequent live `ls-remote`
confirmed:

| Reference | Exact target |
|---|---|
| `main` | `0a389237bfaf8fd62f35bcdae394b630418a4309` |
| `backup/pre-repository-cleanup` | `0a389237bfaf8fd62f35bcdae394b630418a4309` |
| `pre-cleanup-research-snapshot` annotated tag object | `bf204775cd547ec0dbe7d5f7e8ddf07cf85ad58d` |
| Peeled tag commit | `0a389237bfaf8fd62f35bcdae394b630418a4309` |

The preservation commit tracks 450 files. Raw data, row-level predictions,
fitted bundles and the environment were excluded from Git. The backup branch
and tag remain intact. No history was rewritten.

## 3. Complete classification

[The audit index](docs/audits/repository-cleanup-2026-10-09/README.md) explains the
[complete per-file A–K assessment](docs/audits/repository-cleanup-2026-10-09/file_classification.csv.gz),
[directory summary](docs/audits/repository-cleanup-2026-10-09/directory_summary.csv),
[duplicate review](docs/audits/repository-cleanup-2026-10-09/duplicate_review.csv)
and [22-stage research dependency trace](docs/audits/repository-cleanup-2026-10-09/RESEARCH_DEPENDENCIES.md).

| Category | Original files | Disposition |
|---|---:|---|
| KEEP | 6,035 | Retained |
| ARCHIVE | 171 | Historical material retained at its existing paths |
| GENERATED | 21,460 | 158 verified caches/metadata removed; 21,302 environment files kept locally |
| REDUNDANT | 0 | No scientific file demonstrated unnecessary |
| REVIEW | 4 | Retained unchanged for current-claim reconciliation |
| **Total** | **27,670** | **27,512 original files retained** |

Every project file was read for hashing; project text was inspected for static
references and credential patterns, Python parsed, and 131 output CSV schemas
examined. Binary artifacts were fingerprinted without unsafe pickle/joblib
execution. Installed third-party files were classified by environment/package
role, not audited line by line for third-party vulnerabilities. Git internals
are preserved by the snapshot/reference record rather than presented as research
files. Manuscript references are marked uncertain where a direct connection
could not be established; a static-reference scan alone never justified removal.

There were 527 identical-hash groups overall, including 368 non-environment
groups. Equal bytes did not demonstrate unnecessary evidence: checkpoint/model
copies, before/after records, report formats and study contexts may have distinct
provenance. They were retained.

## 4. Removed and archived files

**158 files removed, 1,795,717 bytes total:**

- 146 verified CPython bytecode cache files, with source retained.
- 6 macOS Finder `.DS_Store` files.
- 5 pytest cache files.
- 1 machine-local Matplotlib font-discovery cache.

The [deletion ledger](docs/audits/repository-cleanup-2026-10-09/proposed_deletions.csv)
records every exact path, fingerprint, reason, reference evidence, regeneration
mechanism, result impact and risk. Each file's current fingerprint matched the
preserved snapshot before removal. All were ignored and low risk. Empty cache
directories were removed only after their files were removed.

**Newly archived or moved: 0 files.** The 171 ARCHIVE-classified historical files
already had meaningful paths and remain in place. Moving the conference package,
its rendered QA evidence or dated research records would break existing builders,
package manifests or historical references. No research output, trial ledger,
negative finding, failed attempt, model, dataset, split, manuscript or experiment
was deleted. All four REVIEW documents were retained.

## 5. Organization and retained functionality

The architecture and public API/configuration keys remain stable.
[PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md) maps the source, data flow and
evidence directories. The README now leads to installation, acquisition,
reproduction, results and contribution guides. Existing reproducibility,
structure, archiving, runbook and evidence guides were updated rather than
creating parallel duplicates. `docs/RESULTS_GUIDE.md` and `CONTRIBUTING.md` add the
missing evidence-tier and collaboration instructions.

The current aggregate package and its existing superseded archive are tracked.
CSV/Markdown/LaTeX tables and PNG/PDF/SVG figures remain distinct useful formats.
The master results, protocol bindings, before/after corrections, source figure
data, leakage audit, execution metadata, logs and receipts retain their original
bytes. The frozen protocol's earlier journal/title remains historical metadata;
current contributor-facing text uses Discover Computing and the requested title.

All 22 requested research stages retain their implementation/configuration/test
closure, as detailed in the dependency trace. Hospital130 remains separate
30-day readmission. PIDD/Sylhet probability aggregation, Sylhet profile-cluster
uncertainty, fixed-panel stress results and actual runtime fallback are clearly
distinguished. No probabilities are pooled across cohorts. Negative switching
findings and scientific limitations remain explicit.

`evidence/final_artifact_release_manifest.json` adds a **1,304-file** hash inventory
for final study artifacts and input/split/execution dependencies, including
checkpoints. It contains paths/hashes, not participant records or fitted models.
The original 1,962-artifact development manifest remains unchanged. Relative
receipt basenames are resolved inside their study directory; no missing receipt
was inferred from looking only at the repository root.

The only test changes are seven `local_research_data` markers and the pytest
import needed by them. Original method/assertion ASTs were checked to be
unchanged. CI now runs the complete portable suite plus publication fingerprints,
instead of an older incomplete explicit selection. Local full-suite execution
still exercises every original test. `scripts/verify_publication_results.py` is a
new standard-library-only read-only verifier; a deliberately modified temporary
copy was correctly rejected.

## 6. Git hygiene, licensing and data

`.gitignore` continues to exclude raw data, private outputs, caches and local
environments. It now permits the reviewed aggregate final package and adds common
local secret/environment, private-key, temporary/editor and build-output patterns.
There is no blanket `*.log` rule: execution logs can be scientific provenance.
The ignore file describes preservation rather than implying all results should
be discarded. Future aggregate additions still require content/provenance review.

All four raw-data hashes were verified. The acquisition guide and
`config/data_sources.yaml` retain official source records, exact filenames,
expected paths and preprocessing/conversion steps. No raw records or restricted
artifacts were added to Git. No dataset terms were newly granted by cleanup;
source/license records still require release review.

`LICENSE_STATUS.md` is unchanged: no software license has been approved.
`CITATION.cff` uses the requested research title, while retaining the contributor
placeholder and development version pending human authorship/release decisions.
No license, author identity, DOI, ethics approval or experimental result was
invented.

## 7. Executed validation

Machine-readable details are in
[validation.json](docs/audits/repository-cleanup-2026-10-09/validation.json).

| Check | Executed result |
|---|---|
| Reference environment | Python 3.12.0, all 48 locked distributions match |
| Full local suite after cleanup/test-marker edits | **129 passed, 7 subtests passed, 0 failed**; 3 upstream SHAP deprecation warnings |
| Separate copy with no raw data or private study outputs | **122 passed, 7 deselected, 7 subtests passed, 0 failed**; same 3 warnings |
| Imports and syntax | 67 package modules imported; 119 Python source/script/test files compiled |
| Configuration/CLI | Four contracts and five profiles loaded; 26 subcommand help definitions and top-level/final-orchestrator help checked |
| Editable installation | Installed successfully into isolated environment; import resolved to the separate source copy |
| Wheel build | Built `diabetes_publication_pipeline-0.1.0-py3-none-any.whl` successfully |
| Dependency consistency | `pip check`: no broken requirements |
| Feature dictionary | Generated successfully in the separate copy, outside preserved study outputs |
| Raw inputs | **4/4** expected SHA-256 hashes match |
| Current publication fingerprints | **101/101** match |
| Superseded publication fingerprints | **87/87** match |
| Master-result source-artifact fingerprints | **28/28** match |
| Historical development release inventory | **1,962/1,962** artifacts verified |
| Final artifact/input/dependency inventory | **1,304/1,304** artifacts verified |
| Verifier failure detection | Modified temporary summary correctly produced nonzero status |
| Scientific file preservation | 6,094 original scientific files rehashed; zero changed/missing |
| Internal file links | 42 checked; zero broken current or historical links |
| Credential/privacy checks | No selected credential-pattern matches in proposed Git files or 609 reachable historical blobs; no raw/private output/environment paths selected for Git |

The first separate-copy attempt found two additional data/artifact-dependent
tests beyond the five raw-data tests. Explicit markers corrected the portability
instructions/CI selection; no assertions were removed or weakened. The later
portable and full suites both passed.

The separate environment reused the already verified local dependency set while
installing a fresh editable project. A fresh network install of all dependencies
was **not** executed. Docker was unavailable, so no container build/run is claimed.
Wheel construction succeeded; standalone wheel execution outside a source
checkout is unsupported because configuration is resolved relative to source.
No expensive final training, calibration, SHAP, export or protocol-correction
workflow was rerun. No locked output was overwritten. Historical path references
are preserved and are not proof of portable exact replay.

## 8. Size and scope

- Initial project-file payload excluding `.git`/backup: **16,082,436,004 bytes**.
- Removed cache/metadata payload: **1,795,717 bytes**.
- Final project-file payload: **16,083,493,003 bytes** (16.083493 GB), measured at validation.
- Original files retained: **27,512**, including **6,210 research/source/governance
  files** and **21,302 local environment files**.
- Tracked files: **216 originally → 450 after preservation → 465**.

Size uses logical file bytes, following existing environment symlinks for the
same before/after convention; it is not disk allocation or download size. The
new compressed audit inventory and final evidence manifest add useful provenance.
A small net size increase is expected despite cache removal; research
preservation takes priority. The 16.16 GB local backup is outside the repository
and excluded from these totals.

## 9. Outstanding risks and manual review

1. **Exact executed training-source recovery:** none of the 16 reachable committed
   source states matched the frozen training fingerprint
   `7d5347cf4c10e50dceb201ad36527f6d1c3e2770bba364c15c9093bf97cc6a94`.
   The preservation/current active source fingerprint is
   `2bf35ec02600e20b6acc275be6b1ee56849f3dd8661cec065b67906ae7afd4f4`.
   Current packaging code and source excerpts are not a demonstrated complete
   executed-source snapshot. Recover it before claiming exact training replay;
   do not bypass frozen hash guards or rewrite old hashes.
2. **External archival:** manifests still truthfully report no upload/URI/DOI.
   Choose an approved immutable restricted archive and deposit permitted
   artifacts plus the complete executed source/configuration closure.
3. **Portability:** historical absolute paths need controlled restoration or
   adaptation in a successor working copy. Metadata is preserved unchanged.
4. **Manuscript closure:** the sibling `journal_readiness_revision/` package was
   left intact outside the Git repository. Full reconciliation against the
   final author-approved manuscript remains a review task. Frozen metadata
   retains Discover Applied Sciences; submission-facing metadata must be aligned
   to Discover Computing without rewriting the frozen record.
5. **Mentor analyses:** panel-specific retraining rejects locked profiles and is
   implemented for nested-CV development, not all four finalized cohorts.
   Dedicated alternative-imputation comparisons and final artifact-ablation
   outputs are not demonstrated complete. Calibration, model-family, routing,
   fallback, masked-panel and checkpoint code/evidence remains available.
6. **Governance:** author list, affiliations/declarations, software license,
   dataset-use review and independent scientific/statistical sign-off remain
   human decisions. A passing test/checksum is not clinical or external validation.
7. **Four REVIEW files, kept unchanged:** `docs/DEFINITIVE_PROJECT_CONTEXT.md`,
   `docs/NEXT_STEPS_PUBLICATION_ROADMAP.md`,
   `docs/research/Publication_Blocker_Register.md`, and
   `docs/research/Execution_Status.md`. Reconcile their dated status claims before
   using them as current evidence. Other dated reports are historical context.
8. **Audit limits:** credential detection is pattern-based, not proof against
   every possible secret; third-party environment internals were not subjected
   to a full security audit. Historical binary report layouts were not edited or
   regenerated. Source links/commands were checked at the documented evidence
   tier, without rerunning expensive analyses.

## 10. Collaboration next steps and exact review references

Review this cleanup PR, then agree contributor responsibilities without inventing
author roles. New contributors should use the README's portable verification
command, acquire permitted data separately, and restore approved artifacts only
when needed. Define mentor analyses in a successor plan/output location. Complete
source recovery, restricted archival, manuscript reconciliation and human
release decisions before presenting the repository as submission-complete.

- Original GitHub commit: `c964664ddaa1e4a1fbc6dd72fde9dfb66fc88cfc`.
- Preservation/base commit: `0a389237bfaf8fd62f35bcdae394b630418a4309`.
- Backup branch: `backup/pre-repository-cleanup`.
- Annotated tag: `pre-cleanup-research-snapshot` (targets preservation commit).
- Cleanup branch: `chore/repository-cleanup`.
- Primary cleanup commit: `e1aadf63bf9a5e93c610df075cfb3082c7e33bb9`.
- Required cleanup commit subject: `chore: organize and clean research repository`.
- Pull request: PR_URL_PENDING.
- The branch tip may include a subsequent report-only commit recording the PR
  URL and primary cleanup SHA. Resolve it with `git rev-parse chore/repository-cleanup`.
- `main` retains the preservation commit; cleanup is not automatically merged.
