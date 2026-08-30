#!/usr/bin/env python3
"""Build registry-driven, estimand-correct development conference tables."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
STUDIES = ROOT / "outputs" / "publication_pipeline" / "studies"
GENERATED = ROOT / "conference_package" / "generated"
AUTHORITATIVE = ROOT / "config" / "authoritative_studies.yaml"
DATASETS = ROOT / "config" / "datasets.yaml"
PRIMARY_METRICS = (
    "auroc",
    "average_precision",
    "brier_score",
    "log_loss",
    "calibration_intercept",
    "calibration_slope",
    "expected_calibration_error",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _nested_participant_rows(
    study: Path, dataset: str, study_id: str, evidence_tier: str
) -> pd.DataFrame:
    predictions = pd.read_csv(study / "participant_predictions.csv")
    intervals = pd.read_csv(study / "participant_confidence_intervals.csv")
    intervals = intervals[
        intervals["probability_version"].eq("calibrated")
        & intervals["threshold_policy"].eq("fixed_0_5")
        & intervals["metric"].isin(PRIMARY_METRICS)
    ]
    records: list[dict[str, object]] = []
    for model, frame in predictions.groupby("model", sort=True):
        model_intervals = intervals[intervals["model"].eq(model)].set_index("metric")
        record: dict[str, object] = {
            "study_id": study_id,
            "dataset": dataset,
            "evidence_tier": evidence_tier,
            "estimand": "participant_mean_across_repeats",
            "model": model,
            "n": int(len(frame)),
            "positives": int(frame["target"].sum()),
            "prevalence": float(frame["target"].mean()),
        }
        for metric in PRIMARY_METRICS:
            row = model_intervals.loc[metric]
            record[metric] = float(row["estimate"])
            record[f"{metric}_ci_lower"] = float(row["ci_lower"])
            record[f"{metric}_ci_upper"] = float(row["ci_upper"])
        records.append(record)
    return pd.DataFrame(records)


def _holdout_rows(
    study: Path, dataset: str, study_id: str, evidence_tier: str
) -> pd.DataFrame:
    summary = pd.read_csv(study / "summary_metrics.csv")
    intervals = pd.read_csv(study / "confidence_intervals.csv")
    primary = summary[
        summary["probability_version"].eq("calibrated")
        & summary["threshold_policy"].eq("fixed_0_5")
    ].copy()
    primary.insert(0, "study_id", study_id)
    primary["dataset"] = dataset
    primary["evidence_tier"] = evidence_tier
    primary["estimand"] = "development_test_holdout"
    interval_rows = intervals[
        intervals["probability_version"].eq("calibrated")
        & intervals["threshold_policy"].eq("fixed_0_5")
        & intervals["metric"].isin(PRIMARY_METRICS)
    ]
    for metric in PRIMARY_METRICS:
        metric_rows = interval_rows[interval_rows["metric"].eq(metric)].set_index("model")
        primary[f"{metric}_ci_lower"] = primary["model"].map(metric_rows["ci_lower"])
        primary[f"{metric}_ci_upper"] = primary["model"].map(metric_rows["ci_upper"])
    columns = [
        "study_id", "dataset", "evidence_tier", "estimand", "model",
        "n", "positives", "prevalence",
    ]
    for metric in PRIMARY_METRICS:
        columns.extend([metric, f"{metric}_ci_lower", f"{metric}_ci_upper"])
    return primary[columns]


def main() -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    declarations = yaml.safe_load(AUTHORITATIVE.read_text(encoding="utf-8"))["studies"]
    dataset_contracts = yaml.safe_load(DATASETS.read_text(encoding="utf-8"))["datasets"]
    frames: list[pd.DataFrame] = []
    provenance: dict[str, object] = {
        "schema_version": "2.0",
        "evidence_role": "development_only_not_final",
        "primary_estimands": {
            "pidd": "participant_mean_across_repeats",
            "sylhet": "participant_mean_across_repeats_with_profile_cluster_inference",
            "brfss": "development_test_holdout",
            "hospital130": "development_test_holdout_with_patient_cluster_inference",
        },
        "studies": {},
    }
    for dataset, declaration in declarations.items():
        study_id = str(declaration["study_id"])
        evidence_tier = str(declaration["evidence_tier"])
        study = STUDIES / study_id
        metadata_path = study / "experiment_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("runner") == "development_locked_holdout":
            frame = _holdout_rows(study, dataset, study_id, evidence_tier)
            metrics_path = study / "summary_metrics.csv"
        else:
            frame = _nested_participant_rows(study, dataset, study_id, evidence_tier)
            metrics_path = study / "participant_confidence_intervals.csv"
        frame.insert(3, "endpoint", dataset_contracts[dataset]["endpoint"])
        frames.append(frame)
        provenance["studies"][dataset] = {
            "study_id": study_id,
            "endpoint": dataset_contracts[dataset]["endpoint"],
            "profile": metadata["profile"]["name"],
            "profile_locked": bool(metadata["profile"].get("locked", False)),
            "metadata_sha256": _sha256(metadata_path),
            "primary_metrics_artifact": metrics_path.relative_to(ROOT).as_posix(),
            "primary_metrics_sha256": _sha256(metrics_path),
            "dataset_configuration_sha256": metadata.get("dataset_configuration_sha256"),
            "raw_data_sha256": metadata.get("raw_data_sha256"),
            "split_manifest_sha256": metadata.get("split_manifest_sha256"),
            "source_tree_sha256": metadata.get("source_tree_sha256"),
            "eligible_for_final_claims": False,
        }
    pd.concat(frames, ignore_index=True).to_csv(
        GENERATED / "development_model_performance.csv", index=False
    )
    (GENERATED / "development_evidence_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
