"""Build a complete feature dictionary without erasing dataset semantics."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from diabetes_pipeline.settings import (
    DEFAULT_OUTPUT_ROOT,
    PROJECT_ROOT,
    load_dataset_registry,
)


DEFAULT_ONTOLOGY_PATH = PROJECT_ROOT / "config" / "feature_ontology.yaml"


@dataclass(frozen=True)
class FeatureOntologyResult:
    output_dir: Path
    dictionary_path: Path
    report_path: Path
    metadata_path: Path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_ontology(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Feature ontology must be a mapping")
    return payload


def build_feature_dictionary(
    ontology_path: Path | str = DEFAULT_ONTOLOGY_PATH,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return one semantic mapping row for every configured model feature."""

    ontology_path = Path(ontology_path)
    ontology = _load_ontology(ontology_path)
    registry = load_dataset_registry()
    endpoint_contracts = dict(ontology["endpoint_contracts"])
    dataset_endpoints: dict[str, str] = {}
    for endpoint, contract in endpoint_contracts.items():
        for dataset_name in contract["datasets"]:
            if dataset_name in dataset_endpoints:
                raise ValueError(f"Dataset {dataset_name} appears in multiple endpoints")
            dataset_endpoints[str(dataset_name)] = str(endpoint)
    if set(dataset_endpoints) != set(registry):
        raise ValueError("Endpoint contracts must cover every configured dataset")

    mapped: dict[tuple[str, str], dict[str, Any]] = {}
    for canonical_feature, definition in ontology["shared_mappings"].items():
        for dataset_name, mapping in definition["mappings"].items():
            key = (str(dataset_name), str(mapping["feature"]))
            if key in mapped:
                raise ValueError(f"Feature mapping is duplicated: {key}")
            if dataset_name not in registry:
                raise ValueError(f"Feature mapping uses unknown dataset: {dataset_name}")
            configured = set(
                registry[dataset_name]["numeric_features"]
                + registry[dataset_name]["categorical_features"]
            )
            if mapping["feature"] not in configured:
                raise ValueError(f"Feature mapping is absent from dataset contract: {key}")
            mapped[key] = {
                "canonical_feature": canonical_feature,
                "domain": definition["domain"],
                **mapping,
            }

    records: list[dict[str, Any]] = []
    for dataset_name, cfg in registry.items():
        endpoint = dataset_endpoints[dataset_name]
        numeric = set(cfg["numeric_features"])
        for feature in cfg["numeric_features"] + cfg["categorical_features"]:
            mapping = mapped.get((dataset_name, feature))
            if mapping is None:
                mapping = {
                    "canonical_feature": f"dataset_specific::{dataset_name}::{feature}",
                    "domain": "dataset_specific",
                    "relation": "dataset_specific",
                    "measurement_scale": (
                        "numeric_as_defined_by_source"
                        if feature in numeric
                        else "categorical_as_defined_by_source"
                    ),
                    "harmonization": "prohibited_without_new_validation",
                }
            records.append(
                {
                    "endpoint": endpoint,
                    "dataset": dataset_name,
                    "dataset_feature": feature,
                    "configured_type": (
                        "numeric" if feature in numeric else "categorical"
                    ),
                    "canonical_feature": mapping["canonical_feature"],
                    "domain": mapping["domain"],
                    "relation": mapping["relation"],
                    "measurement_scale": mapping["measurement_scale"],
                    "harmonization": mapping["harmonization"],
                }
            )
    frame = pd.DataFrame(records).sort_values(
        ["endpoint", "canonical_feature", "dataset", "dataset_feature"]
    ).reset_index(drop=True)
    if frame[["dataset", "dataset_feature"]].duplicated().any():
        raise RuntimeError("Every dataset feature must have exactly one dictionary row")
    return frame, ontology


def _report(frame: pd.DataFrame, ontology: dict[str, Any]) -> str:
    shared = frame[~frame["canonical_feature"].str.startswith("dataset_specific::")]
    lines = [
        "# Master Feature Dictionary",
        "",
        "This dictionary preserves measurement and endpoint semantics. A shared "
        "name does not imply that values can be substituted or probabilities pooled.",
        "",
        "## Endpoint contracts",
        "",
    ]
    for endpoint, contract in ontology["endpoint_contracts"].items():
        lines.extend(
            [
                f"### {endpoint}",
                "",
                f"- Datasets: {', '.join(contract['datasets'])}",
                f"- Comparability: `{contract['comparability']}`",
                f"- Probability pooling: `{contract['probability_pooling']}`",
            ]
        )
        lines.extend(f"- {note}" for note in contract.get("notes", []))
        lines.append("")
    lines.extend(
        [
            "## Shared or related concepts",
            "",
            "| Canonical concept | Dataset | Source feature | Relation | Scale | Harmonization |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in shared.itertuples(index=False):
        lines.append(
            f"| {row.canonical_feature} | {row.dataset} | {row.dataset_feature} | "
            f"{row.relation} | {row.measurement_scale} | {row.harmonization} |"
        )
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"The machine-readable dictionary contains {len(frame)} rows and covers "
            "every configured input feature exactly once.",
            "",
            "| Dataset | Endpoint | Features covered | Dataset-specific features |",
            "|---|---|---:|---:|",
        ]
    )
    summary = (
        frame.assign(
            dataset_specific=frame["canonical_feature"].str.startswith(
                "dataset_specific::"
            )
        )
        .groupby(["dataset", "endpoint"], as_index=False)
        .agg(
            features=("dataset_feature", "size"),
            dataset_specific=("dataset_specific", "sum"),
        )
    )
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.dataset} | {row.endpoint} | {row.features} | "
            f"{row.dataset_specific} |"
        )
    lines.extend(["", "## Routing constraints", ""])
    lines.extend(f"- {rule}" for rule in ontology["routing_constraints"])
    lines.append("")
    return "\n".join(lines)


def write_feature_ontology(
    *,
    ontology_path: Path | str = DEFAULT_ONTOLOGY_PATH,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> FeatureOntologyResult:
    ontology_path = Path(ontology_path)
    frame, ontology = build_feature_dictionary(ontology_path)
    output_dir = output_root / "feature_ontology"
    output_dir.mkdir(parents=True, exist_ok=True)
    dictionary_path = output_dir / "master_feature_dictionary.csv"
    report_path = output_dir / "master_feature_dictionary.md"
    metadata_path = output_dir / "feature_ontology_metadata.json"
    frame.to_csv(dictionary_path, index=False)
    report_path.write_text(_report(frame, ontology), encoding="utf-8")
    metadata_path.write_text(
        json.dumps(
            {
                "version": ontology["version"],
                "ontology_path": str(ontology_path),
                "ontology_sha256": _sha256(ontology_path),
                "dictionary_sha256": _sha256(dictionary_path),
                "dictionary_rows": len(frame),
                "dataset_feature_counts": frame.groupby("dataset").size().to_dict(),
                "endpoint_contracts": ontology["endpoint_contracts"],
                "routing_constraints": ontology["routing_constraints"],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return FeatureOntologyResult(
        output_dir=output_dir,
        dictionary_path=dictionary_path,
        report_path=report_path,
        metadata_path=metadata_path,
    )
