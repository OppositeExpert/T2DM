"""Independent numerical and identity checks for isolated journal analyses."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss, log_loss

from diabetes_pipeline.evaluation.bootstrap import bootstrap_index_samples
from diabetes_pipeline.journal_revision.common import aggregate, align
from diabetes_pipeline.journal_revision.statistics import WeightedMetrics, bootstrap_indexes, holm


@pytest.mark.parametrize("grouped", [False, True])
def test_streaming_samples_match_original_group_bootstrap(grouped):
    y = np.array([0, 1, 1, 0, 0, 1, 1, 0])
    groups = np.array(["a", "a", "b", "c", "c", "d", "e", "e"]) if grouped else None
    expected = bootstrap_index_samples(y, n_bootstrap=30, seed=41, groups=groups)
    actual = list(bootstrap_indexes(y, n_bootstrap=30, seed=41, groups=groups))
    for a, b in zip(actual, expected):
        np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("seed", [0, 42, 900])
def test_weighted_metrics_match_sklearn_with_ties_and_mixed_labels(seed):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, 80)
    p = rng.choice([.000001, .1, .2, .5, .8, .999999], size=80)
    scorer = WeightedMetrics(y, p)
    for _ in range(10):
        indexes = rng.choice(len(y), len(y), replace=True)
        weights = np.bincount(indexes, minlength=len(y))
        expected = [roc_auc_score(y[indexes], p[indexes]), average_precision_score(y[indexes], p[indexes]),
                    brier_score_loss(y[indexes], p[indexes]), log_loss(y[indexes], p[indexes], labels=[0, 1])]
        np.testing.assert_allclose(scorer(weights), expected, rtol=0, atol=1e-14)


def test_primary_average_probability_differs_from_repeat_mean_metric():
    frame = pd.DataFrame({"row_id": ["a", "b", "a", "b"], "group_id": [""] * 4,
                          "repeat": [0, 0, 1, 1], "target": [0, 1, 0, 1],
                          "model": ["x"] * 4, "probability_calibrated": [.1, .9, .9, .1]})
    result = aggregate(frame, ["model"], 2)
    np.testing.assert_allclose(result.probability_calibrated, [.5, .5])
    assert brier_score_loss(result.target, result.probability_calibrated) == .25
    repeat_mean_brier = np.mean([brier_score_loss(v.target, v.probability_calibrated) for _, v in frame.groupby("repeat")])
    assert repeat_mean_brier > .25


@pytest.mark.parametrize("problem", ["duplicate", "missing", "label", "group"])
def test_repeated_identity_corruption_fails(problem):
    frame = pd.DataFrame({"row_id": ["a", "b", "a", "b"], "group_id": ["g1", "g2", "g1", "g2"],
                          "repeat": [0, 0, 1, 1], "target": [0, 1, 0, 1], "model": ["x"] * 4,
                          "probability_calibrated": [.2, .8, .3, .7]})
    if problem == "duplicate":
        frame = pd.concat([frame, frame.iloc[[0]]])
    elif problem == "missing":
        frame = frame.iloc[:-1]
    elif problem == "label":
        frame.loc[2, "target"] = 1
    else:
        frame.loc[2, "group_id"] = "g3"
    with pytest.raises(ValueError):
        aggregate(frame, ["model"], 2)


def test_pairing_rejects_mismatched_population_and_group():
    a = pd.DataFrame({"row_id": ["b", "a"], "target": [1, 0], "group_id": ["g2", "g1"]})
    b = a.copy()
    align(a, b.iloc[::-1])
    b.loc[0, "group_id"] = "wrong"
    with pytest.raises(ValueError, match="group_id"):
        align(a, b)


def test_holm_uses_declared_metric_family_and_monotonic_stepdown():
    frame = pd.DataFrame({"dataset": ["d"] * 5, "metric": ["auc"] * 3 + ["brier"] * 2,
                          "paired_bootstrap_p_value": [.03, .01, .04, .02, .8]})
    result = holm(frame, ["dataset", "metric"])
    np.testing.assert_allclose(result.holm_adjusted_p_value, [.06, .03, .06, .04, .8])


def test_reduced_panel_predictions_do_not_depend_on_evaluation_labels_or_excluded_features(tmp_path, monkeypatch):
    """A real fitted pipeline must ignore both evaluation outcomes and masked inputs."""
    from types import SimpleNamespace
    import joblib
    from diabetes_pipeline.calibration.calibrators import IdentityCalibrator
    from diabetes_pipeline.journal_revision import experiments
    from diabetes_pipeline.models.registry import build_estimator
    from diabetes_pipeline.preprocessing.builders import build_preprocessor
    from diabetes_pipeline.settings import get_dataset_config

    cfg = get_dataset_config("pidd")
    features = cfg["numeric_features"]
    panel = "no_insulin_or_skinfold"
    selected = [f for f in features if f not in {"Insulin", "SkinThickness"}]
    rng = np.random.default_rng(42)
    X = pd.DataFrame(rng.normal(size=(120, len(features))), columns=features)
    y = np.tile([0, 1], 60)
    prep = build_preprocessor(cfg, "random_forest")
    fitted = build_estimator("random_forest", {"n_estimators": 8, "max_depth": 3}, seed=42, n_jobs=1)
    fitted.fit(prep.fit_transform(X.iloc[:100]), y[:100])
    base = {"preprocessor": prep, "model": fitted, "best_params": {"n_estimators": 8, "max_depth": 3}}
    bundle = {"configured_features": features, "scenarios": {panel: selected},
              "selected_models": {panel: "random_forest"}, "model_bundles": {"random_forest": base},
              "scenario_calibrators": {"random_forest": {panel: IdentityCalibrator()}}}
    router_path = tmp_path / "router.joblib"
    joblib.dump(bundle, router_path)
    report = tmp_path / "report"
    report.mkdir()
    (report / "experiment_plan.json").write_text('{}')
    monkeypatch.setattr(experiments, "REPORT", report)
    monkeypatch.setattr(experiments, "git_commit", lambda: "test-source")
    def role(indexes):
        return pd.DataFrame({"row_id": [f"pidd:{i}" for i in indexes], "group_id": "", "target": y[indexes], "row_position": indexes})
    context = {"dataset": "pidd", "repeat": 0, "fold": 0, "bundle": bundle, "bundle_path": router_path,
               "train": role(np.arange(100)), "evaluation": role(np.arange(100, 120)), "loaded": SimpleNamespace(X=X),
               "metadata": {"split_manifest_sha256": "test-split"}, "cfg": cfg, "holdout": False,
               "groups": None, "predefined_splits": None}
    monkeypatch.setattr(experiments, "PRIVATE", tmp_path / "first")
    experiments.fit_task(context, panel)
    first = pd.read_csv(experiments.task_path(context, panel) / "predictions.csv.gz")
    changed = X.copy()
    changed.loc[100:, ["Insulin", "SkinThickness"]] = 1000000
    context["loaded"] = SimpleNamespace(X=changed)
    context["evaluation"]["target"] = 1 - context["evaluation"]["target"]
    monkeypatch.setattr(experiments, "PRIVATE", tmp_path / "second")
    experiments.fit_task(context, panel)
    second = pd.read_csv(experiments.task_path(context, panel) / "predictions.csv.gz")
    # Parallel RF tree accumulation can vary by one machine epsilon even with
    # identical seeds; this bound is far below any model/evaluation difference.
    np.testing.assert_allclose(first.probability_calibrated, second.probability_calibrated, rtol=0, atol=1e-14)
    assert not np.array_equal(first.target, second.target)
    new_model = joblib.load(experiments.task_path(context, panel) / "bundle.joblib")
    assert set(new_model["preprocessor"].feature_names_in_) == set(selected)


def test_blank_abstention_probabilities_keep_string_record_id(tmp_path):
    from diabetes_pipeline.journal_revision.common import read_csv
    p = tmp_path / "probabilities.csv"
    p.write_text('row_id,group_id,probability_calibrated\n100,,0.2\n2,,\n')
    frame = read_csv(p)
    assert frame.row_id.tolist() == ["100", "2"]
    assert frame.group_id.tolist() == ["", ""]
    assert np.isnan(frame.probability_calibrated.iloc[1])


def test_paired_bootstrap_intervals_and_tail_tests_match_reference(tmp_path, monkeypatch):
    from diabetes_pipeline.journal_revision import statistics
    from diabetes_pipeline.evaluation.comparisons import paired_bootstrap_model_comparisons
    rng = np.random.default_rng(13)
    y = np.tile([0, 1], 30)
    p = rng.choice([.1, .3, .6, .9], size=len(y))
    a = pd.DataFrame({"row_id": [f"r:{i:03d}" for i in range(len(y))], "group_id": "", "target": y,
                      "probability_calibrated": p, "model": "a"})
    b = a.copy()
    # Strictly monotone transform: tied rank metrics have exact zero effects,
    # exercising the reference tail arithmetic rather than just nonzero draws.
    b["probability_calibrated"] = .05 + .9 * p
    b["model"] = "b"
    expected = paired_bootstrap_model_comparisons(pd.concat([a, b]), n_bootstrap=100, seed=42)
    monkeypatch.setattr(statistics, "PRIVATE", tmp_path)
    _, actual = statistics.paired_bootstrap({"a": a, "b": b}, [("a", "b")], seed=42, name="comparison", n_bootstrap=100)
    for _, row in actual.iterrows():
        reference = expected[expected.metric == row.metric].iloc[0]
        for key in ["observed_difference_a_minus_b", "ci_lower_a_minus_b", "ci_upper_a_minus_b", "paired_bootstrap_p_value"]:
            assert row[key] == pytest.approx(reference[key], abs=1e-14)
