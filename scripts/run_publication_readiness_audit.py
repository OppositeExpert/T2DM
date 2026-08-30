#!/usr/bin/env python3
"""Regenerate the single canonical publication-readiness audit from the registry."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from diabetes_pipeline.reporting.publication_readiness import (
    audit_publication_readiness,
    render_publication_readiness_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "authoritative_studies.yaml"
PROTOCOL = ROOT / "config" / "publication_protocol.yaml"
QA = ROOT / "conference_package" / "qa"


def main() -> None:
    declarations = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))["studies"]
    primary = yaml.safe_load(PROTOCOL.read_text(encoding="utf-8"))["primary_datasets"]
    study_dirs = [
        ROOT / "outputs" / "publication_pipeline" / "studies" / declarations[name]["study_id"]
        for name in primary
    ]
    result = audit_publication_readiness(study_dirs, protocol_path=PROTOCOL)
    QA.mkdir(parents=True, exist_ok=True)
    (QA / "publication_readiness.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (QA / "Publication_Readiness_Audit.md").write_text(
        render_publication_readiness_markdown(result).rstrip() + "\n", encoding="utf-8"
    )
    print(json.dumps({"blockers": result["blocker_count"], "warnings": result["warning_count"]}))


if __name__ == "__main__":
    main()
