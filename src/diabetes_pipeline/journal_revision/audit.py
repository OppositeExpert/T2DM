"""Read-only feasibility and preservation inventory before any new fitting."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .common import ROOT, REPORT, PRIVATE, sha, write_json, studies, panels, bundle_paths, git_commit, markdown_table


def run_audit():
    REPORT.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    baseline = PRIVATE / "protected_baseline.json"
    if baseline.exists():
        raise FileExistsError("Preservation baseline already exists; use verification, never overwrite it")
    protected = set()
    inventories = []
    for dataset, directory, metadata in studies():
        files = [p for p in directory.rglob("*") if p.is_file()]
        protected.update(files)
        split = Path(metadata["split_manifest"])
        protected.add(split)
        protected.add(split.with_suffix(".json"))
        raw = ROOT / f"data/raw/{dataset}.csv"
        protected.add(raw)
        required = [split, raw, directory / "runtime_policy_evaluation/policy_decisions.csv",
                    directory / "runtime_policy_evaluation/participant_policy_predictions.csv",
                    directory / "availability_routing/stress_predictions.csv",
                    directory / "availability_routing/system_predictions.csv",
                    directory / "best_parameters.csv"]
        absent = [str(p.relative_to(ROOT)) for p in required if not p.is_file()]
        if absent:
            raise FileNotFoundError(absent)
        if sha(raw) != metadata["raw_data_sha256"] or sha(split) != metadata["split_manifest_sha256"]:
            raise ValueError(f"Frozen input binding mismatch: {dataset}")
        manifest = pd.read_csv(split)
        repeat_count = 5 if dataset in {"pidd", "sylhet"} else 1
        count = len(bundle_paths(directory))
        if count != (25 if repeat_count == 5 else 1):
            raise ValueError("Incomplete router bundle population")
        inventories.append({"dataset": dataset, "study_id": directory.name,
                            "endpoint": metadata["endpoint"], "files": len(files),
                            "bytes": sum(p.stat().st_size for p in files),
                            "model_bundles": len(list((directory / "models").glob("*.joblib"))),
                            "router_bundles": count, "repeat_count": repeat_count,
                            "split_manifest": str(split.relative_to(ROOT)),
                            "split_sha256": sha(split), "raw_sha256": sha(raw),
                            "split_roles": manifest["role"].value_counts().to_dict()})
    for relative in ["results/final_publication", "evidence", "config"]:
        protected.update(p for p in (ROOT / relative).rglob("*") if p.is_file())
    # Capturing hashes is read-only; all subsequent generated files are elsewhere.
    hashes = {str(p.relative_to(ROOT)): sha(p) for p in sorted(protected)}
    write_json(baseline, {"git_commit": git_commit(), "files": hashes})
    write_json(REPORT / "artifact_inventory.json", {"git_commit": git_commit(), "studies": inventories,
               "protected_file_count": len(hashes), "protected_baseline": str(baseline.relative_to(ROOT))})
    rows = [
        ("A3 per-repeat sensitivity", "repeated_cv.py; 5-repeat base/stress/runtime predictions", "predictions.csv; stress/system_predictions.csv; policy_decisions.csv", "AVAILABLE all repeats", "No", "Seconds to minutes", "Validate identities, compute 5 separate metrics and participant-mean estimand", "Repeat SD is descriptive; no repeat-level independent tests"),
        ("A2 routing distribution", "policy_evaluator.py; inference.py", "policy decisions; participant policy predictions; raw X; frozen panels", "AVAILABLE full provenance", "No", "Minutes incl. raw-input validation", "Recompute eligibility; reconcile unique identities and fold selections", "Natural eligibility differs from forced masking"),
        ("C8 selective prediction", "selective_prediction.py", "participant runtime probabilities; saved acceptance decisions", "AVAILABLE", "No", "Seconds to minutes", "Reuse original group/tie rules; add excluded event counts and prevalences", "Group-level mean confidence; coverage can overshoot target"),
        ("A1 independent panel training", "panel_training_ablations.py development-only; current final path unsupported", "raw data; frozen splits; per-fold params; selected families; calibrators", "AVAILABLE; successor runner required", "Yes for reduced panels", "234 tasks x (5 OOF + 1 final) = 1404 new base fits; pilot required", "Matched frozen family/parameters; train on panel columns only; refit calibration", "Conditional on full-schema tuning; not independently optimized reduced models"),
        ("A1 fixed imputation + 2x2 ablations", "saved robust and dynamic runtime raw probabilities; base/scenario calibrators", "same-fold router bundle + policy_decisions.csv", "AVAILABLE; historical B/D match after validation", "No", "Mapping seconds; paired bootstrap minutes", "A/C original full-schema calibration; B/D scenario calibration; choices held fixed", "Calibration and family interaction; original robust is cohort/fold fixed, not global"),
        ("A4 computational cost", "fold_metrics/best_parameters timings; fitted bundles", "historical timing columns; controlled reruns; package/hardware info", "PARTIAL historical component timings", "Bounded reduced-panel fits also measured", "20 warmed repeats x single + batch; serial local CPU", "Separate historical tune/fit, new OOF/final/calibration, inference/routing/storage", "Historical calibration/OOF and process peak RAM not separately logged; no invented durations"),
        ("B7 PIDD estimands", "protocol_correction.py; fixed panel + runtime CIs", "saved predictions; interval tables; bootstrap seed metadata", "AVAILABLE", "No", "Minutes", "Recompute forced core and runtime separately with original seeds/units", "Do not swap close rounded estimates/intervals"),
        ("C9 Table S9 + general verification", "policy_evaluator.py; comparisons.py; bootstrap.py", "aligned runtime predictions; raw/adjusted tests; frozen intervals", "AVAILABLE", "No", "Minutes; 2000 paired resamples", "Independently reproduce metrics, intervals, Holm families, split/group constraints", "Conditional inference; internal validation, historical access disclosed"),
        ("Methods/configuration exports", "loaders/builders/registry/tuning/calibration/routing/reporting", "current code plus frozen source/provenance", "AVAILABLE; exact old training tree not established", "No", "Documentation", "Export exact panels, algorithm behavior, configurations and commands", "Current HEAD differs from historical training source; preserve both"),
    ]
    matrix = pd.DataFrame(rows, columns=["Mentor request", "Existing implementation", "Required input artifacts",
                            "Availability status", "New training required?", "Estimated computational cost",
                            "Proposed implementation", "Risks/blockers"])
    matrix.to_csv(REPORT / "PHASE_0_FEASIBILITY_MATRIX.csv", index=False)
    text = """# Phase 0 feasibility audit

