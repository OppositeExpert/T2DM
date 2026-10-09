"""Batch evaluation of the deployed largest-supported-panel fallback policy."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from diabetes_pipeline.data.loaders import load_dataset
from diabetes_pipeline.evaluation.bootstrap import bootstrap_metric_intervals
from diabetes_pipeline.evaluation.comparisons import paired_bootstrap_model_comparisons
from diabetes_pipeline.evaluation.metrics import binary_metrics
from diabetes_pipeline.settings import get_dataset_config, source_tree_sha256


POLICY_SYSTEMS = (
    "availability_router",
    "robust_single_model",
    "full_panel_champion",
)
POLICY_METRICS = (
    "auroc",
    "average_precision",
    "brier_score",
    "scaled_brier_score",
    "log_loss",
    "calibration_intercept",
    "calibration_slope",
    "observed_expected_ratio",
    "expected_calibration_error",
    "sensitivity",
    "specificity",
    "ppv",
    "npv",
)


@dataclass(frozen=True)
class PolicyEvaluationResult:
    study_dir: Path
    output_dir: Path
    decisions_path: Path
    metrics_path: Path
    comparisons_path: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _supported_scenarios(
    frame: pd.DataFrame, scenarios: dict[str, list[str]]
) -> np.ndarray:
    """Choose panels with the same ordering used by ``route_patient``."""

    chosen = np.full(len(frame), "", dtype=object)
    ordered = sorted(
        scenarios,
        key=lambda name: (len(scenarios[name]), name == "full", name),
        reverse=True,
    )
    unresolved = np.ones(len(frame), dtype=bool)
    for scenario in ordered:
        supported = (
            frame[scenarios[scenario]].notna().all(axis=1).to_numpy() & unresolved
        )
        chosen[supported] = scenario
        unresolved[supported] = False
    return chosen


def _predict_batch(
    router_bundle: dict[str, Any],
    frame: pd.DataFrame,
    scenario: str,
    model_name: str,
) -> tuple[np.ndarray, np.ndarray, str]:
    configured = list(router_bundle["configured_features"])
    ordered = frame.reindex(columns=configured).copy()
    unavailable = sorted(set(configured) - set(router_bundle["scenarios"][scenario]))
    for feature in unavailable:
        ordered[feature] = np.nan
    model_bundle = router_bundle["model_bundles"][model_name]
    calibrator = router_bundle["scenario_calibrators"][model_name][scenario]
    transformed = model_bundle["preprocessor"].transform(ordered)
    raw = np.asarray(model_bundle["model"].predict_proba(transformed), dtype=float)
    calibrated = np.asarray(calibrator.predict(raw), dtype=float)
    method = str(getattr(calibrator, "method", type(calibrator).__name__))
    return raw, calibrated, method


def _validate_router_bundle(
    bundle: dict[str, Any], metadata: dict[str, Any], dataset_cfg: dict[str, Any]
) -> None:
    required = {
        "experiment_id",
        "dataset",
        "task",
        "endpoint",
        "raw_data_sha256",
        "split_manifest_sha256",
        "analysis_configuration_sha256",
        "protocol_id",
        "configured_features",
        "scenarios",
        "selected_models",
        "model_bundles",
        "scenario_calibrators",
        "full_panel_champion",
        "robust_single_model",
    }
    missing = sorted(required - set(bundle))
    if missing:
        raise ValueError(f"Router bundle is missing provenance keys: {missing}")
    expected = {
        "experiment_id": metadata.get("experiment_id"),
        "dataset": metadata.get("dataset"),
        "task": dataset_cfg["task"],
        "endpoint": dataset_cfg["endpoint"],
        "raw_data_sha256": metadata.get("raw_data_sha256"),
        "split_manifest_sha256": metadata.get("split_manifest_sha256"),
        "analysis_configuration_sha256": metadata.get(
            "analysis_configuration_sha256"
        ),
        "protocol_id": metadata.get("protocol_id"),
    }
    mismatched = [key for key, value in expected.items() if bundle.get(key) != value]
    if mismatched:
        raise ValueError(f"Router bundle provenance mismatch: {mismatched}")
    fold_ids = set()
    for model_name, model_bundle in bundle["model_bundles"].items():
        for key in (
            "experiment_id",
            "dataset",
            "task",
            "endpoint",
            "raw_data_sha256",
            "split_manifest_sha256",
            "analysis_configuration_sha256",
        ):
            if model_bundle.get(key) != expected[key]:
                raise ValueError(
                    f"Model bundle {model_name} does not match router {key}"
                )
        fold_identity = (
            model_bundle.get("repeat", 0),
            model_bundle.get("outer_fold", 0),
            model_name,
        )
        if fold_identity in fold_ids:
            raise ValueError("Duplicate model/fold identity in router bundle")
        fold_ids.add(fold_identity)


def _fold_inputs(
    study_dir: Path,
    metadata: dict[str, Any],
) -> list[tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, int, int]]:
    dataset = load_dataset(str(metadata["dataset"]))
    manifest = pd.read_csv(metadata["split_manifest"])
    runner = str(metadata.get("runner", "nested_cv"))
    routing_dir = study_dir / "availability_routing" / "router_bundles"
    records: list[tuple[dict[str, Any], pd.DataFrame, pd.DataFrame, int, int]] = []
    if runner in {"development_locked_holdout", "locked_internal_validation_holdout"}:
        bundle_paths = sorted(routing_dir.glob("*.joblib"))
        if len(bundle_paths) != 1:
            raise ValueError("Holdout routing requires exactly one router bundle")
        role = manifest[manifest["role"] == "test"].sort_values("row_position")
        positions = role["row_position"].to_numpy(dtype=int)
        records.append(
            (
                joblib.load(bundle_paths[0]),
                dataset.X.iloc[positions].reset_index(drop=True),
                role.reset_index(drop=True),
                0,
                0,
            )
        )
        return records
    for path in sorted(routing_dir.glob("router_repeat_*_fold_*.joblib")):
        bundle = joblib.load(path)
        repeat = int(bundle["repeat"])
        fold = int(bundle["outer_fold"])
        role = manifest[
            (manifest["repeat"] == repeat)
            & (manifest["outer_fold"] == fold)
            & (manifest["role"] == "validation")
        ].sort_values("row_position")
        positions = role["row_position"].to_numpy(dtype=int)
        records.append(
            (
                bundle,
                dataset.X.iloc[positions].reset_index(drop=True),
                role.reset_index(drop=True),
                repeat,
                fold,
            )
        )
    if not records:
        raise FileNotFoundError("No nested router bundles were found")
    return records


def _optional_group_values(values: pd.Series) -> np.ndarray | None:
    """Return a NumPy string array only when a non-empty group ID exists."""

    groups = values.fillna("").astype(str).to_numpy(dtype=str)
    return groups if np.any(np.char.str_len(groups) > 0) else None


def evaluate_runtime_policy(study_dir: Path | str) -> PolicyEvaluationResult:
    """Score actual fallback, robust-fixed, and full-panel-fixed policies."""

    study_dir = Path(study_dir).resolve()
    metadata = json.loads(
        (study_dir / "experiment_metadata.json").read_text(encoding="utf-8")
    )
    dataset_name = str(metadata["dataset"])
    dataset_cfg = get_dataset_config(dataset_name)
    profile = dict(metadata["profile"])
    if metadata.get("evidence_tier") not in {
        "full_development",
        "final_internal_validation",
        "final_locked",
    }:
        raise PermissionError(
            "Runtime policy evaluation requires scientific study artifacts"
        )
    decision_frames: list[pd.DataFrame] = []
    for bundle, X, role, repeat, fold in _fold_inputs(study_dir, metadata):
        _validate_router_bundle(bundle, metadata, dataset_cfg)
        scenarios = {
            str(name): list(features)
            for name, features in dict(bundle["scenarios"]).items()
        }
        chosen = _supported_scenarios(X, scenarios)
        for system in POLICY_SYSTEMS:
            system_frame = pd.DataFrame(
                {
                    "experiment_id": metadata["experiment_id"],
                    "protocol_id": metadata.get("protocol_id"),
                    "dataset": dataset_name,
                    "task": dataset_cfg["task"],
                    "endpoint": dataset_cfg["endpoint"],
                    "evaluation_role": metadata.get(
                        "evaluation_role", "outer_validation"
                    ),
                    "evidence_tier": metadata["evidence_tier"],
                    "system": system,
                    "repeat": repeat,
                    "outer_fold": fold,
                    "row_id": role["row_id"].astype(str).to_numpy(),
                    "group_id": role["group_id"].fillna("").astype(str).to_numpy(),
                    "target": role["target"].to_numpy(dtype=int),
                    "status": np.where(chosen == "", "abstain", "predicted"),
                    "abstention_reason": np.where(
                        chosen == "", "no_supported_feature_panel", ""
                    ),
                    "scenario": chosen,
                    "model": "",
                    "calibration_method": "",
                    "probability_raw": np.nan,
                    "probability_calibrated": np.nan,
                    "threshold_policy": str(
                        bundle.get("threshold_policy", "fixed_0_5")
                    ),
                    "threshold": float(bundle.get("threshold", 0.5)),
                    "prediction": pd.array([pd.NA] * len(X), dtype="Int64"),
                    "used_features": "[]",
                    "ignored_features": "[]",
                }
            )
            for scenario in sorted(set(chosen) - {""}):
                mask = chosen == scenario
                model_name = (
                    str(bundle["selected_models"][scenario])
                    if system == "availability_router"
                    else str(bundle[system])
                )
                raw, calibrated, method = _predict_batch(
                    bundle, X.loc[mask], scenario, model_name
                )
                threshold = float(bundle.get("threshold", 0.5))
                system_frame.loc[mask, "model"] = model_name
                system_frame.loc[mask, "calibration_method"] = method
                system_frame.loc[mask, "probability_raw"] = raw
                system_frame.loc[mask, "probability_calibrated"] = calibrated
                system_frame.loc[mask, "prediction"] = (
                    calibrated >= threshold
                ).astype(int)
                used = list(scenarios[scenario])
                ignored = sorted(set(bundle["configured_features"]) - set(used))
                system_frame.loc[mask, "used_features"] = json.dumps(used)
                system_frame.loc[mask, "ignored_features"] = json.dumps(ignored)
            decision_frames.append(system_frame)
    decisions = pd.concat(decision_frames, ignore_index=True)

    stability = decisions.groupby(["system", "row_id"], sort=False).agg(
        targets=("target", "nunique"),
        groups=("group_id", "nunique"),
        statuses=("status", "nunique"),
        scenarios=("scenario", "nunique"),
    )
    if (stability != 1).any().any():
        raise RuntimeError(
            "Runtime policy identity changed across repeated evaluations"
        )
    aggregated = (
        decisions.groupby(["system", "row_id"], as_index=False, sort=True)
        .agg(
            experiment_id=("experiment_id", "first"),
            protocol_id=("protocol_id", "first"),
            dataset=("dataset", "first"),
            task=("task", "first"),
            endpoint=("endpoint", "first"),
            evaluation_role=("evaluation_role", "first"),
            evidence_tier=("evidence_tier", "first"),
            group_id=("group_id", "first"),
            target=("target", "first"),
            status=("status", "first"),
            abstention_reason=("abstention_reason", "first"),
            scenario=("scenario", "first"),
            selected_models=(
                "model",
                lambda values: "|".join(sorted(set(values) - {""})),
            ),
            calibration_methods=(
                "calibration_method",
                lambda values: "|".join(sorted(set(values) - {""})),
            ),
            probability_raw=("probability_raw", "mean"),
            probability_calibrated=("probability_calibrated", "mean"),
            threshold_policy=("threshold_policy", "first"),
            threshold=("threshold", "mean"),
            repeat_count=("repeat", "nunique"),
            used_features=("used_features", "first"),
            ignored_features=("ignored_features", "first"),
        )
    )
    aggregated["prediction"] = pd.array(
        np.where(
            aggregated["status"].eq("predicted"),
            aggregated["probability_calibrated"] >= aggregated["threshold"],
            np.nan,
        ),
        dtype="Int64",
    )

    reference = aggregated[aggregated["system"] == POLICY_SYSTEMS[0]]
    total_n = len(reference)
    total_events = int(reference["target"].sum())
    metric_records: list[dict[str, Any]] = []
    interval_records: list[dict[str, Any]] = []
    for index, (system, frame) in enumerate(
        aggregated.groupby("system", sort=True)
    ):
        accepted = frame[frame["status"] == "predicted"].reset_index(drop=True)
        accepted_events = int(accepted["target"].sum())
        base = {
            "experiment_id": metadata["experiment_id"],
            "protocol_id": metadata.get("protocol_id"),
            "dataset": dataset_name,
            "task": dataset_cfg["task"],
            "endpoint": dataset_cfg["endpoint"],
            "evaluation_role": metadata.get("evaluation_role"),
            "evidence_tier": metadata["evidence_tier"],
            "system": system,
            "total_n": total_n,
            "accepted_n": len(accepted),
            "abstained_n": total_n - len(accepted),
            "coverage": len(accepted) / total_n,
            "total_positive_events": total_events,
            "accepted_positive_events": accepted_events,
            "positive_event_coverage": (
                accepted_events / total_events if total_events else np.nan
            ),
        }
        if accepted["target"].nunique() < 2:
            metric_records.append({**base, "status": "suppressed_single_class"})
            continue
        estimates = binary_metrics(
            accepted["target"].to_numpy(dtype=int),
            accepted["probability_calibrated"].to_numpy(dtype=float),
            threshold=accepted["threshold"].to_numpy(dtype=float),
        )
        metric_records.append({**base, "status": "estimated", **estimates})
        groups = _optional_group_values(accepted["group_id"])
        intervals = bootstrap_metric_intervals(
            accepted["target"].to_numpy(dtype=int),
            accepted["probability_calibrated"].to_numpy(dtype=float),
            threshold=0.5,
            n_bootstrap=int(profile["n_bootstrap"]),
            seed=int(profile["seed"]) + 1_600_000 + index,
            metric_names=POLICY_METRICS,
            groups=groups,
        )
        interval_records.extend({**base, **row} for row in intervals)
    metrics = pd.DataFrame(metric_records)
    intervals = pd.DataFrame(interval_records)

    predicted = aggregated[aggregated["status"] == "predicted"].copy()
    first = (
        predicted[predicted["system"] == POLICY_SYSTEMS[0]]
        .sort_values("row_id")
        .reset_index(drop=True)
    )
    comparison_groups = _optional_group_values(first["group_id"])
    comparisons = paired_bootstrap_model_comparisons(
        predicted.rename(columns={"system": "model"})[
            ["model", "row_id", "target", "probability_calibrated"]
        ],
        n_bootstrap=int(profile["n_bootstrap"]),
        seed=int(profile["seed"]) + 1_700_000,
        groups=comparison_groups,
    )
    comparisons.insert(0, "dataset", dataset_name)
    comparisons.insert(0, "experiment_id", metadata["experiment_id"])

    output_dir = study_dir / "runtime_policy_evaluation"
    output_dir.mkdir(parents=True, exist_ok=True)
    decisions_path = output_dir / "policy_decisions.csv"
    aggregate_path = output_dir / "participant_policy_predictions.csv"
    metrics_path = output_dir / "policy_metrics.csv"
    intervals_path = output_dir / "policy_confidence_intervals.csv"
    comparisons_path = output_dir / "policy_paired_comparisons.csv"
    decisions.to_csv(decisions_path, index=False)
    aggregated.to_csv(aggregate_path, index=False)
    metrics.to_csv(metrics_path, index=False)
    intervals.to_csv(intervals_path, index=False)
    comparisons.to_csv(comparisons_path, index=False)
    artifact_paths = [
        decisions_path,
        aggregate_path,
        metrics_path,
        intervals_path,
        comparisons_path,
    ]
    (output_dir / "metadata.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "experiment_id": metadata["experiment_id"],
                "protocol_id": metadata.get("protocol_id"),
                "dataset": dataset_name,
                "task": dataset_cfg["task"],
                "endpoint": dataset_cfg["endpoint"],
                "evidence_tier": metadata["evidence_tier"],
                "policy": "largest_fully_supported_prespecified_panel",
                "systems": list(POLICY_SYSTEMS),
                "abstention": "no_supported_feature_panel",
                "probability_aggregation": "participant_mean_across_repeats",
                "bootstrap_resamples": int(profile["n_bootstrap"]),
                "source_tree_sha256": source_tree_sha256(),
                "artifacts": {
                    str(path.relative_to(study_dir)): _sha256(path)
                    for path in artifact_paths
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return PolicyEvaluationResult(
        study_dir=study_dir,
        output_dir=output_dir,
        decisions_path=decisions_path,
        metrics_path=metrics_path,
        comparisons_path=comparisons_path,
    )
