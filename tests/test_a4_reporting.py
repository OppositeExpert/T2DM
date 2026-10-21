"""Cost reporting validity checks; these tests never fit a model."""
import numpy as np
import pandas as pd
import pytest

from diabetes_pipeline.journal_revision.a4 import elapsed_utc, selected_payload, routed_predict, prediction_parity, read_cost_csv


@pytest.mark.parametrize("start,end",[("2026-01-01T00:00:00","2026-01-01T00:00:01"),
    ("2026-01-02T00:00:00+00:00","2026-01-01T00:00:01+00:00")])
def test_rejects_unreliable_historical_interval(start,end):
    with pytest.raises(ValueError): elapsed_utc(start,end)


def test_historical_interval_uses_timezone_offsets():
    assert elapsed_utc("2026-01-01T05:30:00+05:30","2026-01-01T00:00:03+00:00")==3


def test_storage_parity_accepts_only_roundoff_and_requires_exact_decisions():
    a={"status":"predicted","probability_raw":.2,"probability_calibrated":.3,"prediction":0}
    assert prediction_parity(a,{**a,"probability_raw":.2+1e-16})
    assert not prediction_parity(a,{**a,"probability_raw":.2+1e-8})
    assert not prediction_parity(a,{**a,"prediction":1})


def test_timing_csv_preserves_subsecond_decimal_roundtrip():
    from io import StringIO
    value="0.0019763328600674868"
    parsed=read_cost_csv(StringIO("seconds\n"+value+"\n"))
    assert parsed.seconds.iloc[0]==float(value)


def test_storage_payload_shares_family_once_and_omits_unused_families():
    model,prep,cal=object(),object(),object()
    b={"configured_features":["a","b"],"scenarios":{"full":["a","b"],"small":["a"]},
       "selected_models":{"full":"used","small":"used"},"threshold":.5,"threshold_policy":"fixed",
       "model_bundles":{"used":{"model":model,"preprocessor":prep,"calibrator":object()},"unused":{}},
       "scenario_calibrators":{"used":{"full":cal,"small":cal},"unused":{}}}
    p=selected_payload(b)
    assert list(p["model_bundles"])==["used"]
    assert p["model_bundles"]["used"]["model"] is model
    assert set(p["scenario_calibrators"]["used"])=={"full","small"}
    assert "calibrator" not in p["model_bundles"]["used"]


def test_fixed_comparator_does_not_apply_panel_calibrator():
    class Prep:
        def transform(self,x):return x
    class Model:
        def predict_proba(self,x):return np.full(len(x),.2)
    class FullCal:
        def predict(self,x):return x+.1
    class NeverPanelCal:
        def predict(self,x):raise AssertionError("Fixed comparator applied a panel map")
    bundle={"scenarios":{"full":["a"]},"selected_models":{"full":"f"},"robust_single_model":"f",
            "configured_features":["a"],"model_bundles":{"f":{"preprocessor":Prep(),"model":Model(),"calibrator":FullCal()}},
            "scenario_calibrators":{"f":{"full":NeverPanelCal()}}}
    np.testing.assert_allclose(routed_predict(bundle,pd.DataFrame({"a":[1,2]}),True),[.3,.3])