Status: COMPLETE for feasibility inspection. No training was launched before this report.
The user authorizes a successor post-review analysis; the original locked protocol and receipts remain unchanged.

## Repository and evidence boundary

Starting HEAD: `%s`; starting branch `docs/team-collaboration`, clean working tree.
Working branch: `analysis/journal-model-revision`. Frozen protocol:
`results/final_publication/provenance/frozen_protocol.yaml`, ID `t2dm-final-internal-validation-v1`.
75 original Optuna trials per applicable family/fold, 2000 bootstrap resamples.
Current source differs from the historical training fingerprint `7d5347cf4c10e50dceb201ad36527f6d1c3e2770bba364c15c9093bf97cc6a94`.
Exact historical retraining-source completeness is not established; this is a successor experiment using recorded fitted artifacts, parameters and splits.

Cleanup merge `b3792b8` preserved original evidence and removed archived conference/superseded material from tracking.
Read README, CONTRIBUTING, project structure, result/reproduction/acquisition/archive guides,
cleanup/simplification reports, frozen protocol, study registry and implementation.
Local archives outside the checkout are indexed in `evidence/repository_simplification_manifest.json`;
no restoration is needed because required private final-study artifacts remain available locally.
No manuscript, archived file or original output is modified. New aggregate exports: `analysis/journal_revision/`.
Private predictions/models/checkpoints: ignored `outputs/journal_revision_v1/`.

## Implementation inspection

