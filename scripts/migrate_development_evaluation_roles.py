#!/usr/bin/env python3
"""Migrate ambiguous evaluation-role labels in current authoritative development holdouts."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "authoritative_studies.yaml"
STUDIES = ROOT / "outputs" / "publication_pipeline" / "studies"


def _replace_json(value):
    if isinstance(value, dict):
        return {key: _replace_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_json(item) for item in value]
    return "development_test" if value == "locked_test" else value


def migrate(study: Path) -> tuple[int, int]:
    metadata_path = study / "experiment_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("evidence_tier") != "full_development":
        raise ValueError(f"Refusing to migrate non-development study: {study.name}")
    if metadata.get("profile", {}).get("name") != "development":
        raise ValueError(f"Refusing to migrate non-development profile: {study.name}")
    csv_changes = 0
    json_changes = 0
    for path in sorted(study.rglob("*.csv")):
        frame = pd.read_csv(path, low_memory=False)
        if "evaluation_role" not in frame or not frame["evaluation_role"].eq("locked_test").any():
            continue
        frame["evaluation_role"] = frame["evaluation_role"].replace(
            {"locked_test": "development_test"}
        )
        frame.to_csv(path, index=False)
        csv_changes += 1
    for path in sorted(study.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        migrated = _replace_json(payload)
        if migrated == payload:
            continue
        path.write_text(json.dumps(migrated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        json_changes += 1
    return csv_changes, json_changes


def main() -> None:
    declarations = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["studies"]
    result = {}
    for dataset, declaration in declarations.items():
        study = STUDIES / declaration["study_id"]
        metadata = json.loads((study / "experiment_metadata.json").read_text(encoding="utf-8"))
        if metadata.get("runner") != "development_locked_holdout":
            continue
        csv_changes, json_changes = migrate(study)
        result[dataset] = {"csv_files": csv_changes, "json_files": json_changes}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
