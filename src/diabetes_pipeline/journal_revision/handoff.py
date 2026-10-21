"""Curate and verify existing aggregate evidence; never fit, predict, or time models."""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

import numpy as np
import pandas as pd

from .common import ROOT, REPORT, PRIVATE, EXPECTED, METRICS, sha

HANDOFF = REPORT / "manuscript_handoff"
SEAL = REPORT / "MANUSCRIPT_HANDOFF_CHECKSUMS.json"
ARCHIVE = ROOT / "analysis/JOURNAL_REVISION_HANDOFF_FINAL.zip"
ARCHIVE_MANIFEST = ROOT / "analysis/JOURNAL_REVISION_HANDOFF_FINAL_MANIFEST.md"
INDEX = "TABLE_SOURCE_INDEX.json"
SOURCES = "analysis/journal_revision/"
FROZEN = "results/final_publication/tables/"
PRIVATE_COLUMNS = {"row_id", "group_id", "patient_nbr", "encounter_id", "row_position",
                   "target", "probability_calibrated", "probability_raw"}


def read_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if not reader.fieldnames or PRIVATE_COLUMNS.intersection(reader.fieldnames):
            raise ValueError(f"Not an approved aggregate table: {path}")
        return reader.fieldnames, rows


def csv_bytes(columns, rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows({c: row[c] for c in columns} for row in rows)
    return out.getvalue().encode()


def display(value):
    try:
        number = float(value)
    except (ValueError, TypeError):
        return str(value).replace("|", " / ").replace("\n", " ")
    if not math.isfinite(number):
        return "—"
    return format(number, ".6g")


def table_markdown(title, columns, rows, note):
    lines = [f"# {title}", "", note, "", "Display values use six significant figures; the adjacent CSV retains the exact source strings.", "",
             "| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines.extend("| " + " | ".join(display(r[c]) for c in columns) + " |" for r in rows)
    return ("\n".join(lines) + "\n").encode()


def specifications():
    """Explicit projections; no inference or silent source rounding."""
    metric_columns = ["auroc", "average_precision", "brier_score", "log_loss"]
    effect_columns = ["dataset", "metric", "observed_difference_a_minus_b", "ci_lower_a_minus_b",
                      "ci_upper_a_minus_b", "holm_adjusted_p_value"]
    definitions = [
        ("01_reduced_schema", "Reduced-schema versus masked-input models", "04_RETRAINED_PANEL_COMPARISON.csv",
         lambda r: r["panel"] != "full", ["dataset", "panel", "comparison_arm", "evaluation_n"] + metric_columns,
         "Matched family and frozen full-schema hyperparameters; preprocessing/model/calibration refitted only in original training partitions. Full controls and all paired effects remain in the supplement."),
        ("01_reduced_schema_effects", "Paired reduced-schema effects", "04_PANEL_PAIRED_CONTRASTS.csv",
         lambda r: r["panel"] != "full", ["dataset", "panel"] + effect_columns[1:],
         "Literal retrained minus masked effect; positive AUROC/AP and negative Brier/log loss favor retraining. 95% paired percentile intervals; Holm family includes every prespecified panel within cohort/metric, including the reused full control."),
        ("02_fixed_imputation", "Fixed imputation versus complete framework", "05_CALIBRATION_SWITCHING_ABLATION.csv",
         lambda r: r["system"] in {"A", "D"}, ["dataset", "system", "evaluation_n", "coverage"] + metric_columns,
         "A: fixed robust family with original full-schema mapping. D: development-selected panel family and panel mapping. Identical eligible records and training-fitted imputation."),
        ("02_fixed_imputation_effects", "Complete framework minus fixed imputation", "05_ABLATION_PAIRED_CONTRASTS.csv",
         lambda r: r["model_a"] == "D" and r["model_b"] == "A", effect_columns,
         "D minus A; intervals/p-values come from the five-contrast ablation family, not the original three-policy family."),
        ("03_calibration_switching", "Frozen-family 2 × 2 ablation", "05_CALIBRATION_SWITCHING_ABLATION.csv",
         lambda r: True, ["dataset", "system", "evaluation_n"] + metric_columns,
         "A/B: robust fixed family; C/D: panel-selected family. A/C: full-schema mapping; B/D: panel mapping. B equals historical robust policy and D equals historical router. Five declared paired contrasts per cohort/metric are in the supplement."),
        ("04_routing", "Runtime routing and events", "02_ROUTING_DISTRIBUTION.csv",
         lambda r: r["row_type"] == "unique_panel", ["dataset", "panel", "evaluation_records", "positive_events", "population_pct", "event_pct"],
         "Unique evaluation records. UNSUPPORTED means availability abstention. Family/mapping counts per repeat are separate supplementary rows and cannot be summed as unique participants."),
        ("05_per_repeat", "Five-repeat sensitivity versus primary estimate", "01_PER_REPEAT_SENSITIVITY.csv",
         lambda r: r["analysis"] == "runtime_policy" and r["system"] == "availability_router" and r["probability_version"] == "probability_calibrated" and r["summary"] in {"repeat_metric_mean", "repeat_metric_sample_sd", "participant_mean_probability_metric"},
         ["dataset", "summary", "evaluation_n", "positive_events"] + metric_columns,
         "Pair repeat_metric_mean with repeat_metric_sample_sd as mean ± descriptive sample SD (five dependent repeats). Primary metrics first average five OOF probabilities per participant. SD is not a confidence interval."),
        ("06_selective_prediction", "Selective prediction at approximately 70% observation coverage", "03_SELECTIVE_PREDICTION.csv",
         lambda r: r["system"] == "availability_router" and float(r["nominal_coverage"]) == .7,
         ["dataset", "actual_observation_coverage", "positive_event_coverage", "accepted_n", "rejected_n", "accepted_positive_events", "rejected_positive_events", "accepted_prevalence", "rejected_prevalence"] + metric_columns,
         "Coverage is a fraction of the complete evaluation population/events. Metrics condition on accepted cases. Availability abstention differs from confidence rejection. All targets and uncertainty are supplied in the supplement."),
        ("07_computational_cost", "Computational cost", "A4_MAIN_TEXT_TABLE.csv", lambda r: True, None,
         "Final-fit/calibration SUMS in seconds over reduced-schema tasks; loaded original-artifact D inference in ms per call (batch is 256 records); exemplar storage in MiB=2^20 bytes. These columns describe different workloads, not one model's training-to-deployment lifecycle. Historical environment is unknown; see A4 publication summary."),
        ("08_main_statistical_comparisons", "Original runtime router minus robust fixed policy", "07_RUNTIME_PAIRED_COMPARISONS.csv",
         lambda r: r["model_a"] == "availability_router" and r["model_b"] == "robust_single_model", effect_columns,
         "Literal router minus robust difference; negative loss differences favor router. 95% paired percentile intervals; Holm adjusts three original policy contrasts within cohort/metric. Robust here is B, not fixed-imputation A."),
        ("09_pidd_estimands", "Distinct PIDD estimands", "07_PIDD_ESTIMANDS.csv", lambda r: r["metric"] == "auroc",
         ["estimand", "estimate", "ci_lower", "ci_upper", "evaluation_n", "positive_events", "bootstrap_seed", "n_bootstrap"],
         "Forced core-metabolic and natural runtime policy use different predictions and seeds. Both estimates round to .837; their intervals are not interchangeable."),
    ]
    for name, title, source, select, columns, note in definitions:
        yield f"03_MAIN_TEXT_TABLES/{name}", title, SOURCES + source, select, columns, note, True
    supplementary = ["01_PER_REPEAT_SENSITIVITY.csv", "02_ROUTING_DISTRIBUTION.csv", "03_SELECTIVE_PREDICTION.csv",
        "04_RETRAINED_PANEL_COMPARISON.csv", "04_PANEL_PAIRED_CONTRASTS.csv", "05_CALIBRATION_SWITCHING_ABLATION.csv",
        "05_ABLATION_PAIRED_CONTRASTS.csv", "07_PIDD_ESTIMANDS.csv", "07_RUNTIME_PAIRED_COMPARISONS.csv",
        "07_STATISTICAL_VERIFICATION_PUBLIC.csv", "PANEL_DEFINITIONS.csv", "BASE_MODEL_CONFIGURATIONS.csv",
        "MODEL_CONFIGURATIONS.csv", "PANEL_TASK_MANIFEST.csv", "PANEL_FINDING_COUNTS.csv", "06_COMPUTATIONAL_COST.csv",
        "A4_MAIN_TEXT_TABLE.csv", "A4_INFERENCE_SUMMARY.csv", "A4_TRAINING_SUMMARY.csv", "A4_HISTORICAL_MODEL_COSTS.csv",
        "A4_HISTORICAL_TIMING.csv", "A4_HISTORICAL_TRIAL_TIMING.csv", "A4_STORAGE_DETAILS.csv",
        "A4_STORAGE_VERIFICATION.csv", "A4_COMPONENT_STORAGE_VERIFICATION.csv", "A4_COMPARATOR_COSTS.csv"]
    for source in supplementary:
        yield f"04_SUPPLEMENTARY_TABLES/{Path(source).stem}", Path(source).stem, SOURCES + source, lambda r: True, None, "Exact source copy; includes negative and nonsignificant results.", False
    for source in ["dataset_characteristics.csv", "full_panel_model_performance.csv", "model_performance_confidence_intervals.csv",
                   "model_paired_comparisons.csv", "calibration_selection.csv", "repeated_panel_all_system_performance.csv",
                   "availability_panel_confidence_intervals.csv", "availability_panel_degradation.csv",
                   "routing_fallback_performance.csv", "selective_prediction_confidence_intervals.csv"]:
        yield f"04_SUPPLEMENTARY_TABLES/frozen_{Path(source).stem}", source, FROZEN + source, lambda r: True, None, "Unmodified frozen aggregate evidence.", False


def expected_tables():
    outputs, index = {}, []
    for name, title, source, select, columns, note, rounded in specifications():
        fields, all_rows = read_rows(ROOT / source)
        selection = [i for i, row in enumerate(all_rows) if select(row)]
        rows = [all_rows[i] for i in selection]
        if not rows:
            raise ValueError(f"Empty curated selection: {name}")
        columns = (columns or [c for c in fields if c != "source"]) if rounded else fields
        data = csv_bytes(columns, rows) if rounded else (ROOT / source).read_bytes()
        outputs[name + ".csv"] = data
        if rounded:
            outputs[name + ".md"] = table_markdown(title, columns, rows, note)
        index.append({"table": name + ".csv", "source": source, "source_sha256": sha(ROOT / source),
                      "source_data_row_indexes_zero_based": selection, "columns": columns, "rows": len(rows),
                      "method": "exact source-string projection" if rounded else "byte-identical aggregate source copy"})
    return outputs, index


def write_new(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)


def build(destination):
    outputs, index = expected_tables()
    for name, data in outputs.items():
        write_new(destination / name, data)
    write_new(destination / INDEX, (json.dumps(index, indent=2) + "\n").encode())
    source_map = ["# Publication table source map", "", "Every curated CSV is listed below. TABLE_SOURCE_INDEX.json records each source hash, selected data-row index (zero based), column and row count. Six-significant-figure Markdown is a deterministic view of the exact-string CSV; supplementary CSVs are byte-identical copies. Sources remain authoritative and unchanged.", "", "| Curated table | Repository source | Rows |", "| --- | --- | --- |"]
    source_map.extend(f"| {r['table']} | {r['source']} | {r['rows']} |" for r in index)
    source_map.extend(["", "Public snapshot curation uses saved aggregate values only. The original metadata-bearing statistical verification CSV is excluded; 07_STATISTICAL_VERIFICATION_PUBLIC.csv preserves every retained column string and removes the private source-path column. No fitting, prediction or new timing occurs.", "", "The source index binds these 47 curated tables. The complete public snapshot has its own publication_release/PUBLIC_EVIDENCE_MANIFEST.csv and SNAPSHOT_PROVENANCE.json. Original research seals/history remain separately preserved; their completeness is not claimed for this sanitized subset.", ""])
    write_new(destination / "08_SOURCE_MAP.md", "\n".join(source_map).encode())


def close(actual, expected, label, tolerance=1e-10):
    if not np.isclose(actual, expected, atol=tolerance, rtol=0, equal_nan=True):
        raise ValueError(f"Verification discrepancy: {label}: {actual} != {expected}")


def check_contrasts():
    """Recompute saved-draw intervals/tails, source point differences and Holm."""
    from .statistics import holm
    count = 0
    for name in ["04_PANEL_PAIRED_CONTRASTS.csv", "05_ABLATION_PAIRED_CONTRASTS.csv", "07_RUNTIME_PAIRED_COMPARISONS.csv"]:
        frame = pd.read_csv(REPORT / name, float_precision="round_trip")
        corrected = holm(frame, ["dataset", "metric"])
        for i, row in frame.iterrows():
            close(row.holm_adjusted_p_value, corrected.loc[i, "holm_adjusted_p_value"], name + "/Holm")
            with np.load(ROOT / row.bootstrap_distribution, allow_pickle=False) as draws:
                j = list(draws["metric_names"]).index(row.metric)
                difference = draws[row.model_a][:, j] - draws[row.model_b][:, j]
                assert len(difference) == row.n_bootstrap == 2000
                lower, upper = np.quantile(difference, [.025, .975])
                p = min(1., 2 * min((np.sum(difference <= 0) + 1) / (len(difference) + 1),
                                   (np.sum(difference >= 0) + 1) / (len(difference) + 1)))
            close(lower, row.ci_lower_a_minus_b, name + "/lower")
            close(upper, row.ci_upper_a_minus_b, name + "/upper")
            close(p, row.paired_bootstrap_p_value, name + "/tail")
            if name.startswith("04"):
                points = pd.read_csv(REPORT / "04_RETRAINED_PANEL_COMPARISON.csv", float_precision="round_trip")
                sub = points[(points.dataset == row.dataset) & (points.panel == row.panel)].set_index("comparison_arm")
            elif name.startswith("05"):
                points = pd.read_csv(REPORT / "05_CALIBRATION_SWITCHING_ABLATION.csv", float_precision="round_trip")
                sub = points[points.dataset == row.dataset].set_index("system")
            else:
                points = pd.read_csv(ROOT / FROZEN / "routing_fallback_performance.csv", float_precision="round_trip")
                sub = points[points.dataset == row.dataset].set_index("system")
            effect = sub.loc[row.model_a, row.metric] - sub.loc[row.model_b, row.metric]
            close(effect, row.observed_difference_a_minus_b, name + "/effect")
            direction = 1 if row.metric in {"auroc", "average_precision"} else -1
            close(direction * effect, row.observed_improvement_a_over_b, name + "/direction")
            count += 1
    return count


def check_repeat_summaries():
    data = pd.read_csv(REPORT / "01_PER_REPEAT_SENSITIVITY.csv", keep_default_na=False, float_precision="round_trip")
    keys = ["dataset", "analysis", "model", "scenario", "system", "probability_version"]
    count = 0
    for _, frame in data.groupby(keys, dropna=False):
        repeats = frame[frame.summary == "per_repeat"]
        assert len(repeats) == 5 and repeats.repeat.nunique() == 5
        for metric in METRICS:
            values = repeats[metric].astype(float)
            for label, expected in [("repeat_metric_mean", values.mean()), ("repeat_metric_sample_sd", values.std(ddof=1))]:
                close(float(frame[frame.summary == label][metric].iloc[0]), expected, "repeat/" + metric)
                count += 1
            mean = float(frame[frame.summary == "repeat_metric_mean"][metric].iloc[0])
            primary = float(frame[frame.summary == "participant_mean_probability_metric"][metric].iloc[0])
            close(float(frame[frame.summary == "repeat_metric_mean_minus_primary"][metric].iloc[0]), mean-primary, "repeat difference")
    return count


def verify_tables(destination):
    outputs, index = expected_tables()
    for name, data in outputs.items():
        if (destination / name).read_bytes() != data:
            raise ValueError(f"Curated numerical/display table mismatch: {name}")
    if json.loads((destination / INDEX).read_text()) != index:
        raise ValueError("Source-index mismatch")
    return {"tables": len(index), "rounded_tables": sum(p.endswith('.md') for p in outputs),
            "source_rows_curated": sum(r["rows"] for r in index)}


def verify_science():
    # All earlier source/report bytes remain bound by the unchanged A4-era seal.
    previous = json.loads((REPORT / "FINAL_HANDOFF_CHECKSUMS.json").read_text())
    for relative, digest in previous["files"].items():
        if sha(ROOT / relative) != digest:
            raise ValueError("Existing sealed evidence changed: " + relative)
    before = PRIVATE / "final_handoff_v1/pre_finalization_manifest.json"
    manuscript_count = None
    if before.exists():
        inventory = json.loads(before.read_text())
        for relative, digest in inventory["analysis_files"].items():
            if sha(ROOT / relative) != digest:
                raise ValueError("Before-finalization evidence changed: " + relative)
        for absolute, digest in inventory["manuscript_package"].items():
            if sha(Path(absolute)) != digest:
                raise ValueError("Manuscript package changed: " + absolute)
        manuscript_count = len(inventory["manuscript_package"])
    immutable = json.loads((PRIVATE / "a4_reporting_v2/private_measurement_manifest.json").read_text())
    for relative, digest in immutable["files"].items():
        if sha(ROOT / relative) != digest:
            raise ValueError("Private measurement evidence changed: " + relative)
    routes = pd.read_csv(REPORT / "02_ROUTING_DISTRIBUTION.csv")
    for dataset, (n, events) in EXPECTED.items():
        sub = routes[(routes.dataset == dataset) & (routes.row_type == "unique_panel")]
        assert sub.evaluation_records.sum() == n and sub.positive_events.sum() == events
    hospital = routes[(routes.dataset == "hospital130") & (routes.row_type == "unique_panel")]
    assert len(hospital) == 1 and hospital.iloc[0].panel == "encounter_utilization" and hospital.iloc[0].evaluation_records == 19868
    comparisons = pd.read_csv(REPORT / "04_PANEL_PAIRED_CONTRASTS.csv")
    brfss = comparisons[(comparisons.dataset == "brfss") & (comparisons.panel != "full")]
    assert len(brfss) == 20 and (brfss.observed_improvement_a_over_b > 0).all() and (brfss.holm_adjusted_p_value < .05).all()
    ablation = pd.read_csv(REPORT / "05_CALIBRATION_SWITCHING_ABLATION.csv")
    hospital_points = ablation[ablation.dataset == "hospital130"].set_index("system")
    close(hospital_points.loc["A", "auroc"], .63426, "Hospital A target", 5e-6)
    close(hospital_points.loc["D", "auroc"], .62714, "Hospital D target", 5e-6)
    selective = pd.read_csv(REPORT / "03_SELECTIVE_PREDICTION.csv")
    for _, row in selective.iterrows():
        assert row.accepted_n + row.rejected_n == row.total_n
        assert row.accepted_positive_events + row.rejected_positive_events == row.total_positive_events
        assert row.availability_abstained_n + row.confidence_rejected_n == row.rejected_n
        assert row.availability_abstained_events + row.confidence_rejected_events == row.rejected_positive_events
        close(row.accepted_n/row.total_n, row.actual_observation_coverage, "observation coverage")
        close(row.accepted_positive_events/row.total_positive_events, row.positive_event_coverage, "event coverage")
    selected = selective[(selective.dataset == "brfss") & (selective.system == "availability_router") & (selective.nominal_coverage == .7)].iloc[0]
    close(selected.positive_event_coverage * 100, 26.94, "BRFSS event target", .005)
    costs = pd.read_csv(REPORT / "A4_MAIN_TEXT_TABLE.csv")
    for dataset, one, batch in [("pidd", 2.136, 6.272), ("sylhet", 28.034, 52.933), ("brfss", 2.147, 11.261), ("hospital130", 30.605, 45.909)]:
        row = costs[costs.dataset == dataset].iloc[0]
        close(row.D_single_median_ms, one, "inference single", .00051)
        close(row.D_batch256_median_ms, batch, "inference batch", .00051)
    status = json.loads((REPORT / "A4_VERIFICATION.json").read_text())
    assert (status["A4_reporting"], status["historical_components"], status["historical_replay"]) == ("COMPLETE", "PARTIAL", "BLOCKED")
    return {"passed": True, "existing_seal_files_unchanged": len(previous["files"]),
            "private_A4_files_unchanged": len(immutable["files"]), "manuscript_files_unchanged": manuscript_count,
            "paired_effect_interval_tail_Holm_records": check_contrasts(), "repeat_mean_sd_cells": check_repeat_summaries(),
            "routing_populations_checked": 4, "selective_rows_reconciled": len(selective),
            "new_model_fits": 0, "new_calibrator_fits": 0, "new_timing_measurements": 0,
            "A4_reporting": "COMPLETE", "historical_components": "PARTIAL", "historical_replay": "BLOCKED"}


def safe_member(info):
    path = PurePosixPath(info.filename)
    mode = info.external_attr >> 16
    if (path.is_absolute() or ".." in path.parts or "\\" in info.filename or ":" in info.filename
            or stat.S_ISLNK(mode) or info.is_dir()):
        raise ValueError("Unsafe archive member: " + info.filename)
    if path.suffix not in {".csv", ".md", ".json", ".py", ".yaml", ".txt", ".lock", ".toml"}:
        raise ValueError("Unapproved archive extension: " + info.filename)
    if set(path.parts).intersection({"outputs", "raw", ".git", "local_archives", ".venv-pipeline"}):
        raise ValueError("Private/unrelated archive path: " + info.filename)


def seal_files():
    previous = json.loads((REPORT / "FINAL_HANDOFF_CHECKSUMS.json").read_text())
    files = {relative: sha(ROOT / relative) for relative in previous["files"]}
    files["analysis/journal_revision/FINAL_HANDOFF_CHECKSUMS.json"] = sha(REPORT / "FINAL_HANDOFF_CHECKSUMS.json")
    for _, _, source, _, _, _, _ in specifications():
        files[source] = sha(ROOT / source)
    for relative in ["config/authoritative_studies.yaml", "config/availability_scenarios.yaml",
                     "requirements.lock", "pyproject.toml", "results/final_publication/provenance/frozen_protocol.yaml"]:
        files[relative] = sha(ROOT / relative)
    for path in HANDOFF.rglob("*"):
        if path.is_file():
            files[str(path.relative_to(ROOT))] = sha(path)
    for relative in ["src/diabetes_pipeline/journal_revision/handoff.py", "scripts/finalize_journal_handoff.py",
                     "tests/test_journal_handoff.py", "analysis/journal_revision/MODEL_ANALYSIS_FINAL_READINESS.md",
                     "analysis/journal_revision/MODEL_ANALYSIS_FINAL_QA.md", "analysis/journal_revision/MODEL_ANALYSIS_FINAL_VERIFICATION.json",
                     "analysis/journal_revision/MODEL_ANALYSIS_FINAL_TEST_RESULTS.json"]:
        files[relative] = sha(ROOT / relative)
    return dict(sorted(files.items()))


def seal():
    write_new(SEAL, (json.dumps({"version": "journal_revision_final_author_handoff_v1", "files": seal_files(),
        "previous_seal_sha256": sha(REPORT / "FINAL_HANDOFF_CHECKSUMS.json"),
        "scope": "Existing scientific evidence unchanged; curated aggregate tables and documentation added. Local commit receipt binds the eventual commit without a circular self-hash."}, indent=2) + "\n").encode())


def archive_inputs():
    files = json.loads(SEAL.read_text())["files"]
    for relative, digest in files.items():
        if sha(ROOT / relative) != digest:
            raise ValueError("Final sealed content changed: " + relative)
    paths = sorted(files) + [str(SEAL.relative_to(ROOT))]
    # Small tracked source/configuration dependencies make provenance references inspectable.
    paths += ["config/authoritative_studies.yaml", "config/availability_scenarios.yaml", "requirements.lock", "pyproject.toml",
              "results/final_publication/provenance/frozen_protocol.yaml"]
    return sorted(set(paths))


def make_archive():
    if ARCHIVE.exists() or ARCHIVE_MANIFEST.exists():
        raise FileExistsError("Preserve the delivered archive; use a new release version")
    paths = archive_inputs()
    with zipfile.ZipFile(ARCHIVE, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for relative in paths:
            path = ROOT / relative
            if path.is_symlink():
                raise ValueError("Symlink in handoff: " + relative)
            info = zipfile.ZipInfo(relative, (2026, 10, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            safe_member(info)
            data = path.read_bytes()
            data.decode("utf-8")
            if path.suffix == ".csv":
                read_rows(path)
            handle.writestr(info, data)
    verify_archive(paths)
    lines = ["# Final journal revision handoff archive", "", f"Location: `{ARCHIVE.relative_to(ROOT)}`", "",
        f"Size: {ARCHIVE.stat().st_size} bytes", "", f"SHA-256: `{sha(ARCHIVE)}`", "", f"Files: {len(paths)}", "",
        "The ZIP is a local release artifact excluded from Git. This manifest/checksum is committed. It contains the current A4-complete package, curated exact/rounded author tables, code/tests and safe provenance. Original data, row-level predictions, fitted objects, caches, secrets and the previous ZIP are excluded. Sources with private paths are references only. Supplementary source copies are explicitly byte-identical, not competing result versions.", "",
        "Commit identity is recorded after committing in JOURNAL_REVISION_HANDOFF_FINAL_COMMIT_RECEIPT.json (local, excluded): a commit cannot contain its own SHA. The receipt binds the resulting commit to this exact ZIP and manifest. The committed readiness assessment gives an equivalent Git query.", "",
        "All members passed UTF-8 readability, extension/path/symlink checks, CRC verification and extraction/hash comparison. A checkout is required to run the full test suite; private original artifacts are additionally required for full evidence verification.", "",
        "| Included repository-relative path | Bytes | SHA-256 |", "| --- | --- | --- |"]
    lines += [f"| {relative} | {(ROOT/relative).stat().st_size} | {sha(ROOT/relative)} |" for relative in paths]
    write_new(ARCHIVE_MANIFEST, ("\n".join(lines) + "\n").encode())


def verify_archive(paths=None):
    paths = paths or archive_inputs()
    with zipfile.ZipFile(ARCHIVE) as handle, tempfile.TemporaryDirectory(prefix="t2dm-handoff-check-") as temp:
        assert sorted(handle.namelist()) == sorted(paths) and len(handle.namelist()) == len(set(handle.namelist()))
        assert handle.testzip() is None
        for info in handle.infolist():
            safe_member(info)
            original = ROOT / info.filename
            data = handle.read(info)
            data.decode("utf-8")
            assert data == original.read_bytes()
        handle.extractall(temp)
        for relative in paths:
            if sha(Path(temp) / relative) != sha(ROOT / relative):
                raise ValueError("Archive extraction mismatch: " + relative)
    if ARCHIVE_MANIFEST.exists():
        text = ARCHIVE_MANIFEST.read_text()
        assert f"Size: {ARCHIVE.stat().st_size} bytes" in text and f"Files: {len(paths)}" in text
        assert f"SHA-256: `{sha(ARCHIVE)}`" in text
        for relative in paths:
            assert f"| {relative} | {(ROOT/relative).stat().st_size} | {sha(ROOT/relative)} |" in text
    return {"archive_files": len(paths), "archive_bytes": ARCHIVE.stat().st_size, "archive_sha256": sha(ARCHIVE), "passed": True}


def reconstruct(destination):
    destination = Path(destination).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError("Reconstruction requires an empty destination")
    if destination == HANDOFF or destination.is_relative_to(REPORT) or destination.is_relative_to(PRIVATE):
        raise ValueError("Reconstruction must use a separate directory")
    destination.mkdir(parents=True, exist_ok=True)
    for path in HANDOFF.rglob("*.md"):
        if not set(path.relative_to(HANDOFF).parts).intersection({"03_MAIN_TEXT_TABLES", "04_SUPPLEMENTARY_TABLES"}) and path.name != "08_SOURCE_MAP.md":
            target = destination / path.relative_to(HANDOFF)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
    build(destination)
    return verify_tables(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "verify", "seal", "archive", "verify-archive", "reconstruct"])
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args()
    if args.phase == "prepare":
        build(HANDOFF)
        print(json.dumps(verify_tables(HANDOFF), indent=2))
    elif args.phase == "verify":
        result = {**verify_science(), **verify_tables(HANDOFF)}
        print(json.dumps(result, indent=2))
    elif args.phase == "seal":
        seal()
        print(f"Sealed {len(seal_files())} files")
    elif args.phase == "archive":
        make_archive()
        print(json.dumps(verify_archive(), indent=2))
    elif args.phase == "verify-archive":
        print(json.dumps(verify_archive(), indent=2))
    elif args.phase == "reconstruct":
        if args.destination is None:
            parser.error("--destination is required")
        print(json.dumps(reconstruct(args.destination), indent=2))


if __name__ == "__main__":
    main()