Data: `data/loaders.py`, `data/validators.py`, `contracts.py`, `config/datasets.yaml`.
Splits: `splitting/strategies.py` and original hashed CSV manifests. PIDD uses 5 x 5 outer folds;
Sylhet uses identical full-predictor profiles; Hospital130 groups patients across partitions and development folds.
Preprocessing: `preprocessing/builders.py` fits median numeric imputation with indicators, missing-token categorical
imputation/one-hot vocabularies, and LR scaling within training partitions only.
Five families/search spaces: `models/registry.py`; tuning and base cross-fitting: `training/tuning.py`.
Calibration: `calibration/calibrators.py` selects identity/sigmoid/isotonic by second-layer cross-fitted Brier then log loss,
isotonic eligible only with >=1000 training observations. Routing: `routing/evaluator.py`,
`holdout_evaluator.py`, `policy_evaluator.py`, `inference.py`; configured four tree families, not LR, compete in the original router.
Robust family minimizes mean scenario development Brier with log loss/AP tiebreaks;
full-panel champion minimizes full-scenario development scores. Both use scenario calibrators in historical runtime comparisons.
Selective prediction: `evaluation/selective_prediction.py`; bootstrap and Holm: `evaluation/bootstrap.py`, `comparisons.py`.
Existing panel/retraining ablations cannot be called on locked studies; a separate successor runner is necessary.
Orchestration: `runner.py`, `holdout_runner.py`, `scripts/run_final_internal_validation.py`.
Publication/reproduction guards and tests are retained; no guard will be disabled.

## Available artifact inventory

%s

All four raw hashes and split hashes match study metadata before fitting. Private study files contain
raw and calibrated base probabilities, repeated/participant predictions, stress and runtime predictions,
full routing provenance, per-model parameters, fitted preprocessing/models/full calibrators,
scenario calibrators, selection scores, trials, confidence intervals, paired comparisons, software records and timing columns.
PIDD/Sylhet contain 125 base bundles and 25 routers each; BRFSS/Hospital130 contain five base bundles and one router each.
Runtime provenance is per outer repeat/fold plus participant-aggregated records for the repeated cohorts.
Historical tune/final-fit timing columns exist; historical calibration and base OOF time are not separately timed.

## Feasibility matrix

%s

## Bounded successor design and costs

`experiment_plan.json` is the prespecified successor configuration. There are 22 panels (6/5/6/5)
and 286 panel/fold combinations. Full panels reuse existing identical-schema fits (52 tasks);
234 reduced-schema tasks require 1404 base-model fits, no new optimization trials.
Each comparison holds family and parameters fixed to the original development choice for that panel/fold.
Calibration candidates/budgets and original partition identities are preserved. This is scientifically valid
as a conditional training-schema ablation, not a claim about optimal independently tuned reduced models.
Original full-schema tuning is inherited equally; disclose its 75 trials and zero new tuning in both arms.
Original small-cohort seeds and partitioned development folds are retained for base cross-fitting.
No evaluation label is used by tuning, calibration or family/panel selection.

Before a full launch, time one complete small-cohort task and one large-cohort task; record a cost projection.
Pre-pilot planning range: tens of minutes to several CPU hours, dependent on forest/boosting parameters.
No full 75-trial reduced-schema search is launched: 234 x 75 x 5 inner fits would be 87750 tuning fits before
calibration/final fits, and is outside this bounded conditional design.
Existing outputs are preferred for all other phases. Original inference is one fitted model per router bundle;
the patient-report wrapper can average all available fold routers. Evaluation averages five OOF predictions per participant,
which differs from averaging all 25 routers on a new record; document this distinction explicitly.

## Risks and blockers

No essential input artifact is currently missing. Exact historical training-source reconstruction and off-site archival
are unresolved existing reproducibility limitations. Retuned reduced-panel optima are outside this fixed-parameter comparison.
All findings remain post-review internal validation; reused partitions are not untouched external tests.
Uncertainty is conditional on fitted predictions and does not include full tuning/retraining variability.
Any identity/hash/probability discrepancy will stop the affected analysis, without substituting another cohort or estimand.
""" % (git_commit(), markdown_table(pd.DataFrame(inventories)[["dataset", "study_id", "endpoint", "files", "model_bundles", "router_bundles"]]), markdown_table(matrix))
    (REPORT / "PHASE_0_FEASIBILITY_AUDIT.md").write_text(text)
    print(f"Phase 0 complete; {len(hashes)} protected file hashes captured", flush=True)


def verify_protected():
    baseline = json.loads((PRIVATE / "protected_baseline.json").read_text())
    failures = [p for p, digest in baseline["files"].items()
                if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
    result = {"protected_files": len(baseline["files"]), "failures": failures,
              "passed": not failures, "starting_git_commit": baseline["git_commit"]}
    write_json(REPORT / "preservation_verification.json", result)
    if failures:
        raise ValueError(f"Protected evidence changed: {failures}")
    return result
