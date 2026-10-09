# Cleanup audit evidence

Audit date: 9 October 2026. The inventory covers all 27,670 initial local project
file paths, including ignored and untracked files. Git internals are captured by
the full private snapshot and Git-reference records rather than classified as
research files. Symlink targets in the installed environment are hashed from the
unchanged local runtime; the snapshot preserves the links.

| Category | Initial files | Decision |
|---|---:|---|
| KEEP | 6,035 | Retain implementation, contracts and scientific evidence |
| ARCHIVE | 171 | 171 historical files already retained in place; no moves |
| GENERATED | 21,460 | Only 158 verified caches/metadata removed; environment kept |
| REDUNDANT | 0 | No scientific file demonstrated unnecessary |
| REVIEW | 4 | Known historical narrative needing current-claim reconciliation; keep |

## Files in this audit

- `file_classification.csv.gz`: complete per-file A–K assessment, original size, SHA-256, static references and action. Decompress with any gzip tool or `gzip -dc`.
- `directory_summary.csv`: category counts and original bytes by root directory.
- `proposed_deletions.csv`: all 158 exact paths, reasons, reference/regeneration evidence, result impact, risk and pre-removal hashes.
- `removal_result.json`: actual deletion counts; no research evidence removed.
- `preservation.json`: original Git state, confirmed remote references and private snapshot fingerprint.
- `RESEARCH_DEPENDENCIES.md`: the 22 requested workflow stages, implementation/configuration paths, tests and limitations.
- `duplicate_review.csv`: byte-identical non-environment groups retained because provenance/context may differ.
- `validation.json`: executed checks and honest omissions.

Every initial project file was read for hashing. Project text was read for
static references/credential patterns, Python parsed, and CSV schemas inspected.
Binary artifacts were fingerprinted without executing pickle/joblib contents.
The installed third-party environment was classified by package/runtime role,
not audited line by line for third-party vulnerabilities. Historical DOCX/PDF/PNG
research evidence was retained rather than restyled or regenerated.

An absent static reference does not prove an artifact is unused. Runtime-created
paths, source hashes, report manifests, negative findings and future mentor
analyses are all reasons to preserve it. CSV/Markdown/LaTeX tables and PNG/PDF/SVG
figures have distinct export purposes. No broad cleanup of ignored outputs occurred.

## Manual review

- `docs/NEXT_STEPS_PUBLICATION_ROADMAP.md`: reconcile dated status claims before using it as current evidence; original content retained.
- `docs/DEFINITIVE_PROJECT_CONTEXT.md`: reconcile dated status claims before using it as current evidence; original content retained.
- `docs/research/Publication_Blocker_Register.md`: reconcile dated status claims before using it as current evidence; original content retained.
- `docs/research/Execution_Status.md`: reconcile dated status claims before using it as current evidence; original content retained.

The manuscript package in the sibling `journal_readiness_revision/` is outside
the repository. Its full claim/cell reconciliation, exact executed-source recovery,
licensing/authorship decisions and an approved immutable deposit remain outstanding.
A local backup is not off-site archival.
