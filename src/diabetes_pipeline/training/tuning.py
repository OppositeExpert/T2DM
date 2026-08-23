"""Leakage-free Optuna tuning and inner out-of-fold prediction generation."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from typing import Any, Iterator

import numpy as np
import optuna
import pandas as pd
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold

from diabetes_pipeline.models.registry import build_estimator, suggest_parameters
from diabetes_pipeline.preprocessing.builders import build_preprocessor


optuna.logging.set_verbosity(optuna.logging.WARNING)


@dataclass(frozen=True)
class TuningResult:
    best_params: dict[str, Any]
    best_score: float
    trials: pd.DataFrame


def positive_class_weight(y: np.ndarray) -> float:
    positives = int(np.sum(y == 1))
    negatives = int(np.sum(y == 0))
    return float(negatives / positives) if positives else 1.0


def inner_splits(
    y: np.ndarray,
    *,
    n_splits: int,
    seed: int,
    groups: np.ndarray | None = None,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    positions = np.arange(len(y))
    if groups is None:
        splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        yield from splitter.split(positions, y)
    else:
        splitter = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
        yield from splitter.split(positions, y, groups)


def tune_model(
    X: pd.DataFrame,
    y: np.ndarray,
    dataset_cfg: dict[str, Any],
    model_name: str,
    *,
    n_trials: int,
    n_splits: int,
    seed: int,
    groups: np.ndarray | None = None,
    predefined_splits: Sequence[tuple[np.ndarray, np.ndarray]] | None = None,
    n_jobs: int = 1,
) -> TuningResult:
    resolved_splits = (
        [
            (np.asarray(training, dtype=int), np.asarray(validation, dtype=int))
            for training, validation in predefined_splits
        ]
        if predefined_splits is not None
        else list(inner_splits(y, n_splits=n_splits, seed=seed, groups=groups))
    )
    if len(resolved_splits) < 2:
        raise ValueError("Tuning requires at least two development folds")

    def objective(trial: optuna.Trial) -> float:
        suggested = suggest_parameters(trial, model_name, positive_class_weight(y))
        scores: list[float] = []
        for fold, (training, validation) in enumerate(resolved_splits):
            preprocessor = build_preprocessor(dataset_cfg, model_name)
            X_training = preprocessor.fit_transform(X.iloc[training])
            X_validation = preprocessor.transform(X.iloc[validation])
            y_training = y[training]
            model = build_estimator(
                model_name,
                suggested,
                seed=seed + fold,
                n_jobs=n_jobs,
                positive_class_weight=positive_class_weight(y_training),
            )
            model.fit(X_training, y_training)
            probability = model.predict_proba(X_validation)
            scores.append(float(average_precision_score(y[validation], probability)))
            trial.report(float(np.mean(scores)), step=fold)
            if trial.should_prune():
                raise optuna.TrialPruned()
        trial.set_user_attr("fold_scores", scores)
        trial.set_user_attr("score_std", float(np.std(scores, ddof=1)) if len(scores) > 1 else 0.0)
        return float(np.mean(scores))

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=seed),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=max(2, n_trials // 5)),
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    return TuningResult(
        best_params=dict(study.best_params),
        best_score=float(study.best_value),
        trials=study.trials_dataframe(),
    )


def cross_fitted_probabilities(
    X: pd.DataFrame,
    y: np.ndarray,
    dataset_cfg: dict[str, Any],
    model_name: str,
    params: dict[str, Any],
    *,
    n_splits: int,
    seed: int,
    groups: np.ndarray | None = None,
    predefined_splits: Sequence[tuple[np.ndarray, np.ndarray]] | None = None,
    n_jobs: int = 1,
) -> np.ndarray:
    probabilities = np.full(len(y), np.nan, dtype=float)
    resolved_splits = (
        [
            (np.asarray(training, dtype=int), np.asarray(validation, dtype=int))
            for training, validation in predefined_splits
        ]
        if predefined_splits is not None
        else list(inner_splits(y, n_splits=n_splits, seed=seed, groups=groups))
    )
    for fold, (training, validation) in enumerate(resolved_splits):
        preprocessor = build_preprocessor(dataset_cfg, model_name)
        X_training = preprocessor.fit_transform(X.iloc[training])
        X_validation = preprocessor.transform(X.iloc[validation])
        y_training = y[training]
        model = build_estimator(
            model_name,
            params,
            seed=seed + 10_000 + fold,
            n_jobs=n_jobs,
            positive_class_weight=positive_class_weight(y_training),
        )
        model.fit(X_training, y_training)
        probabilities[validation] = model.predict_proba(X_validation)
    if np.isnan(probabilities).any():
        raise RuntimeError("Cross-fitting did not produce a probability for every training row")
    return probabilities


def cross_fitted_probabilities_by_scenario(
    X: pd.DataFrame,
    y: np.ndarray,
    dataset_cfg: dict[str, Any],
    model_name: str,
    params: dict[str, Any],
    scenarios: dict[str, list[str]],
    *,
    n_splits: int,
    seed: int,
    groups: np.ndarray | None = None,
    predefined_splits: Sequence[tuple[np.ndarray, np.ndarray]] | None = None,
    n_jobs: int = 1,
) -> dict[str, np.ndarray]:
    """Predict masked validation panels while always fitting on full training data."""

    configured_features = set(
        dataset_cfg["numeric_features"] + dataset_cfg["categorical_features"]
    )
    if not scenarios:
        raise ValueError("At least one availability scenario is required")
    for scenario_name, available_features in scenarios.items():
        unknown = sorted(set(available_features) - configured_features)
        if unknown:
            raise ValueError(
                f"Scenario '{scenario_name}' contains unknown features: {unknown}"
            )
        if not available_features:
            raise ValueError(f"Scenario '{scenario_name}' contains no features")

    probabilities = {
        scenario_name: np.full(len(y), np.nan, dtype=float)
        for scenario_name in scenarios
    }
    resolved_splits = (
        [
            (np.asarray(training, dtype=int), np.asarray(validation, dtype=int))
            for training, validation in predefined_splits
        ]
        if predefined_splits is not None
        else list(inner_splits(y, n_splits=n_splits, seed=seed, groups=groups))
    )
    for fold, (training, validation) in enumerate(resolved_splits):
        preprocessor = build_preprocessor(dataset_cfg, model_name)
        X_training = preprocessor.fit_transform(X.iloc[training])
        y_training = y[training]
        model = build_estimator(
            model_name,
            params,
            seed=seed + 30_000 + fold,
            n_jobs=n_jobs,
            positive_class_weight=positive_class_weight(y_training),
        )
        model.fit(X_training, y_training)
        validation_frame = X.iloc[validation]
        for scenario_name, available_features in scenarios.items():
            masked_validation = validation_frame.copy()
            unavailable = sorted(configured_features - set(available_features))
            for feature in unavailable:
                # Column-wise assignment safely promotes integer and categorical
                # source columns to a missing-capable dtype under pandas 3.x.
                masked_validation[feature] = np.nan
            transformed_validation = preprocessor.transform(masked_validation)
            probabilities[scenario_name][validation] = model.predict_proba(
                transformed_validation
            )
    for scenario_name, scenario_probability in probabilities.items():
        if np.isnan(scenario_probability).any():
            raise RuntimeError(
                f"Cross-fitting did not complete scenario '{scenario_name}'"
            )
    return probabilities
