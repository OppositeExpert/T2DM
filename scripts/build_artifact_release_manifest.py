#!/usr/bin/env python3
"""Create a tracked release manifest for externally archived study artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "evidence" / "study_registry.json"
OUTPUT = ROOT / "evidence" / "artifact_release_manifest.json"
CORE_REQUIRED = {
    "experiment_metadata.json",
    "summary_metrics.csv",
    "confidence_intervals.csv",
    "calibration_selection.csv",
    "selected_thresholds.csv",
    "decision_curves.csv",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    records: list[dict[str, object]] = []
    for dataset, study in sorted(registry["studies"].items()):
        command = str(study["command"])
        study_root = ROOT / study["study_directory"]
        for path in sorted(study_root.rglob("*")):
            if not path.is_file() or "checkpoints" in path.relative_to(study_root).parts:
                continue
            relative_study_path = path.relative_to(study_root).as_posix()
            is_model_bundle = (
                relative_study_path.startswith("models/") and path.suffix == ".joblib"
            )
            records.append(
                {
                    "logical_name": relative_study_path,
                    "study_id": study["study_id"],
                    "dataset": dataset,
                    "evidence_tier": study["evidence_tier"],
                    "relative_local_path": path.relative_to(ROOT).as_posix(),
                    "file_size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "artifact_type": (
                        "joblib_model_bundle"
                        if is_model_bundle
                        else path.suffix.lstrip(".") or "binary"
                    ),
                    "requirement": (
                        "required"
                        if path.name in CORE_REQUIRED or is_model_bundle
                        else "optional"
                    ),
                    "regeneration_command": command,
                    "external_uri": None,
                    "archive_identifier": None,
                    "archive_status": "pending_external_archive",
                }
            )
    payload = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive_state": "not_uploaded",
        "archive_uri": None,
        "source_registry": REGISTRY.relative_to(ROOT).as_posix(),
        "source_registry_sha256": sha256(REGISTRY),
        "artifact_count": len(records),
        "artifacts": records,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
