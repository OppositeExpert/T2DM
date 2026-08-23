"""Model construction and Optuna search spaces."""

from __future__ import annotations

from typing import Any

import optuna
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier

from diabetes_pipeline.models.base import ModelAdapter


MODEL_NAMES = (
    "logistic_regression",
    "random_forest",
    "xgboost",
    "lightgbm",
    "catboost",
)


def suggest_parameters(
    trial: optuna.Trial,
    model_name: str,
    positive_class_weight: float,
) -> dict[str, Any]:
    if model_name == "logistic_regression":
        return {
            "C": trial.suggest_float("C", 1e-3, 100.0, log=True),
            "l1_ratio": trial.suggest_categorical("l1_ratio", [0.0, 1.0]),
            "class_weight": trial.suggest_categorical("class_weight", [None, "balanced"]),
        }
    if model_name == "random_forest":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 200, 800, step=100),
            "max_depth": trial.suggest_categorical("max_depth", [None, 6, 10, 16, 24]),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 16),
            "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", 0.5]),
            "class_weight": trial.suggest_categorical(
                "class_weight", [None, "balanced", "balanced_subsample"]
            ),
        }
    if model_name == "xgboost":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 200, 800, step=100),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "min_child_weight": trial.suggest_float("min_child_weight", 1.0, 20.0, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "gamma": trial.suggest_float("gamma", 0.0, 3.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-5, 3.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),
            "use_class_weight": trial.suggest_categorical("use_class_weight", [False, True]),
        }
    if model_name == "lightgbm":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 200, 800, step=100),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 127),
            "max_depth": trial.suggest_categorical("max_depth", [-1, 4, 6, 8, 12]),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 80),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-5, 3.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),
            "class_weight": trial.suggest_categorical("class_weight", [None, "balanced"]),
        }
    if model_name == "catboost":
        return {
            "iterations": trial.suggest_int("iterations", 200, 800, step=100),
            "depth": trial.suggest_int("depth", 3, 9),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 15.0, log=True),
            "random_strength": trial.suggest_float("random_strength", 0.0, 3.0),
            "auto_class_weights": trial.suggest_categorical(
                "auto_class_weights", [None, "Balanced"]
            ),
        }
    raise ValueError(f"Unknown model '{model_name}'. Expected one of {MODEL_NAMES}")


def build_estimator(
    model_name: str,
    params: dict[str, Any] | None = None,
    *,
    seed: int = 42,
    n_jobs: int = 1,
    positive_class_weight: float | None = None,
) -> ModelAdapter:
    params = dict(params or {})
    if model_name == "logistic_regression":
        estimator = LogisticRegression(
            solver="liblinear",
            max_iter=3_000,
            random_state=seed,
            **params,
        )
    elif model_name == "random_forest":
        defaults = {"n_estimators": 300}
        defaults.update(params)
        estimator = RandomForestClassifier(
            random_state=seed,
            n_jobs=n_jobs,
            **defaults,
        )
    elif model_name == "xgboost":
        use_class_weight = bool(params.pop("use_class_weight", False))
        if use_class_weight:
            if positive_class_weight is None:
                raise ValueError("XGBoost class weighting requires a training-fold class ratio")
            params["scale_pos_weight"] = float(positive_class_weight)
        defaults = {"n_estimators": 300, "max_depth": 5, "learning_rate": 0.05}
        defaults.update(params)
        estimator = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            tree_method="hist",
            random_state=seed,
            n_jobs=n_jobs,
            verbosity=0,
            **defaults,
        )
    elif model_name == "lightgbm":
        defaults = {"n_estimators": 300, "learning_rate": 0.05, "verbosity": -1}
        defaults.update(params)
        estimator = LGBMClassifier(
            objective="binary",
            random_state=seed,
            n_jobs=n_jobs,
            deterministic=True,
            force_col_wise=True,
            subsample_freq=1,
            **defaults,
        )
    elif model_name == "catboost":
        if params.get("auto_class_weights") is None:
            params.pop("auto_class_weights", None)
        defaults = {"iterations": 300, "depth": 6, "learning_rate": 0.05}
        defaults.update(params)
        estimator = CatBoostClassifier(
            loss_function="Logloss",
            random_seed=seed,
            thread_count=n_jobs,
            verbose=False,
            allow_writing_files=False,
            **defaults,
        )
    else:
        raise ValueError(f"Unknown model '{model_name}'. Expected one of {MODEL_NAMES}")
    return ModelAdapter(name=model_name, estimator=estimator)
