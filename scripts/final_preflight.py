#!/usr/bin/env python3
"""Read-only final-run preflight; never changes authorization or accesses labels."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from diabetes_pipeline.settings import get_dataset_config, load_experiment_profile
from diabetes_pipeline.splitting.concealment import (
    assert_final_execution_authorized,
    final_analysis_configuration_sha256,
)


MODEL_CHOICES = (
    "logistic_regression",
    "random_forest",
    "xgboost",
    "lightgbm",
    "catboost",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset", required=True, choices=("pidd", "sylhet", "brfss", "hospital130")
    )
    parser.add_argument(
        "--models", nargs="+", choices=MODEL_CHOICES, default=list(MODEL_CHOICES)
    )
    args = parser.parse_args()

    dataset_config = get_dataset_config(args.dataset)
    profile = load_experiment_profile("final")
    raw_hash = sha256(Path(dataset_config["raw_path"]))
    analysis_hash = final_analysis_configuration_sha256(
        dataset_name=args.dataset,
        dataset_config=dataset_config,
        profile=profile,
        models=args.models,
    )
    result: dict[str, object] = {
        "dataset": args.dataset,
        "profile": "final",
        "models": args.models,
        "raw_data_sha256": raw_hash,
        "analysis_configuration_sha256": analysis_hash,
        "authorized": False,
        "outcome_accessed": False,
    }
    try:
        manifest = assert_final_execution_authorized(
            profile_name="final",
            profile=profile,
            dataset_name=args.dataset,
            raw_data_sha256=raw_hash,
            analysis_configuration_sha256=analysis_hash,
            requires_concealed_holdout=str(
                dataset_config["evaluation_strategy"]
            ).endswith("holdout_cv"),
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        result["reason"] = str(exc)
        print(json.dumps(result, indent=2, sort_keys=True))
        raise SystemExit(2) from None
    result["authorized"] = True
    result["concealed_manifest"] = str(manifest) if manifest is not None else None
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
