"""Shared identity, provenance, and output contracts for journal revisions."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from diabetes_pipeline.evaluation.metrics import binary_metrics

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "analysis/journal_revision"
PRIVATE = ROOT / "outputs/journal_revision_v1"
METRICS = ("auroc", "average_precision", "brier_score", "log_loss")
DIAGNOSTICS = METRICS + ("calibration_intercept", "calibration_slope",
                         "observed_expected_ratio", "expected_calibration_error")
EXPECTED = {"pidd": (768, 268), "sylhet": (520, 320),
            "brfss": (85872, 11451), "hospital130": (19868, 2262)}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    temporary.replace(path)


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"row_id": str, "group_id": str},
                        keep_default_na=False, low_memory=False, **kwargs)
    # Unsupported records have blank probabilities. Retain string IDs while
    # resolving blank numerical fields to NaN, rather than a string column.
    for column in frame.columns:
        if column.startswith("probability_") or column in {"threshold", "confidence"}:
            frame[column] = pd.to_numeric(frame[column].replace("", np.nan), errors="raise")
    return frame


def studies():
    cfg = yaml.safe_load((ROOT / "config/authoritative_studies.yaml").read_text())
    for name, info in cfg["studies"].items():
        directory = ROOT / "outputs/publication_pipeline/studies" / info["study_id"]
        metadata = json.loads((directory / "experiment_metadata.json").read_text())
        yield name, directory, metadata


def panels():
    cfg = yaml.safe_load((ROOT / "config/availability_scenarios.yaml").read_text())
    return cfg["datasets"]


def bundle_paths(directory: Path):
    return sorted((directory / "availability_routing/router_bundles").glob("*.joblib"))


def numeric_probability(frame: pd.DataFrame, column="probability_calibrated") -> np.ndarray:
    values = pd.to_numeric(frame[column], errors="raise").to_numpy(float)
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError("Invalid probability")
    return values


def metrics(frame: pd.DataFrame, column="probability_calibrated") -> dict:
    y = frame["target"].to_numpy(int)
    if len(y) == 0 or len(np.unique(y)) != 2:
        return {key: np.nan for key in DIAGNOSTICS}
    result = binary_metrics(y, numeric_probability(frame, column))
    return {key: result[key] for key in DIAGNOSTICS}


def aggregate(frame: pd.DataFrame, keys: list[str], expected_repeats: int) -> pd.DataFrame:
    """Require one OOF row per record and repeat, with invariant labels/groups."""
    frame = frame.copy()
    if "repeat" not in frame:
        frame["repeat"] = 0
    frame["row_id"] = frame["row_id"].astype(str)
    frame["group_id"] = frame["group_id"].fillna("").astype(str)
    if frame.duplicated(keys + ["row_id", "repeat"]).any():
        raise ValueError("Duplicate evaluation identity within repeat")
    counts = frame.groupby(keys + ["row_id"], dropna=False).agg(
        repeats=("repeat", "nunique"), labels=("target", "nunique"),
        groups=("group_id", "nunique"))
    if counts["repeats"].ne(expected_repeats).any():
        raise ValueError("Incomplete repeat coverage")
    if counts[["labels", "groups"]].ne(1).any().any():
        raise ValueError("Outcome/group identity changed")
    numeric_probability(frame)
    mappings = {"target": ("target", "first"), "group_id": ("group_id", "first"),
                "probability_calibrated": ("probability_calibrated", "mean")}
    if "probability_raw" in frame:
        numeric_probability(frame, "probability_raw")
        mappings["probability_raw"] = ("probability_raw", "mean")
    return frame.groupby(keys + ["row_id"], as_index=False, sort=True).agg(**mappings)


def align(a: pd.DataFrame, b: pd.DataFrame):
    a = a.sort_values("row_id").reset_index(drop=True)
    b = b.sort_values("row_id").reset_index(drop=True)
    if a["row_id"].duplicated().any() or b["row_id"].duplicated().any():
        raise ValueError("Duplicate paired identity")
    for key in ["row_id", "target", "group_id"]:
        if not np.array_equal(a[key].to_numpy(), b[key].to_numpy()):
            raise ValueError(f"Paired {key} mismatch")
    return a, b


def markdown_table(frame: pd.DataFrame, columns=None, limit=None) -> str:
    if columns is not None:
        frame = frame[columns]
    if limit is not None:
        frame = frame.head(limit)
    def fmt(value):
        if isinstance(value, (float, np.floating)):
            return "NA" if not np.isfinite(value) else f"{value:.6g}"
        return str(value).replace("|", "/").replace("\n", " ")
    lines = ["| " + " | ".join(frame.columns) + " |",
             "| " + " | ".join(["---"] * len(frame.columns)) + " |"]
    lines.extend("| " + " | ".join(fmt(v) for v in row) + " |"
                 for row in frame.itertuples(index=False, name=None))
    return "\n".join(lines)


def save_table(stem: str, frame: pd.DataFrame, narrative: str) -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    frame.to_csv(REPORT / f"{stem}.csv", index=False)
    (REPORT / f"{stem}.md").write_text(narrative.rstrip() + "\n")
