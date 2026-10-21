#!/usr/bin/env python3
"""Verify complete public file coverage, original test/source seals and exclusions."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "publication_release/PUBLIC_EVIDENCE_MANIFEST.csv"
SELF_SEALS = {"publication_release/PUBLIC_EVIDENCE_MANIFEST.csv",
              "publication_release/PUBLIC_EVIDENCE_MANIFEST.sha256"}
LOCAL_DIRS = {".git", ".pytest_cache", "__pycache__", "outputs", ".venv", ".venv-review"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory():
    result = set()
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if set(rel.parts) & LOCAL_DIRS or str(rel).startswith("data/raw/") or any(p.endswith(".egg-info") for p in rel.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"Symlink not allowed in snapshot: {rel}")
        if path.is_file() and str(rel) not in SELF_SEALS:
            result.add(str(rel))
    return result


def verify():
    origin = json.loads((ROOT / "publication_release/SNAPSHOT_PROVENANCE.json").read_text())
    with MANIFEST.open(newline="") as f:
        records = list(csv.DictReader(f))
    paths = [r["release_path"] for r in records]
    if not paths or len(paths) != len(set(paths)) or set(paths) != inventory():
        raise ValueError("Manifest does not exactly cover the public snapshot")
    for r in records:
        path = (ROOT / r["release_path"]).resolve()
        if not path.is_relative_to(ROOT) or sha(path) != r["sha256"]:
            raise ValueError(f"Snapshot hash mismatch: {r['release_path']}")
        if r["public_private_classification"] != "PUBLIC_SNAPSHOT_CANDIDATE":
            raise ValueError("Non-public or unreviewed artifact in public manifest")
    if sha(MANIFEST) != (MANIFEST.with_suffix(".sha256")).read_text().split()[0]:
        raise ValueError("Manifest sidecar does not match")
    for path in origin["omitted_hold_paths"]:
        if (ROOT / path).exists():
            raise ValueError(f"Excluded original artifact present: {path}")
    for section in ["inherited_test_sha256", "unchanged_scientific_source_sha256"]:
        for rel, expected in origin[section].items():
            if sha(ROOT / rel) != expected:
                raise ValueError(f"Original implementation/test changed: {rel}")
    summary = json.loads((ROOT / "publication_release/PUBLIC_STUDY_SUMMARY.json").read_text())
    if summary["independent_holdout_claim_allowed"] or summary["cross_cohort_probability_pooling"] or summary["dynamic_model_switching"]["multiplicity_corrected_superiority_established"]:
        raise ValueError("Original scientific claim boundary changed")
    if not summary["datasets_are_endpoint_separated"] or len(summary["studies"]) != 4:
        raise ValueError("Endpoint-separated study summary incomplete")
    derivative = origin["aggregate_derivative"]
    if sha(ROOT / derivative["public"]) != derivative["public_sha256"]:
        raise ValueError("Public statistical derivative changed")
    with (ROOT / derivative["public"]).open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != derivative["retained_columns"] or len(list(reader)) != 220:
            raise ValueError("Public statistical derivative schema or count changed")
    return {"passed": True, "public_files_hashed": len(records),
            "inherited_test_files_unchanged": len(origin["inherited_test_sha256"]),
            "scientific_source_files_unchanged": len(origin["unchanged_scientific_source_sha256"]),
            "excluded_originals_present": 0, "historical_reanalysis_claimed": False}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
