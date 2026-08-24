"""Build traceable development-evidence tables for the conference package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STUDIES = ROOT / "outputs" / "publication_pipeline" / "studies"
GENERATED = ROOT / "conference_package" / "generated"
STUDY_IDS = {
    "pidd": "pidd_development_072cd2104089",
    "sylhet": "sylhet_development_b52477910fe6",
    "brfss": "brfss_smoke_holdout_b3a6ad2aa89e",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    provenance: dict[str, object] = {
        "schema_version": "1.0",
        "evidence_role": "development_and_smoke_not_final",
        "studies": {},
    }
    for dataset, study_id in STUDY_IDS.items():
        study = STUDIES / study_id
        metadata_path = study / "experiment_metadata.json"
        summary_path = study / "summary_metrics.csv"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        summary = pd.read_csv(summary_path)
        primary = summary[
            (summary["probability_version"] == "calibrated")
            & (summary["threshold_policy"] == "fixed_0_5")
        ].copy()
        primary.insert(0, "study_id", study_id)
        if "dataset" not in primary:
            primary.insert(1, "dataset", dataset)
        primary.insert(
            2,
            "evidence_tier",
            "execution_only_smoke" if dataset == "brfss" else "development_only",
        )
        columns = [
            "study_id",
            "dataset",
            "evidence_tier",
            "model",
            "n",
            "positives",
            "prevalence",
            "auroc",
            "average_precision",
            "brier_score",
            "log_loss",
            "calibration_intercept",
            "calibration_slope",
            "expected_calibration_error",
        ]
        frames.append(primary[columns])
        provenance["studies"][dataset] = {
            "study_id": study_id,
            "profile": metadata["profile"]["name"],
            "profile_locked": bool(metadata["profile"].get("locked", False)),
            "metadata_sha256": _sha256(metadata_path),
            "summary_metrics_sha256": _sha256(summary_path),
            "dataset_configuration_sha256": metadata.get(
                "dataset_configuration_sha256"
            ),
            "raw_data_sha256": metadata.get("raw_data_sha256"),
            "split_manifest_sha256": metadata.get("split_manifest_sha256"),
            "source_tree_sha256": metadata.get("source_tree_sha256"),
            "eligible_for_final_claims": False,
        }
    performance = pd.concat(frames, ignore_index=True)
    performance.to_csv(GENERATED / "development_model_performance.csv", index=False)
    (GENERATED / "development_evidence_provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
