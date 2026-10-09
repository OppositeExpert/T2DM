"""Regression tests exercise the publication sources and prediction summaries."""
import numpy as np
import pandas as pd
import pytest
from diabetes_pipeline.publication.protocol_correction import (
    aggregate_panel_predictions, panel_summary, panel_interval_task,
    publication_panel_source, publication_panel_intervals, verified_benchmark_tables, publication_design,
)


def panel_fixture(dataset="pidd"):
    rows = []
    for repeat in range(5):
        for i, y in enumerate([0, 0, 1, 1]):
            rows.append(dict(system="availability_router", scenario="full", available_feature_count=2,
                             row_id=str(i), group_id=f"profile:{i//2}" if dataset=="sylhet" else "",
                             repeat=repeat, outer_fold=i//2, target=y,
                             probability_raw=[.1,.7,.5,.9][i] + repeat*.005,
                             probability_calibrated=[.1,.7,.5,.9][i] + repeat*.005,
                             selected_model="catboost", calibration_method="identity"))
    return pd.DataFrame(rows)


def meta(dataset):
    return dict(dataset=dataset, task="fixture", endpoint="fixture", experiment_id="fixture",
                evidence_tier="fixture", evaluation_role="fixture", protocol_id="fixture",
                evaluation_strategy="repeated_nested_stratified_group_cv" if dataset=="sylhet" else "repeated_nested_stratified_cv")


def test_panel_metrics_use_averaged_probabilities_not_fold_metric_means(tmp_path):
    f = panel_fixture()
    a = aggregate_panel_predictions(f,"pidd")
    assert len(a)==4 and a.repeat_count.eq(5).all()
    assert np.allclose(a.probability_calibrated,[.11,.71,.51,.91])
    table=panel_summary(a,meta("pidd"))
    assert table.iloc[0].auroc==.75
    corrected=tmp_path/"publication_protocol_correction";corrected.mkdir()
    table.to_csv(corrected/"panel_summary.csv",index=False)
    legacy=tmp_path/"availability_routing";legacy.mkdir()
    f.to_csv(legacy/"system_predictions.csv", index=False)
    pd.DataFrame([dict(auroc=.99)]).to_csv(legacy/"summary_metrics.csv",index=False)
    assert publication_panel_source(tmp_path,meta("pidd")).iloc[0].auroc==.75
    table["auroc"] = .99
    table.to_csv(corrected/"panel_summary.csv", index=False)
    with pytest.raises(ValueError, match="averaged probabilities"):
        publication_panel_source(tmp_path,meta("pidd"))


def test_missing_repeat_or_duplicate_prediction_rejected():
    f=panel_fixture()
    with pytest.raises(ValueError): aggregate_panel_predictions(f.iloc[:-1],"pidd")
    with pytest.raises(ValueError): aggregate_panel_predictions(pd.concat([f,f.iloc[:1]]),"pidd")


def test_sylhet_bootstrap_receives_profiles_and_preserves_records(monkeypatch):
    f=aggregate_panel_predictions(panel_fixture("sylhet"),"sylhet")
    assert len(f)==4 and f.group_id.nunique()==2
    called={}
    def fake(y,p,**kwargs):
        called.update(kwargs)
        return [dict(metric="auroc",estimate=.75,resampling_unit="cluster")]
    monkeypatch.setattr("diabetes_pipeline.publication.protocol_correction.bootstrap_metric_intervals",fake)
    panel_interval_task((meta("sylhet"),("full",2,"availability_router"),f,42,2000))
    assert called["n_bootstrap"]==2000
    assert np.array_equal(called["groups"],f.group_id.to_numpy())
    bad=f.copy();bad["group_id"]=""
    with pytest.raises(ValueError): panel_interval_task((meta("sylhet"),("full",2,"availability_router"),bad,42,2000))


