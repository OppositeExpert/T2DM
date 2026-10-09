# T2DM research implementation

**Availability-Aware and Leakage-Controlled Evaluation of Predictive Models Across Heterogeneous Feature Schemas**

Research code and preserved evidence for a manuscript being prepared for
**Discover Computing**. The framework compares Logistic Regression, Random
Forest, XGBoost, LightGBM and CatBoost under cohort-specific feature contracts,
fold-local preprocessing, calibration, threshold selection, availability routing
and abstention. The active package is `src/diabetes_pipeline`.

| Cohort | Recorded prediction endpoint | Evaluation boundary |
|---|---|---|
| PIDD | Diabetes-positive label | Repeated nested internal validation |
| Sylhet | Early-stage diabetes-positive label | Repeated nested internal validation grouped by identical predictor profile |
| BRFSS | Self-reported diagnosed diabetes | Historical partition; internal validation only |
| Hospital130 | Readmission within 30 days | Patient-grouped internal validation; separate from diabetes status |

Probabilities are not pooled across cohorts. SHAP describes model associations;
retrospective decision curves do not establish clinical benefit. No external,
prospective, temporal or untouched independent final validation is claimed.
Dynamic model-family switching did not establish consistent Holm-corrected
superiority; that negative result remains preserved.

## Start here

1. [Project structure](docs/PROJECT_STRUCTURE.md) explains the implementation.
2. [Reproducibility](docs/REPRODUCIBILITY.md) covers installation, verification,
   execution boundaries and the limits of a fresh clone.
3. [Results guide](docs/RESULTS_GUIDE.md) distinguishes current publication
   evidence, historical experiments and private study artifacts.
4. [Data acquisition](docs/DATA_ACQUISITION.md) gives official sources, expected
   filenames, conversion steps and exact input hashes.
5. [Contribution instructions](CONTRIBUTING.md) describe safe collaboration and
   the remaining mentor-requested analyses.
6. [Runbook](docs/RUNBOOK.md) maps execution commands to research workflows.
7. [Manuscript review](docs/MANUSCRIPT_REVIEW.md) preserves review scaffolds and
   unresolved journal decisions.
8. [Simplification report](REPOSITORY_SIMPLIFICATION_REPORT.md) records local
   archives, active Git scope, validation and remaining concerns.

## Branch under review

PR #1 contains this simplified tree. Until it is merged, use the review branch:

```bash
git clone --branch chore/repository-cleanup https://github.com/OppositeExpert/T2DM.git
cd T2DM
```

The private repository requires your own authorized GitHub access. After review
and merge, use the agreed shared base branch.

## Install and verify

From the repository root, using Python 3.12:

```bash
python3.12 -m venv .venv-pipeline
source .venv-pipeline/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
python scripts/verify_environment.py
python -m pytest -q -m "not local_research_data"
python scripts/verify_publication_results.py
python -m diabetes_pipeline.cli --help
```

Raw data is acquired separately; verify existing local files with
`python scripts/acquire_data.py --dataset all`. See the acquisition guide before
using `--download`. The command above runs data-independent tests. After acquiring data and restoring the historical study artifacts, run
`python -m pytest -q` to include all seven local research-data checks. Neither
test path launches final training.

## Evidence included in a clone

[`results/final_publication/FINAL_RESULTS.json`](results/final_publication/FINAL_RESULTS.json)
and its [summary](results/final_publication/FINAL_RESULTS_SUMMARY.md) identify the
frozen `t2dm-final-internal-validation-v1` studies. The reviewed aggregate package
is tracked: tables, figure data, PNG/PDF/SVG figures, protocol, execution records,
correction provenance. Essential original correction inputs and executed-code
snapshots are retained in `evidence/publication_correction/`. Publication fingerprints are
verified without modifying those files.

Raw records, row-level predictions, split assignments and fitted models stay
local under `data/raw/` and `outputs/`. Their hashes and paths are recorded in
[evidence](evidence/README.md); an index is not a downloadable archive. Full
artifact restoration and exact retraining are not established by a clone alone.
The historical training source fingerprint differs from the retained packaging
source; final-execution guards must remain intact. See the reproducibility guide.

Historical conference packages, progress reports and superseded full exports
are archived outside active Git tracking. New contributors can install, run
portable tests and verify current results without those archives. Original Git
history remains available. Frozen metadata retains the earlier journal/title;
current submission metadata needs author review without rewriting the protocol.

## Governance

No software license has been approved. Read [LICENSE_STATUS.md](LICENSE_STATUS.md)
and [dataset-use notes](docs/LICENSE_AND_DATA_USE.md) before reuse or release.
`CITATION.cff` retains a contributor placeholder pending the approved author list.
This repository is a research prototype and does not support clinical decisions.
