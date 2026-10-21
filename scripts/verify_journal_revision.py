#!/usr/bin/env python3
"""Read-only cross-check of completed successor predictions and aggregate exports."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from diabetes_pipeline.journal_revision.audit import verify_protected
from diabetes_pipeline.journal_revision.common import ROOT, REPORT, PRIVATE, EXPECTED, METRICS, aggregate, read_csv, metrics, panels, sha, write_json


def main():
    preservation = verify_protected()
    count = 0
    tasks = sorted((PRIVATE / "panel_tasks").glob("*/*/*/task.json"))
    if len(tasks) != 286:
        raise ValueError("Incomplete successor task inventory")
    for path in tasks:
        task = json.loads(path.read_text())
        if not task["training_evaluation_disjoint"] or not task["group_separation_verified"] or task["calibration_evaluation_labels_accessed"]:
            raise ValueError("Invalid training/calibration boundary record")
        for relative, digest in task["output_hashes"].items():
            if sha(path.parent / relative) != digest:
                raise ValueError("New task output changed since checkpoint")
        if task["panel"] != "full":
            model = joblib.load(path.parent / "bundle.joblib")
            if set(model["preprocessor"].feature_names_in_) != set(task["features"]):
                raise ValueError("Reduced-schema preprocessor contains unauthorized predictors")
            if model["signature"] != task["signature"] or len(task["inner_fit_records"]) != 5:
                raise ValueError("Model/checkpoint or five-fold budget mismatch")
        count += 1
    table = pd.read_csv(REPORT / "04_RETRAINED_PANEL_COMPARISON.csv")
    checked = 0
    for dataset in EXPECTED:
        files = sorted((PRIVATE / "panel_tasks" / dataset).glob("*/*/predictions.csv.gz"))
        frame = pd.concat([read_csv(f) for f in files], ignore_index=True)
        source = aggregate(frame, ["scenario"], 5 if dataset in {"pidd", "sylhet"} else 1)
        for panel, sample in source.groupby("scenario", sort=True):
            if len(sample) != EXPECTED[dataset][0] or int(sample.target.sum()) != EXPECTED[dataset][1]:
                raise ValueError("New aggregate population/event mismatch")
            expected = table[(table.dataset == dataset) & (table.panel == panel) & (table.comparison_arm == "retrained")].iloc[0]
            actual = metrics(sample)
            for metric, value in actual.items():
                if not np.isclose(value, expected[metric], atol=1e-10, rtol=0, equal_nan=True):
                    raise ValueError("Aggregate new-panel metric differs from private prediction source")
                checked += 1
    selective = pd.read_csv(REPORT / "03_SELECTIVE_PREDICTION.csv")
    for _, row in selective.iterrows():
        if row.accepted_n + row.rejected_n != row.total_n or row.accepted_positive_events + row.rejected_positive_events != row.total_positive_events:
            raise ValueError("Selective population/event reconciliation failed")
        if row.availability_abstained_n + row.confidence_rejected_n != row.rejected_n:
            raise ValueError("Abstention types fail to reconcile")
        if row.availability_abstained_events + row.confidence_rejected_events != row.rejected_positive_events:
            raise ValueError("Excluded event types fail to reconcile")
    # All exported coverage/count/metric cells match the original selective table.
    original = pd.read_csv(ROOT / "results/final_publication/tables/selective_prediction_metrics.csv")
    mapping = {"actual_observation_coverage": "actual_coverage", "positive_event_coverage": "positive_event_coverage",
               "accepted_n": "accepted_n", "rejected_n": "abstained_n", "accepted_positive_events": "positive_events",
               "accepted_prevalence": "accepted_prevalence", "rejected_prevalence": "rejected_prevalence",
               **{m:m for m in METRICS}}
    selective_cells = 0
    for _, row in selective.iterrows():
        source = original[(original.dataset == row.dataset) & (original.system == row.system) &
                          (original.target_coverage == row.nominal_coverage)].iloc[0]
        for key, other in mapping.items():
            if not np.isclose(row[key], source[other], atol=1e-10, rtol=0, equal_nan=True):
                raise ValueError("Selective aggregate differs from frozen source")
            selective_cells += 1
    source_map = pd.read_csv(REPORT / "ANALYSIS_SOURCE_MAP.csv")
    for output, group in source_map.groupby("output_file"):
        if sha(ROOT / output) != group.output_sha256.iloc[0] or len(group) != len(pd.read_csv(ROOT / output)):
            raise ValueError("Source-map row count/fingerprint mismatch")
    fingerprints = json.loads((REPORT / "analysis_source_fingerprints.json").read_text())
    for path, digest in fingerprints["files"].items():
        if sha(ROOT / path) != digest:
            raise ValueError("Successor source changed after source-map generation")
    for path in REPORT.glob("*.csv"):
        columns = pd.read_csv(path, nrows=0).columns
        if {"row_id", "group_id"} & set(columns):
            raise ValueError("Participant/group IDs exported in aggregate handoff")
    manifest_path = REPORT / "FINAL_HANDOFF_CHECKSUMS.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for relative, digest in manifest["files"].items():
            if sha(ROOT / relative) != digest:
                raise ValueError(f"Final handoff checksum mismatch: {relative}")
    result = {"passed": True, "protected_files_verified": preservation["protected_files"],
              "new_tasks_verified": count, "new_panel_metric_cells": checked,
              "selective_cells_against_original": selective_cells, "source_map_rows": len(source_map),
              "private_ids_present_in_aggregate_csv_columns": False}
    write_json(REPORT / "FINAL_VERIFICATION.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
