#!/usr/bin/env python3
"""Reload every holdout bundle and reproduce its stored test probabilities."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from diabetes_pipeline.data.loaders import load_dataset


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-dir", type=Path, required=True)
    parser.add_argument("--atol", type=float, default=1e-12)
    args = parser.parse_args()

    study = args.study_dir.resolve()
    metadata = json.loads((study / "experiment_metadata.json").read_text())
    predictions = pd.read_csv(study / "test_predictions.csv")
    dataset = load_dataset(str(metadata["dataset"]))
    row_positions = {
        str(row_id): position
        for position, row_id in enumerate(dataset.row_ids.astype(str))
    }
    reports: list[dict[str, object]] = []
    for bundle_path in sorted((study / "models").glob("*.joblib")):
        bundle = joblib.load(bundle_path)
        model_name = str(bundle["model_name"])
        expected = predictions[predictions["model"] == model_name].reset_index(drop=True)
        if len(expected) != int(metadata["evaluated_test_rows"]):
            raise RuntimeError(f"Unexpected prediction row count for {model_name}")
        try:
            positions = [row_positions[str(value)] for value in expected["row_id"]]
        except KeyError as exc:
            raise RuntimeError(f"Stored row identity is absent from raw data: {exc}") from exc
        X = dataset.X.iloc[positions].reset_index(drop=True)
        transformed = bundle["preprocessor"].transform(X)
        raw = np.asarray(bundle["model"].predict_proba(transformed), dtype=float)
        calibrated = np.asarray(bundle["calibrator"].predict(raw), dtype=float)
        raw_error = float(np.max(np.abs(raw - expected["probability_raw"].to_numpy())))
        calibrated_error = float(
            np.max(
                np.abs(
                    calibrated
                    - expected["probability_calibrated"].to_numpy()
                )
            )
        )
        if raw_error > args.atol or calibrated_error > args.atol:
            raise RuntimeError(
                f"Probability mismatch for {model_name}: raw={raw_error}, calibrated={calibrated_error}"
            )
        for key in (
            "experiment_id",
            "dataset",
            "dataset_configuration_sha256",
            "raw_data_sha256",
            "split_manifest_sha256",
        ):
            if key in bundle and str(bundle[key]) != str(metadata.get(key)):
                raise RuntimeError(f"Bundle metadata mismatch for {model_name}: {key}")
        reports.append(
            {
                "model": model_name,
                "bundle": str(bundle_path),
                "bundle_sha256": sha256(bundle_path),
                "rows_reproduced": len(expected),
                "maximum_raw_probability_error": raw_error,
                "maximum_calibrated_probability_error": calibrated_error,
                "passed": True,
            }
        )
    if not reports:
        raise FileNotFoundError(f"No model bundles found under {study / 'models'}")
    print(
        json.dumps(
            {
                "study": str(study),
                "dataset": metadata["dataset"],
                "models_verified": len(reports),
                "atol": args.atol,
                "passed": True,
                "bundles": reports,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
