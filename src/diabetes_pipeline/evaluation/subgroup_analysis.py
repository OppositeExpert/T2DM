"""Prespecified development subgroup performance and abstention coverage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.evaluation.bootstrap import bootstrap_metric_intervals
from diabetes_pipeline.settings import source_tree_sha256


SUBGROUP_METRICS = (
    "auroc",
    "average_precision",
    "brier_score",
    "log_loss",
    "calibration_intercept",
    "calibration_slope",
    "sensitivity",
    "specificity",
)


@dataclass(frozen=True)
class SubgroupAnalysisResult:
    study_dir: Path
    output_dir: Path
    metrics_path: Path
    intervals_path: Path
    report_path: Path


def _age_groups(dataset_name: str, age: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(age, errors="coerce")
    if dataset_name == "brfss":
        return pd.cut(
            numeric,
            bins=[0, 3, 6, 9, 13],
            labels=["18-34", "35-49", "50-64", "65+"],
            include_lowest=True,
        ).astype("string")
    if dataset_name == "hospital130":
        return pd.cut(
            numeric,
            bins=[-np.inf, 2, 4, 6, np.inf],
            labels=["under_30", "30-49", "50-69", "70+"],
        ).astype("string")
    return pd.cut(
        numeric,
        bins=[0, 29, 44, 59, np.inf],
        labels=["under_30", "30-44", "45-59", "60+"],
        include_lowest=True,
    ).astype("string")


def subgroup_membership(dataset_name: str) -> pd.DataFrame:
    """Create prespecified interpretable subgroup labels keyed by stable row ID."""

    dataset = load_dataset(dataset_name)
    # Loaded cohorts retain source indexes after exclusions. Preserve that index
    # while assigning demographic Series so identities cannot shift silently.
    base = pd.DataFrame(
        {"row_id": dataset.row_ids.astype(str).to_numpy()}, index=dataset.X.index
    )
    frames: list[pd.DataFrame] = []
    age_column = "Age" if "Age" in dataset.X else "age" if "age" in dataset.X else None
    if age_column is not None:
        age = base.copy()
        age["subgroup_variable"] = "age_group"
        age["subgroup_value"] = _age_groups(dataset_name, dataset.X[age_column])
        frames.append(age)
    sex_column = next(
        (column for column in ("Gender", "Sex", "gender") if column in dataset.X),
        None,
    )
    if sex_column is not None:
        sex = base.copy()
        sex["subgroup_variable"] = "sex"
        if dataset_name == "hospital130":
            values = dataset.X[sex_column].astype("string").str.strip().str.lower()
            sex["subgroup_value"] = values.map(
                {"female": "female", "male": "male"}
            ).astype("string")
        else:
            values = pd.to_numeric(dataset.X[sex_column], errors="coerce")
            sex["subgroup_value"] = values.map({0.0: "female", 1.0: "male"}).astype(
                "string"
            )
        frames.append(sex)
    if dataset_name == "hospital130" and "race" in dataset.X:
        race = base.copy()
        race["subgroup_variable"] = "race"
        race["subgroup_value"] = dataset.X["race"].astype("string").str.strip()
        frames.append(race)
    if not frames:
        raise ValueError(f"No prespecified supported subgroups exist for {dataset_name}")
    membership = pd.concat(frames, ignore_index=True)
    return membership[membership["subgroup_value"].notna()].reset_index(drop=True)


def subgroup_performance_analysis(
    decisions: pd.DataFrame,
    membership: pd.DataFrame,
    *,
    n_bootstrap: int,
    seed: int,
    minimum_n: int,
    minimum_events: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate accepted-case metrics with explicit small-cell suppression."""

    required = {
        "dataset",
        "system",
        "scenario",
        "row_id",
        "group_id",
        "target",
        "probability_calibrated",
        "target_coverage",
        "accepted",
    }
    missing = sorted(required - set(decisions.columns))
    if missing:
        raise ValueError(f"Selective decisions lack columns: {missing}")
    frame = decisions.copy()
    frame["row_id"] = frame["row_id"].astype(str)
    merged = frame.merge(membership, on="row_id", how="inner", validate="many_to_many")
    metric_records: list[dict[str, Any]] = []
    interval_records: list[dict[str, Any]] = []
    analysis_index = 0
    keys = [
        "dataset",
        "system",
        "scenario",
        "target_coverage",
        "subgroup_variable",
        "subgroup_value",
    ]
    for values, subgroup in merged.groupby(keys, sort=True, dropna=False):
        dataset_name, system, scenario, coverage, variable, value = values
        accepted = subgroup[subgroup["accepted"]].reset_index(drop=True)
        total_n = len(subgroup)
        accepted_n = len(accepted)
        positives = int(accepted["target"].sum())
        negatives = int((accepted["target"] == 0).sum())
        base = {
            "dataset": str(dataset_name),
            "system": str(system),
            "scenario": str(scenario),
            "target_coverage": float(coverage),
            "subgroup_variable": str(variable),
            "subgroup_value": str(value),
            "total_n": int(total_n),
            "accepted_n": int(accepted_n),
            "abstained_n": int(total_n - accepted_n),
            "subgroup_coverage": float(accepted_n / total_n),
            "positive_events": positives,
            "negative_events": negatives,
            "accepted_prevalence": float(positives / accepted_n) if accepted_n else np.nan,
            "minimum_n": int(minimum_n),
            "minimum_events": int(minimum_events),
        }
        if (
            accepted_n < minimum_n
            or positives < minimum_events
            or negatives < minimum_events
        ):
            metric_records.append({**base, "status": "suppressed_small_cell"})
            analysis_index += 1
            continue
        group_values = accepted["group_id"].fillna("").astype(str).to_numpy(dtype=str)
        groups = group_values if np.any(np.char.str_len(group_values) > 0) else None
        intervals = bootstrap_metric_intervals(
            accepted["target"].to_numpy(dtype=int),
            accepted["probability_calibrated"].to_numpy(dtype=float),
            threshold=0.5,
            n_bootstrap=int(n_bootstrap),
            seed=int(seed) + analysis_index,
            metric_names=SUBGROUP_METRICS,
            groups=groups,
        )
        estimates = {str(row["metric"]): float(row["estimate"]) for row in intervals}
        metric_records.append({**base, "status": "estimated", **estimates})
        for row in intervals:
            interval_records.append({**base, **row})
        analysis_index += 1
    return pd.DataFrame(metric_records), pd.DataFrame(interval_records)


