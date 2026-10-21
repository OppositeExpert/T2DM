"""Dataset checksums and human-readable audit reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.data.validators import validate_dataset
from diabetes_pipeline.settings import (
    DEFAULT_OUTPUT_ROOT,
    configuration_sha256,
    get_dataset_config,
)


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def build_audit(dataset: LoadedDataset, cfg: dict[str, Any]) -> dict[str, Any]:
    validate_dataset(dataset, cfg)
    feature_target = dataset.X.copy()
    feature_target["__target__"] = dataset.y
    class_counts = dataset.y.value_counts().sort_index().to_dict()
    group_count = int(dataset.groups.nunique()) if dataset.groups is not None else None
    group_sizes = dataset.groups.value_counts() if dataset.groups is not None else None

    return {
        "dataset": dataset.name,
        "configuration_sha256": configuration_sha256(cfg),
        "display_name": dataset.metadata["display_name"],
        "task": dataset.metadata["task"],
        "endpoint": dataset.metadata["endpoint"],
        "source_url": dataset.metadata.get("source_url"),
        "target_encoding": dataset.metadata.get("target_encoding", {}),
        "raw_path": dataset.metadata["raw_path"],
        "raw_sha256": sha256_file(Path(dataset.metadata["raw_path"])),
        "raw_rows": dataset.metadata["raw_rows"],
        "retained_rows": len(dataset.X),
        "excluded_rows": dataset.metadata["raw_rows"] - len(dataset.X),
        "n_features": dataset.X.shape[1],
        "target_counts": {str(key): int(value) for key, value in class_counts.items()},
        "positive_prevalence": float(dataset.y.mean()),
        "missing_by_feature": {
            column: int(count) for column, count in dataset.X.isna().sum().items()
        },
        "rows_with_any_missing_feature": int(dataset.X.isna().any(axis=1).sum()),
        "duplicate_feature_rows": int(dataset.X.duplicated().sum()),
        "duplicate_feature_target_rows": int(feature_target.duplicated().sum()),
        "group_strategy": cfg.get("group_strategy", "none"),
        "n_groups": group_count,
        "largest_group_size": int(group_sizes.max()) if group_sizes is not None else None,
        "numeric_features": list(cfg["numeric_features"]),
        "categorical_features": list(cfg["categorical_features"]),
        "applicability_notes": list(cfg.get("applicability_notes", [])),
    }


def audit_to_markdown(audit: dict[str, Any]) -> str:
    lines = [
        f"# Dataset Audit: {audit['display_name']}",
        "",
        f"- Dataset key: `{audit['dataset']}`",
        f"- Task: `{audit['task']}`",
        f"- Endpoint: `{audit['endpoint']}`",
        f"- Source documentation: {audit['source_url'] or 'not recorded'}",
        f"- Raw rows: {audit['raw_rows']:,}",
        f"- Retained rows: {audit['retained_rows']:,}",
        f"- Excluded rows: {audit['excluded_rows']:,}",
        f"- Predictors: {audit['n_features']}",
        f"- Positive prevalence: {audit['positive_prevalence']:.4f}",
        f"- Feature-duplicate rows: {audit['duplicate_feature_rows']:,}",
        f"- Feature-plus-target duplicate rows: {audit['duplicate_feature_target_rows']:,}",
        f"- Group strategy: `{audit['group_strategy']}`",
        f"- Groups: {audit['n_groups'] if audit['n_groups'] is not None else 'not applicable'}",
        "",
        "## Missingness",
        "",
        "| Feature | Missing |",
        "|---|---:|",
    ]
    for feature, count in audit["missing_by_feature"].items():
        lines.append(f"| {feature} | {count:,} |")
    lines.extend(["", "## Applicability notes", ""])
    lines.extend(f"- {note}" for note in audit["applicability_notes"])
    lines.append("")
    return "\n".join(lines)


def write_audit(
    dataset: LoadedDataset,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> tuple[Path, Path, dict[str, Any]]:
    cfg = get_dataset_config(dataset.name)
    audit = build_audit(dataset, cfg)
    config_id = audit["configuration_sha256"][:12]
    audit_dir = output_root / "manifests" / "audits" / dataset.name / config_id
    audit_dir.mkdir(parents=True, exist_ok=True)
    json_path = audit_dir / "audit.json"
    md_path = audit_dir / "audit.md"
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(audit_to_markdown(audit), encoding="utf-8")
    return json_path, md_path, audit
