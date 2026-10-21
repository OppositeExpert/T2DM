#!/usr/bin/env python3
"""Recount eligible cohort sizes/events from separately acquired, hash-verified data.

No records, identifiers, predictions or fitted objects are written.
Evaluation split counts cannot be recovered by this eligibility-only check.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import yaml

from diabetes_pipeline.data.loaders import load_dataset

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["all", "pidd", "sylhet", "brfss", "hospital130"], default="all")
    args = parser.parse_args()
    sources = yaml.safe_load((ROOT / "config/data_sources.yaml").read_text())["datasets"]
    with (ROOT / "results/final_publication/tables/dataset_characteristics.csv").open(newline="") as f:
        expected = {r["dataset"]: r for r in csv.DictReader(f)}
    results = []
    for name in sources if args.dataset == "all" else [args.dataset]:
        source = sources[name]
        path = ROOT / source["expected_path"]
        if not path.is_file():
            results.append({"dataset": name, "status": "BLOCKED", "reason": "separately acquired raw input missing"})
            continue
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
                h.update(block)
        if h.hexdigest() != source["expected_sha256"]:
            raise ValueError(f"Raw source hash mismatch: {name}")
        data = load_dataset(name)
        observed = {"n": len(data.y), "positive_events": int(data.y.sum()), "predictor_count": data.X.shape[1]}
        if any(value != int(expected[name][key]) for key, value in observed.items()):
            raise ValueError(f"Eligible cohort aggregate mismatch: {name}")
        results.append({"dataset": name, "status": "PASS", "raw_rows": data.metadata["raw_rows"], **observed})
    print(json.dumps({"results": results, "evaluation_split_recounted": False, "models_fitted": False}, indent=2))
    if any(r["status"] != "PASS" for r in results):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