def _render_report(metadata: dict[str, Any], metrics: pd.DataFrame) -> str:
    estimated = metrics[metrics["status"] == "estimated"]
    suppressed = metrics[metrics["status"] != "estimated"]
    lines = [
        (
            "# Final Internal-Validation Subgroup and Fairness Analysis"
            if metadata.get("evidence_tier") == "final_internal_validation"
            else "# Development Subgroup and Fairness Analysis"
        ),
        "",
        f"**Dataset:** `{metadata['dataset']}`",
        "",
        f"**Profile:** `{metadata['profile']}`",
        "",
        f"**Estimated cells:** {len(estimated)}",
        "",
        f"**Suppressed cells:** {len(suppressed)}",
        "",
        "Cells are suppressed unless accepted observations include the configured "
        "minimum sample size and minimum positive and negative event counts. "
        "Subgroup coverage is reported with performance so selective prediction "
        "cannot hide disproportionate abstention.",
        "",
        "| Variable | Group | Coverage target | Actual coverage | N | Events | Brier | AP |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in estimated.sort_values(
        ["subgroup_variable", "subgroup_value", "target_coverage"],
        ascending=[True, True, False],
    ).iterrows():
        lines.append(
            f"| {row['subgroup_variable']} | {row['subgroup_value']} | "
            f"{row['target_coverage']:.2f} | {row['subgroup_coverage']:.3f} | "
            f"{int(row['accepted_n'])} | {int(row['positive_events'])} | "
            f"{row['brier_score']:.4f} | {row['average_precision']:.4f} |"
        )
    lines.extend(
        [
            "",
            "These analyses describe performance within the observed public-dataset "
            "cohorts. They do not establish population representativeness or causal "
            "fairness.",
            "",
        ]
    )
    return "\n".join(lines)


