"""Reproducible leakage, missingness, grouping, and survey-design audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.data.manifests import build_audit
from diabetes_pipeline.settings import DEFAULT_OUTPUT_ROOT, get_dataset_config
from diabetes_pipeline.splitting.registry import validate_split_manifest
from diabetes_pipeline.splitting.strategies import build_split_manifest


BRFSS_DESIGN_COLUMNS = ("_STATE", "_PSU", "_STSTR", "_LLCPWT")


def _finite_summary(series: pd.Series) -> dict[str, Any]:
    numeric = pd.to_numeric(series, errors="coerce")
    finite = numeric[np.isfinite(numeric.to_numpy(dtype=float))]
    quantiles = (
        finite.quantile([0.0, 0.01, 0.25, 0.5, 0.75, 0.99, 1.0]).to_dict()
        if len(finite)
        else {}
    )
    return {
        "rows": int(len(series)),
        "missing": int(numeric.isna().sum()),
        "finite": int(len(finite)),
        "unique": int(finite.nunique()),
        "non_positive": int((finite <= 0).sum()),
        "quantiles": {str(key): float(value) for key, value in quantiles.items()},
    }


def _safe_weighted_prevalence(y: np.ndarray, weights: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    weights = np.asarray(weights, dtype=float)
    valid = np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    if not np.any(valid):
        return float("nan")
    return float(np.average(y[valid], weights=weights[valid]))


def audit_brfss_survey_design(dataset: LoadedDataset) -> dict[str, Any]:
    """Audit design variables without incorporating them into model fitting."""

    cfg = get_dataset_config("brfss")
    columns = ["DIABETE3", *BRFSS_DESIGN_COLUMNS]
    raw = pd.read_csv(cfg["raw_path"], usecols=columns, low_memory=False)
    encoding = cfg["target_encoding"]
    positive = list(encoding["positive_raw_values"])
    negative = list(encoding["negative_raw_values"])
    retained = raw.loc[raw["DIABETE3"].isin(positive + negative)].copy()
    if len(retained) != len(dataset.X):
        raise ValueError(
            "BRFSS survey-design audit and modelling cohort have different row counts"
        )
    target_map = {value: 1 for value in positive}
    target_map.update({value: 0 for value in negative})
    y = retained["DIABETE3"].map(target_map).to_numpy(dtype=int)
    weights = pd.to_numeric(retained["_LLCPWT"], errors="coerce").to_numpy(
        dtype=float
    )
    return {
        "available": True,
        "variables": {
            column: _finite_summary(retained[column])
            for column in BRFSS_DESIGN_COLUMNS
        },
        "state_count": int(retained["_STATE"].nunique(dropna=True)),
        "stratum_count": int(retained["_STSTR"].nunique(dropna=True)),
        "psu_count": int(retained["_PSU"].nunique(dropna=True)),
        "unweighted_prevalence": float(np.mean(y)),
        "llcpwt_weighted_prevalence": _safe_weighted_prevalence(y, weights),
        "weights_used_by_current_prediction_pipeline": False,
        "interpretation": (
            "Design variables are present in the raw file but are not currently "
            "used by model fitting, performance estimation, or subgroup uncertainty."
        ),
    }


def _missingness_by_outcome(dataset: LoadedDataset) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for feature in dataset.X.columns:
        missing = dataset.X[feature].isna()
        result[str(feature)] = {
            str(outcome): {
                "missing": int(missing[dataset.y == outcome].sum()),
                "rows": int((dataset.y == outcome).sum()),
                "rate": float(missing[dataset.y == outcome].mean()),
            }
            for outcome in (0, 1)
        }
    return result


def _group_integrity(dataset: LoadedDataset) -> dict[str, Any]:
    if dataset.groups is None:
        return {
            "grouped": False,
            "group_count": None,
            "repeated_group_count": None,
            "rows_in_repeated_groups": None,
            "discordant_outcome_group_count": None,
        }
    group_frame = pd.DataFrame(
        {"group": dataset.groups.astype(str), "target": dataset.y.astype(int)}
    )
    sizes = group_frame.groupby("group", sort=False).size()
    outcome_counts = group_frame.groupby("group", sort=False)["target"].nunique()
    repeated = sizes[sizes > 1]
    return {
        "grouped": True,
        "group_count": int(len(sizes)),
        "repeated_group_count": int(len(repeated)),
        "rows_in_repeated_groups": int(repeated.sum()),
        "largest_group_size": int(sizes.max()),
        "discordant_outcome_group_count": int((outcome_counts > 1).sum()),
    }


def _split_integrity(dataset: LoadedDataset, seed: int) -> dict[str, Any]:
    cfg = get_dataset_config(dataset.name)
    manifest = build_split_manifest(dataset, cfg, seed=seed)
    validate_split_manifest(dataset, manifest, cfg)
    holdout = cfg["evaluation_strategy"] in {
        "stratified_holdout_cv",
        "stratified_group_holdout_cv",
    }
    group_overlap = False
    if holdout and dataset.groups is not None:
        development = set(
            manifest.loc[manifest["role"] == "development", "group_id"].astype(str)
        )
        test = set(manifest.loc[manifest["role"] == "test", "group_id"].astype(str))
        group_overlap = bool(development & test)
    return {
        "strategy": str(cfg["evaluation_strategy"]),
        "seed": int(seed),
        "rows": int(len(manifest)),
        "validation_passed": True,
        "group_overlap": bool(group_overlap),
        "manifest_contains_outcomes": "target" in manifest.columns,
        "ordinary_metadata_exposes_partition_outcomes": True,
        "eligible_as_concealed_final_manifest": False,
        "use": "development only",
    }


def audit_dataset_research_controls(
    dataset: LoadedDataset, *, seed: int = 42
) -> dict[str, Any]:
    cfg = get_dataset_config(dataset.name)
    base = build_audit(dataset, cfg)
    result: dict[str, Any] = {
        "dataset": dataset.name,
        "endpoint": base["endpoint"],
        "rows": base["retained_rows"],
        "events": int(dataset.y.sum()),
        "prevalence": base["positive_prevalence"],
        "missing_by_feature": base["missing_by_feature"],
        "rows_with_any_missing_feature": base["rows_with_any_missing_feature"],
        "duplicate_feature_rows": base["duplicate_feature_rows"],
        "duplicate_feature_target_rows": base["duplicate_feature_target_rows"],
        "missingness_by_outcome": _missingness_by_outcome(dataset),
        "group_integrity": _group_integrity(dataset),
        "split_integrity": _split_integrity(dataset, seed),
    }
    if dataset.name == "brfss":
        result["survey_design"] = audit_brfss_survey_design(dataset)
    return result


def build_research_audit(*, seed: int = 42) -> dict[str, Any]:
    datasets = {
        name: audit_dataset_research_controls(load_dataset(name), seed=seed)
        for name in ("pidd", "sylhet", "brfss", "hospital130")
    }
    return {
        "schema_version": "1.0",
        "seed": int(seed),
        "evidence_tier": "development_audit",
        "final_outcome_access_authorized": False,
        "datasets": datasets,
    }


def render_research_audit_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Research Data, Leakage, and Applicability Audit",
        "",
        f"**Evidence tier:** `{audit['evidence_tier']}`",
        "",
        "**Final outcome access authorized:** `false`",
        "",
        "| Dataset | Rows | Events | Prevalence | Any missing | Duplicate feature rows | Group integrity |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for name, row in audit["datasets"].items():
        groups = row["group_integrity"]
        group_text = (
            f"{groups['group_count']} groups; {groups['discordant_outcome_group_count']} discordant"
            if groups["grouped"]
            else "not grouped"
        )
        lines.append(
            f"| {name} | {row['rows']:,} | {row['events']:,} | "
            f"{row['prevalence']:.4f} | {row['rows_with_any_missing_feature']:,} | "
            f"{row['duplicate_feature_rows']:,} | {group_text} |"
        )
    lines.extend(["", "## Split-control finding", ""])
    lines.append(
        "All seed-42 manifests pass their configured structural validation, but "
        "they contain the outcome column and their ordinary metadata exposes "
        "partition event counts and prevalence. They are development manifests, "
        "not concealed final manifests."
    )
    brfss = audit["datasets"]["brfss"].get("survey_design", {})
    if brfss:
        lines.extend(["", "## BRFSS survey design", ""])
        lines.append(
            f"The retained cohort contains {brfss['state_count']} state codes, "
            f"{brfss['stratum_count']} sampling strata, and "
            f"{brfss['psu_count']} primary sampling units. The raw "
            "`_LLCPWT` weight is available."
        )
        lines.append(
            f"Unweighted prevalence is {brfss['unweighted_prevalence']:.4f}; "
            f"the simple `_LLCPWT`-weighted prevalence is "
            f"{brfss['llcpwt_weighted_prevalence']:.4f}. This weighted descriptive "
            "value is not a design-correct variance estimate."
        )
        lines.append(
            "The current prediction pipeline does not use weights, strata, or PSUs; "
            "population-representative claims are therefore prohibited unless a "
            "prespecified survey-aware analysis is added."
        )
    lines.extend(["", "## Dataset-specific controls", ""])
    lines.extend(
        [
            "- PIDD: physiological zero-as-missing handling is outcome-blind and must remain fold-imputed.",
            "- Sylhet: identical predictor profiles are grouped; discordant-outcome groups must be disclosed if present.",
            "- BRFSS: cross-sectional self-reported status is not future incidence.",
            "- Hospital130: patient grouping is mandatory and the endpoint remains 30-day readmission.",
            "",
        ]
    )
    return "\n".join(lines)


def write_research_audit(
    *, seed: int = 42, output_root: Path = DEFAULT_OUTPUT_ROOT
) -> tuple[Path, Path, dict[str, Any]]:
    audit = build_research_audit(seed=seed)
    output_dir = output_root / "research_audit"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"research_audit_seed_{seed}.json"
    md_path = output_dir / f"research_audit_seed_{seed}.md"
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_research_audit_markdown(audit), encoding="utf-8")
    return json_path, md_path, audit
