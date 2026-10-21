"""Streaming exact paired bootstrap with independently checked weighted metrics.

The sampling sequence matches evaluation.bootstrap.bootstrap_index_samples.
Weights avoid storing 2000 complete copies of a large cohort in memory.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common import PRIVATE, METRICS, align, numeric_probability
from diabetes_pipeline.evaluation.comparisons import _probability_metrics


def bootstrap_indexes(y, *, n_bootstrap, seed, groups=None):
    y = np.asarray(y, dtype=int)
    if n_bootstrap < 1 or set(np.unique(y)) != {0, 1}:
        raise ValueError("Bootstrap requires both classes and a positive resample count")
    rng = np.random.default_rng(int(seed))
    if groups is None:
        negative, positive = np.flatnonzero(y == 0), np.flatnonzero(y == 1)
        for _ in range(n_bootstrap):
            indexes = np.concatenate((rng.choice(negative, len(negative), replace=True),
                                      rng.choice(positive, len(positive), replace=True)))
            rng.shuffle(indexes)
            yield indexes
    else:
        groups = np.asarray(groups).astype(str)
        if groups.shape != y.shape or np.any(groups == ""):
            raise ValueError("Complete nonempty cluster identities required")
        unique = np.unique(groups)
        rows = {g: np.flatnonzero(groups == g) for g in unique}
        for _ in range(n_bootstrap):
            for _ in range(100):
                sampled = rng.choice(unique, len(unique), replace=True)
                indexes = np.concatenate([rows[g] for g in sampled])
                if len(np.unique(y[indexes])) == 2:
                    yield indexes
                    break
            else:
                raise RuntimeError("Cluster bootstrap could not obtain both classes")


class WeightedMetrics:
    """AUC/AP with exact tie groups and repeated-record bootstrap weights."""
    def __init__(self, y, p):
        self.y = np.asarray(y, float)
        self.p = np.asarray(p, float)
        if not np.isfinite(self.p).all() or ((self.p <= 0) | (self.p >= 1)).any():
            raise ValueError("Bootstrap probabilities must be finite and strictly in (0,1)")
        _, self.rank = np.unique(self.p, return_inverse=True)
        self.bins = int(self.rank.max()) + 1
        self.brier = (self.p - self.y) ** 2
        self.loss = -(self.y * np.log(self.p) + (1 - self.y) * np.log1p(-self.p))

    def __call__(self, weights):
        positive = np.bincount(self.rank, weights=weights * self.y, minlength=self.bins)
        negative = np.bincount(self.rank, weights=weights * (1 - self.y), minlength=self.bins)
        positives, negatives = positive.sum(), negative.sum()
        auc = np.sum(positive * (np.cumsum(negative) - .5 * negative)) / (positives * negatives)
        tp = np.cumsum(positive[::-1])
        population = np.cumsum((positive + negative)[::-1])
        precision = np.divide(tp, population, out=np.zeros_like(tp), where=population > 0)
        ap = np.sum(positive[::-1] * precision) / positives
        return np.array([auc, ap, np.dot(weights, self.brier) / weights.sum(),
                         np.dot(weights, self.loss) / weights.sum()])


def holm(frame, family_columns):
    result = frame.copy()
    result["holm_adjusted_p_value"] = np.nan
    for _, group in result.groupby(family_columns, dropna=False, sort=False):
        ordered = group["paired_bootstrap_p_value"].dropna().sort_values()
        running = 0.
        for rank, (index, value) in enumerate(ordered.items()):
            running = max(running, min(1., value * (len(ordered) - rank)))
            result.loc[index, "holm_adjusted_p_value"] = running
    return result


def paired_bootstrap(frames, contrasts, *, seed, name, n_bootstrap=2000):
    """Return point/CIs and A-minus-B contrasts; persist actual distributions."""
    names = list(frames)
    reference = frames[names[0]].sort_values("row_id").reset_index(drop=True)
    aligned = {key: align(reference, value)[1] for key, value in frames.items()}
    y = reference["target"].to_numpy(int)
    group_values = reference["group_id"].astype(str).to_numpy()
    groups = group_values if np.any(group_values != "") else None
    scorers = {k: WeightedMetrics(y, numeric_probability(v)) for k, v in aligned.items()}
    probabilities = {k: numeric_probability(v) for k, v in aligned.items()}
    distinct_contrasts = [(a, b) for a, b in contrasts
                          if not np.array_equal(probabilities[a], probabilities[b])]
    observed = {k: scorer(np.ones(len(y))) for k, scorer in scorers.items()}
    draws = {k: np.empty((n_bootstrap, len(METRICS))) for k in names}
    for iteration, indexes in enumerate(bootstrap_indexes(y, n_bootstrap=n_bootstrap, seed=seed, groups=groups)):
        weights = np.bincount(indexes, minlength=len(y)).astype(float)
        for key, scorer in scorers.items():
            draws[key][iteration] = scorer(weights)
        # Tail counts use a literal <=0 rule in the historical implementation.
        # Equivalent weighted AUC/AP arithmetic can differ by a machine epsilon
        # exactly at zero. Resolve only those borderline draws using the original
        # sklearn metric arithmetic, without introducing a new tolerance in p.
        ambiguous = set()
        for a, b in distinct_contrasts:
            if np.any(np.abs(draws[a][iteration] - draws[b][iteration]) < 1e-12):
                ambiguous.update([a, b])
        for key in ambiguous:
            exact = _probability_metrics(y[indexes], probabilities[key][indexes])
            draws[key][iteration] = [exact[m] for m in METRICS]
    target = PRIVATE / "bootstrap" / f"{name}.npz"
    target.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(target, **draws, metric_names=np.array(METRICS), seed=seed,
                        row_id=reference["row_id"].to_numpy(str), target=y)
    point_records, contrast_records = [], []
    for key in names:
        for j, metric in enumerate(METRICS):
            low, high = np.quantile(draws[key][:, j], [.025, .975])
            point_records.append({"system": key, "metric": metric, "estimate": observed[key][j],
                                  "ci_lower": low, "ci_upper": high, "seed": seed, "n_bootstrap": n_bootstrap})
    for a, b in contrasts:
        for j, metric in enumerate(METRICS):
            difference = draws[a][:, j] - draws[b][:, j]
            low, high = np.quantile(difference, [.025, .975])
            p = min(1., 2 * min((np.sum(difference <= 0) + 1) / (n_bootstrap + 1),
                                (np.sum(difference >= 0) + 1) / (n_bootstrap + 1)))
            direction = 1 if metric in {"auroc", "average_precision"} else -1
            contrast_records.append({"model_a": a, "model_b": b, "metric": metric,
                                     "observed_difference_a_minus_b": observed[a][j] - observed[b][j],
                                     "ci_lower_a_minus_b": low, "ci_upper_a_minus_b": high,
                                     "positive_improvement_is_better": True,
                                     "observed_improvement_a_over_b": direction * (observed[a][j] - observed[b][j]),
                                     "paired_bootstrap_p_value": p, "seed": seed, "n_bootstrap": n_bootstrap,
                                     "resampling_unit": "cluster" if groups is not None else "individual",
                                     "uncertainty_scope": "conditional_on_fitted_predictions",
                                     "bootstrap_distribution": str(target.relative_to(PRIVATE.parent.parent))})
    return pd.DataFrame(point_records), pd.DataFrame(contrast_records)
