# Audit probe record

These are the diagnostic scripts executed for the 5 September 2026 repository audit. They are evidence for particular observations, not a replacement test suite or new research results. They use the audited checkout and its existing ignored data/artifacts. Absolute paths deliberately identify that checkout; change `ROOT` only when checking a verified restored copy.

Run from `/Users/pranavprabhu/Codex/Minor Proj/T2DM` with the existing `.venv-pipeline` environment. The scripts write only temporary probe outputs under `/private/tmp/t2dm-final-audit-20260905`, apart from console output. Create that directory first if it has been removed. A full clone without raw/study artifacts cannot execute the artifact-dependent probes.

```bash
mkdir -p /private/tmp/t2dm-final-audit-20260905
PYTHONPATH=src:. .venv-pipeline/bin/python docs/audits/2026-09-05/probes/data_probes.py
PYTHONPATH=src:. .venv-pipeline/bin/python docs/audits/2026-09-05/probes/runtime_probes.py
PYTHONPATH=src:. .venv-pipeline/bin/python docs/audits/2026-09-05/probes/followup_probes.py
PYTHONPATH=src:. .venv-pipeline/bin/python docs/audits/2026-09-05/probes/artifact_probes.py
PYTHONPATH=src:. .venv-pipeline/bin/python docs/audits/2026-09-05/probes/smoke_probe.py
```

| Script | Purpose |
|---|---|
| `data_probes.py` | Loaded cohorts, subgroup row-ID alignment, local/stored split paths and hashes, actual group overlap, split-position corruption and initial loader/ICD probes |
| `runtime_probes.py` | Synthetic routing/report matrix, contradictory bundles, calibration boundaries, dummy readiness artifacts and final secondary-command rejection |
| `followup_probes.py` | Isolated unknown-target/category confirmation, named-panel completeness, actual readiness, and historical source-hash search |
| `artifact_probes.py` | Recompute all main probability metrics, compare full-router participant averages to selective source data, and quantify mixed-repeat SHAP lists |
| `smoke_probe.py` | Actual PIDD Logistic Regression smoke orchestration with audit/split/study output roots redirected to temporary storage |

The readiness-positive fixture is intentionally invalid: empty artifacts, contradictory smoke evidence and absent execution authorization. Its passing result demonstrates a validator weakness; it is not an approved final study. No real protocol file is changed. The smoke uses two trials, three inner folds, one outer fold/repeat and 50 bootstrap samples; it is execution evidence only.

Preliminary probes that did not establish a defect remain recorded. The first invalid hospital fixture had only one class; a missing-patient fixture was rejected; the first unknown-category case lacked required panel fields. The follow-up script isolates the unknown target and unknown category separately and confirms those failures. The artifact script was corrected to accept the holdout output schema without a `repeat` column. The report uses these completed follow-up results.

The consolidated [audit evidence](../audit_evidence.json) contains the observed results, original full-suite output, repository/source inventory hashes, syntax checks, conference checksum check and primary-estimate comparison. The audit's original temporary smoke outputs are separate from authoritative development evidence.
