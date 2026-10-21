#!/usr/bin/env python3
"""Check saved aggregate evidence without datasets, fitted models, or third-party packages.

This verifies exported arithmetic and provenance, not prediction-derived inference.
It never fits models, reruns bootstrap sampling, or writes scientific artifacts.
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "analysis/journal_revision"
HANDOFF = REPORT / "manuscript_handoff"
METRICS = ("auroc", "average_precision", "brier_score", "log_loss")


def safe_path(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f"Missing or unsafe repository file: {relative}")
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def close(a, b):
    a, b = float(a), float(b)
    if not ((math.isnan(a) and math.isnan(b)) or math.isclose(a, b, rel_tol=0, abs_tol=1e-10)):
        raise ValueError("Saved aggregate arithmetic differs beyond absolute tolerance 1e-10")


def verify_tables():
    index = json.loads((HANDOFF / "TABLE_SOURCE_INDEX.json").read_text())
    checked = 0
    for entry in index:
        source = safe_path(entry["source"])
        if digest(source) != entry["source_sha256"]:
            raise ValueError(f"Source checksum mismatch: {entry['source']}")
        source_rows = rows(source)
        target = safe_path(str((HANDOFF / entry["table"]).relative_to(ROOT)))
        wanted = [{c: source_rows[i][c] for c in entry["columns"]}
                  for i in entry["source_data_row_indexes_zero_based"]]
        if rows(target) != wanted or len(wanted) != entry["rows"]:
            raise ValueError(f"Exact source-string projection mismatch: {entry['table']}")
        if entry["method"] == "byte-identical aggregate source copy" and target.read_bytes() != source.read_bytes():
            raise ValueError(f"Supplementary source copy mismatch: {entry['table']}")
        checked += 1
    return checked


def verify_contrasts():
    checked = 0
    for name, points_name, index_keys in [
        ("04_PANEL_PAIRED_CONTRASTS.csv", "analysis/journal_revision/04_RETRAINED_PANEL_COMPARISON.csv", ("dataset", "panel", "comparison_arm")),
        ("05_ABLATION_PAIRED_CONTRASTS.csv", "analysis/journal_revision/05_CALIBRATION_SWITCHING_ABLATION.csv", ("dataset", "system")),
        ("07_RUNTIME_PAIRED_COMPARISONS.csv", "results/final_publication/tables/routing_fallback_performance.csv", ("dataset", "system")),
    ]:
        points = {tuple(r[k] for k in index_keys): r for r in rows(safe_path(points_name))}
        families = collections.defaultdict(list)
        for r in rows(REPORT / name):
            families[(r["dataset"], r["metric"])].append(r)
        for family in families.values():
            ordered = sorted(family, key=lambda r: float(r["paired_bootstrap_p_value"]))
            running = 0.0
            for rank, r in enumerate(ordered):
                running = max(running, min(1., float(r["paired_bootstrap_p_value"]) * (len(ordered) - rank)))
                close(running, r["holm_adjusted_p_value"])
                prefix = (r["dataset"], r["panel"]) if "panel" in r else (r["dataset"],)
                effect = float(points[prefix + (r["model_a"],)][r["metric"]]) - float(points[prefix + (r["model_b"],)][r["metric"]])
                close(effect, r["observed_difference_a_minus_b"])
                close(effect * (1 if r["metric"] in {"auroc", "average_precision"} else -1), r["observed_improvement_a_over_b"])
                checked += 1
    return checked


def verify_repeats():
    groups = collections.defaultdict(list)
    for r in rows(REPORT / "01_PER_REPEAT_SENSITIVITY.csv"):
        groups[tuple(r[k] for k in ("dataset", "analysis", "model", "scenario", "system", "probability_version"))].append(r)
    cells = 0
    for group in groups.values():
        repeated = [r for r in group if r["summary"] == "per_repeat"]
        if len(repeated) != 5 or len({r["repeat"] for r in repeated}) != 5:
            raise ValueError("Expected five distinct dependent repeat summaries")
        summary = {r["summary"]: r for r in group if r["summary"] != "per_repeat"}
        for metric in METRICS:
            values = [float(r[metric]) for r in repeated]
            close(statistics.mean(values), summary["repeat_metric_mean"][metric])
            close(statistics.stdev(values), summary["repeat_metric_sample_sd"][metric])
            close(float(summary["repeat_metric_mean"][metric]) - float(summary["participant_mean_probability_metric"][metric]), summary["repeat_metric_mean_minus_primary"][metric])
            cells += 2
    return cells


def verify_counts():
    routing = rows(REPORT / "02_ROUTING_DISTRIBUTION.csv")
    populations = {r["dataset"]: r for r in routing if r["row_type"] == "population_total"}
    for dataset, population in populations.items():
        panels = [r for r in routing if r["dataset"] == dataset and r["row_type"] == "unique_panel"]
        close(sum(float(r["evaluation_records"]) for r in panels), population["evaluation_records"])
        close(sum(float(r["positive_events"]) for r in panels), population["positive_events"])
        close(float(population["accepted_records"]) + float(population["abstained_records"]), population["evaluation_records"])
    selective = rows(REPORT / "03_SELECTIVE_PREDICTION.csv")
    for r in selective:
        for a, b, total in [
            ("accepted_n", "rejected_n", "total_n"),
            ("accepted_positive_events", "rejected_positive_events", "total_positive_events"),
            ("availability_abstained_n", "confidence_rejected_n", "rejected_n"),
            ("availability_abstained_events", "confidence_rejected_events", "rejected_positive_events"),
        ]:
            close(float(r[a]) + float(r[b]), r[total])
        close(r["total_n"], populations[r["dataset"]]["evaluation_records"])
        close(r["total_positive_events"], populations[r["dataset"]]["positive_events"])
    return {"routing_cohorts": len(populations), "selective_rows": len(selective)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, help="Also check every candidate-file SHA-256 in the local release inventory")
    args = parser.parse_args()
    result = {"passed": True, "curated_tables": verify_tables(),
              "saved_p_value_holm_and_point_contrasts": verify_contrasts(),
              "repeat_mean_sd_cells": verify_repeats(), **verify_counts(),
              "prediction_metrics_or_bootstrap_intervals_recomputed": False,
              "models_fitted": False}
    if args.manifest:
        count = 0
        for r in rows(args.manifest):
            if r["sha256"] and digest(safe_path(r["release_path"])) != r["sha256"]:
                raise ValueError(f"Candidate inventory mismatch: {r['release_path']}")
            count += bool(r["sha256"])
        result["candidate_file_hashes"] = count
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