def run_subgroup_analysis(
    study_dir: Path | str,
    *,
    system: str = "availability_router",
    scenarios: Sequence[str] = ("full",),
    minimum_n: int = 50,
    minimum_events: int = 10,
) -> SubgroupAnalysisResult:
    """Run prespecified subgroup analysis from selective-prediction decisions."""

    study_dir = Path(study_dir).resolve()
    study_metadata = json.loads(
        (study_dir / "experiment_metadata.json").read_text(encoding="utf-8")
    )
    profile = dict(study_metadata["profile"])
    is_final_internal = (
        str(profile.get("name")) == "final_internal_validation"
        and bool(profile.get("locked", False))
        and study_metadata.get("evidence_tier") == "final_internal_validation"
    )
    if str(profile.get("name")) == "final" or (
        bool(profile.get("locked", False)) and not is_final_internal
    ):
        raise PermissionError("Development subgroup analysis is not a final-run command")
    decisions_path = study_dir / "selective_prediction" / "acceptance_decisions.csv"
    if not decisions_path.exists():
        raise FileNotFoundError(
            f"Run selective prediction before subgroup analysis: {decisions_path}"
        )
    decisions = pd.read_csv(decisions_path, low_memory=False)
    filtered = decisions[
        decisions["system"].eq(system) & decisions["scenario"].isin(scenarios)
    ].copy()
    if filtered.empty:
        raise ValueError("No selective-prediction decisions match the requested scope")
    dataset_name = str(study_metadata["dataset"])
    membership = subgroup_membership(dataset_name)
    metrics, intervals = subgroup_performance_analysis(
        filtered,
        membership,
        n_bootstrap=int(profile["n_bootstrap"]),
        seed=int(profile["seed"]) + 1_400_000,
        minimum_n=int(minimum_n),
        minimum_events=int(minimum_events),
    )
    output_dir = study_dir / "subgroup_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "schema_version": "1.0",
        "dataset": dataset_name,
        "source_study": str(study_dir),
        "profile": str(profile["name"]),
        "evidence_tier": (
            "final_internal_validation"
            if is_final_internal
            else "execution_only"
            if str(profile["name"]) == "smoke"
            else "development_only"
        ),
        "system": system,
        "scenarios": list(scenarios),
        "minimum_n": int(minimum_n),
        "minimum_positive_events": int(minimum_events),
        "minimum_negative_events": int(minimum_events),
        "small_cell_suppression": True,
        "source_tree_sha256": source_tree_sha256(),
        "subgroup_analysis_complete": is_final_internal,
        "publication_evidence_eligible": is_final_internal,
        "final_outcome_access_authorized": False,
    }
    metrics_path = output_dir / "subgroup_metrics.csv"
    intervals_path = output_dir / "subgroup_confidence_intervals.csv"
    membership_path = output_dir / "subgroup_membership.csv"
    metadata_path = output_dir / "metadata.json"
    report_path = output_dir / "Subgroup_and_Fairness_Analysis.md"
    metrics.to_csv(metrics_path, index=False)
    intervals.to_csv(intervals_path, index=False)
    membership.to_csv(membership_path, index=False)
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    report_path.write_text(_render_report(metadata, metrics), encoding="utf-8")
    return SubgroupAnalysisResult(
        study_dir=study_dir,
        output_dir=output_dir,
        metrics_path=metrics_path,
        intervals_path=intervals_path,
        report_path=report_path,
    )
