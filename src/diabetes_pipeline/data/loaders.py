"""Raw dataset loaders that defer all learned preprocessing until model folds."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.settings import get_dataset_config


LOGGER = logging.getLogger(__name__)


BRFSS_RAW_COLUMNS = [
    "DIABETE3",
    "_RFHYPE5",
    "TOLDHI2",
    "_CHOLCHK",
    "_BMI5",
    "SMOKE100",
    "CVDSTRK3",
    "CVDINFR4",
    "CVDCRHD4",
    "_TOTINDA",
    "_FRTLT1",
    "_VEGLT1",
    "_RFDRHV5",
    "HLTHPLN1",
    "MEDCOST",
    "GENHLTH",
    "MENTHLTH",
    "PHYSHLTH",
    "DIFFWALK",
    "SEX",
    "_AGEG5YR",
    "EDUCA",
    "INCOME2",
]

PIDD_COLUMNS = [
    "Pregnancies",
    "Glucose",
    "BloodPressure",
    "SkinThickness",
    "Insulin",
    "BMI",
    "DiabetesPedigreeFunction",
    "Age",
    "Outcome",
]


def _aligned_series(values: Any, index: pd.Index, name: str) -> pd.Series:
    return pd.Series(values, index=index, name=name)


def _metadata(cfg: dict[str, Any], raw_rows: int, retained_rows: int) -> dict[str, Any]:
    return {
        "display_name": cfg["display_name"],
        "task": cfg["task"],
        "endpoint": cfg["endpoint"],
        "target_name": cfg["target_name"],
        "target_encoding": dict(cfg.get("target_encoding", {})),
        "source_url": cfg.get("source_url"),
        "raw_path": str(cfg["raw_path"]),
        "raw_rows": int(raw_rows),
        "retained_rows": int(retained_rows),
        "numeric_features": list(cfg["numeric_features"]),
        "categorical_features": list(cfg["categorical_features"]),
        "applicability_notes": list(cfg.get("applicability_notes", [])),
    }


def load_brfss(cfg: dict[str, Any]) -> LoadedDataset:
    raw = pd.read_csv(cfg["raw_path"], usecols=BRFSS_RAW_COLUMNS, low_memory=False)
    raw_rows = len(raw)
    source_index = raw.index.copy()

    target_encoding = cfg["target_encoding"]
    positive_values = list(target_encoding["positive_raw_values"])
    negative_values = list(target_encoding["negative_raw_values"])
    keep = raw["DIABETE3"].isin(positive_values + negative_values)
    raw = raw.loc[keep].copy()
    source_index = source_index[keep]

    X = pd.DataFrame(index=raw.index)
    X["HighBP"] = raw["_RFHYPE5"].map({1: 0, 2: 1})
    X["HighChol"] = raw["TOLDHI2"].map({1: 1, 2: 0})
    X["CholCheck"] = raw["_CHOLCHK"].map({1: 1, 2: 1, 3: 0})
    X["BMI"] = raw["_BMI5"] / 100.0
    X["Smoker"] = raw["SMOKE100"].map({1: 1, 2: 0})
    X["Stroke"] = raw["CVDSTRK3"].map({1: 1, 2: 0})

    heart_attack = raw["CVDINFR4"].map({1: 1, 2: 0})
    coronary_disease = raw["CVDCRHD4"].map({1: 1, 2: 0})
    X["HeartDiseaseorAttack"] = np.where(
        (heart_attack == 1) | (coronary_disease == 1),
        1.0,
        np.where((heart_attack == 0) & (coronary_disease == 0), 0.0, np.nan),
    )

    X["PhysActivity"] = raw["_TOTINDA"].map({1: 1, 2: 0})
    X["Fruits"] = raw["_FRTLT1"].map({1: 1, 2: 0})
    X["Veggies"] = raw["_VEGLT1"].map({1: 1, 2: 0})
    X["HvyAlcoholConsump"] = raw["_RFDRHV5"].map({1: 0, 2: 1})
    X["AnyHealthcare"] = raw["HLTHPLN1"].map({1: 1, 2: 0})
    X["NoDocbcCost"] = raw["MEDCOST"].map({1: 1, 2: 0})
    X["GenHlth"] = raw["GENHLTH"].where(raw["GENHLTH"].isin([1, 2, 3, 4, 5]))
    X["MentHlth"] = raw["MENTHLTH"].replace(88, 0).where(lambda s: s.between(0, 30))
    X["PhysHlth"] = raw["PHYSHLTH"].replace(88, 0).where(lambda s: s.between(0, 30))
    X["DiffWalk"] = raw["DIFFWALK"].map({1: 1, 2: 0})
    X["Sex"] = raw["SEX"].map({1: 1, 2: 0})
    X["Age"] = raw["_AGEG5YR"].where(raw["_AGEG5YR"].between(1, 13))
    X["Education"] = raw["EDUCA"].where(raw["EDUCA"].isin([1, 2, 3, 4, 5, 6]))
    X["Income"] = raw["INCOME2"].where(raw["INCOME2"].isin([1, 2, 3, 4, 5, 6, 7, 8]))
    X = X[cfg["numeric_features"]].astype(float)

    target_map = {value: 1 for value in positive_values}
    target_map.update({value: 0 for value in negative_values})
    y = raw["DIABETE3"].map(target_map).astype(int).rename(cfg["target_name"])
    row_ids = _aligned_series(
        [f"brfss:{int(i)}" for i in source_index], X.index, "row_id"
    )
    return LoadedDataset(
        name=cfg["name"],
        X=X,
        y=y,
        row_ids=row_ids,
        metadata=_metadata(cfg, raw_rows, len(X)),
    )


def load_pidd(cfg: dict[str, Any]) -> LoadedDataset:
    raw = pd.read_csv(cfg["raw_path"], header=None, names=PIDD_COLUMNS)
    raw_rows = len(raw)
    X = raw[cfg["numeric_features"]].copy()
    for column in cfg.get("zero_as_missing", []):
        X[column] = X[column].replace(0, np.nan)
    X = X.astype(float)
    y = raw[cfg["target_name"]].astype(int).rename(cfg["target_name"])
    row_ids = _aligned_series([f"pidd:{i}" for i in raw.index], X.index, "row_id")
    return LoadedDataset(
        name=cfg["name"],
        X=X,
        y=y,
        row_ids=row_ids,
        metadata=_metadata(cfg, raw_rows, len(X)),
    )


def _map_binary_text(series: pd.Series, column: str) -> pd.Series:
    stripped = series.astype(str).str.strip()
    mapped = stripped.map({"Yes": 1, "No": 0, "1": 1, "0": 0})
    if mapped.isna().any():
        invalid = sorted(stripped[mapped.isna()].unique().tolist())
        raise ValueError(f"Unexpected values in Sylhet column '{column}': {invalid}")
    return mapped.astype(float)


def load_sylhet(cfg: dict[str, Any]) -> LoadedDataset:
    raw = pd.read_csv(cfg["raw_path"], low_memory=False)
    raw_rows = len(raw)
    X = pd.DataFrame(index=raw.index)
    X["Age"] = pd.to_numeric(raw["Age"], errors="raise").astype(float)
    X["Gender"] = (
        raw["Gender"].astype(str).str.strip().map({"Male": 1, "Female": 0, "1": 1, "0": 0})
    )
    if X["Gender"].isna().any():
        raise ValueError("Unexpected values in Sylhet Gender column")
    for column in cfg["numeric_features"]:
        if column not in {"Age", "Gender"}:
            X[column] = _map_binary_text(raw[column], column)
    X = X[cfg["numeric_features"]].astype(float)

    raw_target = raw[cfg["target_name"]].astype(str).str.strip()
    y = raw_target.map({"Positive": 1, "Negative": 0, "1": 1, "0": 0})
    if y.isna().any():
        raise ValueError("Unexpected values in Sylhet target")
    y = y.astype(int).rename(cfg["target_name"])

    profile_hash = pd.util.hash_pandas_object(X, index=False).map(lambda value: f"profile:{value:016x}")
    profile_hash.index = X.index
    profile_hash.name = "group_id"
    row_ids = _aligned_series([f"sylhet:{i}" for i in raw.index], X.index, "row_id")
    return LoadedDataset(
        name=cfg["name"],
        X=X,
        y=y,
        row_ids=row_ids,
        groups=profile_hash,
        metadata=_metadata(cfg, raw_rows, len(X)),
    )


def _collapse_icd9(value: Any) -> str:
    if pd.isna(value) or str(value).strip() in {"", "?"}:
        return "Other"
    text = str(value).strip()
    if text.startswith(("E", "V")):
        return "Other"
    try:
        number = float(text)
    except ValueError:
        return "Other"
    if 390 <= number <= 459 or number == 785:
        return "Circulatory"
    if int(number) == 250:
        return "Diabetes"
    if 520 <= number <= 579 or number == 787:
        return "Digestive"
    if 580 <= number <= 629 or number == 788:
        return "Genitourinary"
    if 800 <= number <= 999:
        return "Injury"
    if 710 <= number <= 739:
        return "Musculoskeletal"
    if 140 <= number <= 239:
        return "Neoplasms"
    if 460 <= number <= 519 or number == 786:
        return "Respiratory"
    return "Other"


def load_hospital130(cfg: dict[str, Any]) -> LoadedDataset:
    raw = pd.read_csv(cfg["raw_path"], low_memory=False).replace("?", np.nan)
    raw_rows = len(raw)
    required_identity = {"encounter_id", "patient_nbr", "readmitted"}
    missing_identity = sorted(required_identity - set(raw.columns))
    if missing_identity:
        raise ValueError(f"Hospital130 is missing identity/target columns: {missing_identity}")

    excluded_dispositions = {
        int(value) for value in cfg.get("excluded_discharge_disposition_ids", [])
    }
    if excluded_dispositions:
        raw = raw.loc[
            ~raw["discharge_disposition_id"].isin(excluded_dispositions)
        ].copy()

    row_ids = raw["encounter_id"].astype(str).rename("row_id")
    groups = raw["patient_nbr"].astype(str).rename("group_id")
    y = (raw["readmitted"] == "<30").astype(int).rename(cfg["target_name"])

    working = raw.drop(columns=[c for c in cfg.get("excluded_features", []) if c in raw.columns]).copy()
    age_map = {
        "[0-10)": 0,
        "[10-20)": 1,
        "[20-30)": 2,
        "[30-40)": 3,
        "[40-50)": 4,
        "[50-60)": 5,
        "[60-70)": 6,
        "[70-80)": 7,
        "[80-90)": 8,
        "[90-100)": 9,
    }
    working["age"] = working["age"].map(age_map).astype(float)
    for column in ("diag_1", "diag_2", "diag_3"):
        working[column] = working[column].map(_collapse_icd9)

    feature_order = cfg["numeric_features"] + cfg["categorical_features"]
    missing_features = sorted(set(feature_order) - set(working.columns))
    if missing_features:
        raise ValueError(f"Hospital130 is missing configured features: {missing_features}")
    X = working[feature_order].copy()
    for column in cfg["numeric_features"]:
        X[column] = pd.to_numeric(X[column], errors="coerce")
    for column in cfg["categorical_features"]:
        X[column] = X[column].map(
            lambda value: str(value) if pd.notna(value) else np.nan
        ).astype("object")

    return LoadedDataset(
        name=cfg["name"],
        X=X,
        y=y,
        row_ids=row_ids,
        groups=groups,
        metadata=_metadata(cfg, raw_rows, len(X)),
    )


LOADERS: dict[str, Callable[[dict[str, Any]], LoadedDataset]] = {
    "brfss": load_brfss,
    "pidd": load_pidd,
    "sylhet": load_sylhet,
    "hospital130": load_hospital130,
}


def load_dataset(name: str) -> LoadedDataset:
    cfg = get_dataset_config(name)
    loader_name = cfg["loader"]
    try:
        loader = LOADERS[loader_name]
    except KeyError as exc:
        raise ValueError(f"No loader registered for '{loader_name}'") from exc
    LOGGER.info("Loading %s from %s", name, cfg["raw_path"])
    dataset = loader(cfg)
    LOGGER.info("Loaded %s: %d rows, %d predictors", name, len(dataset.X), dataset.X.shape[1])
    return dataset