@pytest.mark.parametrize("dataset",["brfss","hospital130"])
def test_fixed_internal_sources_remain_fixed(tmp_path,dataset):
    m=dict(dataset=dataset,runner="locked_internal_validation_holdout")
    pd.DataFrame([dict(model="fixture",auroc=.63)]).to_csv(tmp_path/"test_metrics.csv",index=False)
    pd.DataFrame([dict(resampling_unit="cluster" if dataset=="hospital130" else "individual")]).to_csv(tmp_path/"confidence_intervals.csv",index=False)
    p,i,t=verified_benchmark_tables(tmp_path,m)
    assert publication_design(m)=="fixed" and p.iloc[0].auroc==.63
    assert i.iloc[0].resampling_unit==("cluster" if dataset=="hospital130" else "individual")
    # No fixed stress-panel CI was retained; a benchmark CI must not fill it.
    assert publication_panel_intervals(tmp_path,m).empty


def test_sylhet_publication_interval_source_rejects_individual_bootstrap(tmp_path):
    d=tmp_path/'publication_protocol_correction';d.mkdir()
    f=pd.DataFrame([dict(resampling_unit='individual',n_bootstrap=2000,estimation_scope='participant_mean_across_repeats')])
    f.to_csv(d/'panel_confidence_intervals.csv',index=False)
    with pytest.raises(ValueError,match='resampling'):
        publication_panel_intervals(tmp_path,meta('sylhet'))


def test_benchmark_source_requires_design_and_participant_artifacts(tmp_path):
    with pytest.raises(ValueError): publication_design(dict(dataset="sylhet"))
    # An apparently complete legacy summary is never accepted instead of saved predictions.
    pd.DataFrame([dict(auroc=.99)]).to_csv(tmp_path/"summary_metrics.csv",index=False)
    with pytest.raises(FileNotFoundError): verified_benchmark_tables(tmp_path,meta("sylhet"))


def test_panel_export_does_not_read_runtime_fallback(tmp_path):
    d=tmp_path/"runtime_policy_evaluation";d.mkdir()
    pd.DataFrame([dict(auroc=.99)]).to_csv(d/"policy_metrics.csv",index=False)
    with pytest.raises(FileNotFoundError): publication_panel_source(tmp_path,meta("pidd"))


@pytest.mark.parametrize("dataset",["pidd","sylhet"])
def test_benchmark_selects_verified_participants_and_rejects_wrong_ci(tmp_path,dataset):
    from diabetes_pipeline.evaluation.repeated_cv import aggregate_repeated_predictions
    from diabetes_pipeline.evaluation.metrics import binary_metrics
    f=panel_fixture(dataset).rename(columns={"selected_model":"model"})
    f["dataset"]=dataset; f["experiment_id"]="fixture"
    f.to_csv(tmp_path/"predictions.csv",index=False)
    a=aggregate_repeated_predictions(f)
    a.to_csv(tmp_path/"participant_predictions.csv",index=False)
    rows=[]
    for version in ("raw","calibrated"):
        values=binary_metrics(a.target.to_numpy(),a[f"probability_{version}"].to_numpy())
        for metric in ("auroc","average_precision","brier_score"):
            rows.append(dict(model="catboost",probability_version=version,metric=metric,
                             estimate=values[metric],threshold_policy="fixed_0_5",
                             resampling_unit="cluster" if dataset=="sylhet" else "individual",
                             n_bootstrap=2000,confidence_level=.95,valid_replicates=2000,
                             failed_replicates=0,interval_status="estimated",
                             estimation_scope="participant_mean_across_repeats"))
    ci=pd.DataFrame(rows);ci.to_csv(tmp_path/"participant_confidence_intervals.csv",index=False)
    pd.DataFrame([dict(model="catboost",probability_version="calibrated",threshold_policy="fixed_0_5",auroc=.99)]).to_csv(tmp_path/"summary_metrics.csv",index=False)
    pd.DataFrame(columns=["n_bootstrap","resampling_unit"]).to_csv(tmp_path/"participant_paired_model_comparisons.csv",index=False)
    m=meta(dataset);m["models"]=["catboost"]
    table,intervals,_=verified_benchmark_tables(tmp_path,m)
    assert table.auroc.eq(.75).all() and len(intervals)==6
    ci["resampling_unit"]="individual" if dataset=="sylhet" else "cluster"
    ci.to_csv(tmp_path/"participant_confidence_intervals.csv",index=False)
    with pytest.raises(ValueError,match="resampling"):
        verified_benchmark_tables(tmp_path,m)
