"""Construct unfitted preprocessing graphs from dataset contracts."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


TREE_MODELS = {"random_forest", "xgboost", "lightgbm", "catboost"}
SUPPORTED_MODELS = TREE_MODELS | {"logistic_regression"}


def build_preprocessor(
    dataset_cfg: dict[str, Any],
    model_name: str,
    *,
    add_numeric_missing_indicators: bool = True,
) -> ColumnTransformer:
    """Return an unfitted transformer; callers must fit it on training rows only."""
    if model_name not in SUPPORTED_MODELS:
        raise ValueError(f"Unsupported model '{model_name}'. Expected one of {sorted(SUPPORTED_MODELS)}")

    numeric_steps: list[tuple[str, Any]] = [
        (
            "imputer",
            SimpleImputer(
                strategy="median",
                add_indicator=add_numeric_missing_indicators,
                keep_empty_features=True,
            ),
        )
    ]
    if model_name == "logistic_regression":
        numeric_steps.append(("scaler", StandardScaler()))

    transformers: list[tuple[str, Any, list[str]]] = []
    numeric_features = list(dataset_cfg["numeric_features"])
    categorical_features = list(dataset_cfg["categorical_features"])
    if numeric_features:
        transformers.append(("numeric", Pipeline(numeric_steps), numeric_features))
    if categorical_features:
        categorical_pipeline = Pipeline(
            [
                (
                    "imputer",
                    SimpleImputer(
                        strategy="constant",
                        fill_value="__MISSING__",
                        keep_empty_features=True,
                    ),
                ),
                (
                    "encoder",
                    OneHotEncoder(
                        handle_unknown="ignore",
                        sparse_output=True,
                        dtype=np.float32,
                    ),
                ),
            ]
        )
        transformers.append(("categorical", categorical_pipeline, categorical_features))

    if not transformers:
        raise ValueError("Dataset contract contains no features")
    return ColumnTransformer(
        transformers=transformers,
        remainder="drop",
        sparse_threshold=0.3,
        verbose_feature_names_out=False,
    )


def transformed_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    if not hasattr(preprocessor, "transformers_"):
        raise ValueError("Preprocessor must be fitted before requesting feature names")
    return preprocessor.get_feature_names_out().tolist()

