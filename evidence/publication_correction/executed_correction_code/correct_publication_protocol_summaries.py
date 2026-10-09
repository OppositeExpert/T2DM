"""Authorized A-D publication correction using saved predictions only.

Original study files are immutable. Corrected inference is staged separately,
then only dependent publication files are replaced after preservation.
"""
from __future__ import annotations
import hashlib
import json
import shutil
import sys
import platform
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor, as_completed
import numpy as np
import pandas as pd
import yaml

from diabetes_pipeline.publication.protocol_correction import (
    verified_benchmark_tables, aggregate_panel_predictions, panel_summary,
    panel_interval_task, validate_prediction_bindings,
)
from diabetes_pipeline.publication.exporter import _write_table
from diabetes_pipeline.settings import PROJECT_ROOT


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    pub=PROJECT_ROOT/"results/final_publication"
    master=json.loads((pub/"FINAL_RESULTS.json").read_text())
    original_checks=json.loads((pub/"provenance/checksums.json").read_text())
    archive=pub/"superseded_pre_protocol_correction/2026-10-03"
    archive.mkdir(parents=True,exist_ok=True)
    for rel,checksum in original_checks.items():
        source=pub/rel; target=archive/rel
        if target.exists():
            if sha(target)!=checksum: raise ValueError(f"Archive checksum mismatch {rel}")
        else:
            if sha(source)!=checksum: raise ValueError(f"Original artifact changed {rel}")
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    protocol_hash=sha(PROJECT_ROOT/"config/final_publication_protocol.yaml")
    input_hashes={}; staged={}; tasks=[]
    for ds in ("pidd","sylhet"):
        study=Path(master["studies"][ds]["path"])
        meta=json.loads((study/"experiment_metadata.json").read_text())
        output=study/"publication_protocol_correction";output.mkdir(exist_ok=True)
        for rel in ("predictions.csv","participant_predictions.csv","participant_confidence_intervals.csv",
                    "participant_paired_model_comparisons.csv","selected_thresholds.csv","threshold_predictions.csv",
                    "availability_routing/system_predictions.csv","availability_routing/summary_metrics.csv",
                    "availability_routing/confidence_intervals.csv","availability_routing/router_gains.csv",
                    "availability_routing/paired_system_comparisons.csv","availability_routing/routing_metadata.json"):
            input_hashes[str(study/rel)]=sha(study/rel)
            if rel.startswith("availability_routing/") and not rel.endswith("system_predictions.csv"):
                dst=archive/"original_study_derivatives"/ds/rel;dst.parent.mkdir(parents=True,exist_ok=True)
                if not dst.exists():shutil.copy2(study/rel,dst)
        benchmark,benchmark_ci,thresholds=verified_benchmark_tables(study,meta)
        benchmark.to_csv(output/"benchmark_probability_metrics.csv",index=False)
        # Copy correct inference exactly: no unnecessary bootstrap rerun.
        shutil.copy2(study/"participant_confidence_intervals.csv",output/"benchmark_confidence_intervals.csv")
        raw=pd.read_csv(study/"availability_routing/system_predictions.csv",dtype={"row_id":str,"group_id":str})
        validate_prediction_bindings(raw,meta)
        agg=aggregate_panel_predictions(raw,ds)
        agg.to_csv(output/"panel_participant_predictions.csv",index=False)
        summary=panel_summary(agg,meta);summary.to_csv(output/"panel_summary.csv",index=False)
        staged[ds]=(study,meta,output,benchmark,benchmark_ci,thresholds,summary)
        for index,(keys,frame) in enumerate(agg.groupby(["scenario","available_feature_count","system"],sort=True)):
            if keys[2] in {"availability_router","full_panel_champion","robust_single_model"}:
                checkpoint=output/f"ci_{keys[0]}_{keys[2]}.csv"
                if not checkpoint.exists(): tasks.append((ds,checkpoint,(meta,keys,frame,42+1700000+index,2000)))
        print(ds,"source identities, five repeats and retained benchmark inference verified",flush=True)
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(panel_interval_task,t):(ds,path) for ds,path,t in tasks}
        for f in as_completed(futures):
            ds,path=futures[f]; result=f.result();result.to_csv(path,index=False)
            print("Completed",ds,path.name,flush=True)
    for ds,values in staged.items():
        study,meta,output,bench,bci,thresholds,summary=values
        ci=pd.concat([pd.read_csv(p) for p in sorted(output.glob("ci_*.csv"))],ignore_index=True)
        assert ci.n_bootstrap.eq(2000).all()
        assert ci.resampling_unit.eq("cluster" if ds=="sylhet" else "individual").all()
        ci.to_csv(output/"panel_confidence_intervals.csv",index=False)
        gains=[]
        for scenario,f in summary.groupby("scenario"):
            f=f.set_index("system");router=f.loc["availability_router"]
            for baseline in ("full_panel_champion","robust_single_model"):
                b=f.loc[baseline]
                gains.append(dict(dataset=ds,scenario=scenario,baseline=baseline,
                                  average_precision_gain=router.average_precision-b.average_precision,
                                  brier_score_reduction=b.brier_score-router.brier_score,
                                  log_loss_reduction=b.log_loss-router.log_loss))
        pd.DataFrame(gains).to_csv(output/"panel_router_gains.csv",index=False)
    changed_names=["full_panel_model_performance","model_performance_confidence_intervals",
                   "threshold_performance","availability_panel_degradation"]
    frames={n:pd.read_csv(archive/f"tables/{n}.csv") for n in changed_names}
    for n in changed_names:
        frames[n]=frames[n][~frames[n].dataset.isin(["pidd","sylhet"])].copy()
    for ds,(study,meta,output,bench,bci,thresholds,summary) in staged.items():
        identity={k:meta[k] for k in ["dataset","task","endpoint"]}
        def contextual(f):
            f=f.copy()
            for k,v in identity.items():f[k]=v
            return f
        frames["full_panel_model_performance"]=pd.concat([frames["full_panel_model_performance"],bench[bench.probability_version.eq("calibrated")]],ignore_index=True)
        frames["model_performance_confidence_intervals"]=pd.concat([frames["model_performance_confidence_intervals"],contextual(bci)],ignore_index=True)
        frames["threshold_performance"]=pd.concat([frames["threshold_performance"],contextual(thresholds)],ignore_index=True)
        panels=summary[summary.system.eq("availability_router")].copy()
        full=panels[panels.scenario.eq("full")].iloc[0]
        for metric in ("auroc","average_precision"):
            panels[f"{metric}_degradation_from_full"]=full[metric]-panels[metric]
        frames["availability_panel_degradation"]=pd.concat([frames["availability_panel_degradation"],panels],ignore_index=True)
    for name,frame in frames.items(): _write_table(frame,pub/"tables",name)
    panel_ci=pd.concat([pd.read_csv(v[2]/"panel_confidence_intervals.csv") for v in staged.values()],ignore_index=True)
    _write_table(panel_ci,pub/"tables","availability_panel_confidence_intervals")
    all_panels=pd.concat([v[-1] for v in staged.values()],ignore_index=True)
    _write_table(all_panels,pub/"tables","repeated_panel_all_system_performance")
    descriptive=[]
    for ds in staged:
        old=pd.read_csv(archive/"tables/model_performance_confidence_intervals.csv")
        f=old[(old.dataset==ds)&old.threshold_policy.ne("fixed_0_5")].copy()
        f["estimation_scope"]="repeat_level_descriptive_development_thresholds"
        descriptive.append(f)
    _write_table(pd.concat(descriptive,ignore_index=True),pub/"tables","descriptive_threshold_confidence_intervals")
    # Build combined figure in staging, replacing only the dependent combined image and panel-c data.
    from diabetes_pipeline.publication.figure import build_consolidated_figure
    tmp=pub/"correction_figure_staging"
    build_consolidated_figure({ds:Path(s["path"]) for ds,s in master["studies"].items()},tmp)
    for name in ("panel_a_calibration.csv","panel_b_decision_curves.csv"):
        assert sha(tmp/"data"/name)==sha(pub/"figure/data"/name),f"Unrelated figure values changed {name}"
    for p in tmp.glob("consolidated_results.*"):shutil.copy2(p,pub/"figure"/p.name)
    shutil.copy2(tmp/"data/panel_c_availability_degradation.csv",pub/"figure/data/panel_c_availability_degradation.csv")
    shutil.rmtree(tmp)
    changes=[]
    for name in ("full_panel_model_performance","availability_panel_degradation"):
        old=pd.read_csv(archive/f"tables/{name}.csv");new=frames[name]
        keys=["dataset","model"] if name.startswith("full_panel") else ["dataset","scenario"]
        for record in new[new.dataset.isin(staged)].to_dict("records"):
            prior=old.copy()
            for k in keys:prior=prior[prior[k]==record[k]]
            if len(prior)!=1:raise ValueError("Ambiguous historical comparison")
            prior=prior.iloc[0]
            for metric in ("auroc","average_precision","brier_score","log_loss","calibration_intercept","calibration_slope","observed_expected_ratio","expected_calibration_error","auroc_degradation_from_full","average_precision_degradation_from_full"):
                if metric not in prior or metric not in record:continue
                before=float(prior[metric]);after=float(record[metric]);delta=after-before
                changes.append({**{k:record[k] for k in keys},"metric":metric,"previous_value":before,
                                "corrected_value":after,"signed_difference":delta,"absolute_difference":abs(delta),
                                "relative_difference":delta/before if before else np.nan,
                                "source_before":str(archive/f"tables/{name}.csv"),"source_after":str(pub/f"tables/{name}.csv")})
    pd.DataFrame(changes).to_csv(pub/"provenance/correction_value_changes.csv",index=False)
    ci_changes=[]
    oldci=pd.read_csv(archive/"tables/model_performance_confidence_intervals.csv")
    newci=frames["model_performance_confidence_intervals"]
    for record in newci[newci.dataset.isin(staged)].to_dict("records"):
        prior=oldci
        for key in ["dataset","model","probability_version","threshold_policy","metric"]:
            prior=prior[prior[key]==record[key]]
        for oldrow in prior.to_dict("records"):
            for bound in ["estimate","ci_lower","ci_upper"]:
                ci_changes.append({k:record[k] for k in ["dataset","model","probability_version","metric"]}|dict(
                    historical_repeat=oldrow["repeat"],component=bound,previous_value=oldrow[bound],corrected_value=record[bound],
                    absolute_difference=abs(record[bound]-oldrow[bound]),source_before=str(archive/"tables/model_performance_confidence_intervals.csv"),
                    source_after=str(pub/"tables/model_performance_confidence_intervals.csv"),comparison_note="Different aggregation estimands; not paired replacement replicates"))
    pd.DataFrame(ci_changes).to_csv(pub/"provenance/correction_interval_changes.csv",index=False)
    provenance=dict(correction_date_utc=datetime.now(timezone.utc).isoformat(),findings=["A","B","C","D"],
                    aggregation="participant_mean_probability_across_repeats",sylhet_unit="identical_predictor_profile",
                    bootstrap_count=2000,validity_rule="at_least_1900_finite_replicates",protocol_file_sha256=protocol_hash,
                    original_study_source_sha256=master["study_source_tree_sha256"],python=sys.version,
                    platform=platform.platform(),input_files=input_hashes,
                    correction_code_sha256=sha(Path(__file__)),
                    correction_module_sha256=sha(PROJECT_ROOT/"src/diabetes_pipeline/publication/protocol_correction.py"),
                    benchmark_intervals="verified_retained_artifacts_reused_without_regeneration",
                    threshold_estimand="development thresholds remain descriptive mean outer-fold results")
    (pub/"provenance/protocol_correction.json").write_text(json.dumps(provenance,indent=2)+"\n")
    for path,h in input_hashes.items():assert sha(path)==h,f"Study input changed {path}"
    assert sha(PROJECT_ROOT/"config/final_publication_protocol.yaml")==protocol_hash
    changed=[]
    for rel,h in original_checks.items():
        newhash=sha(pub/rel)
        if newhash!=h:
            if not (rel.startswith(tuple(f"tables/{n}." for n in changed_names)) or rel.startswith("figure/consolidated_results.") or rel=="figure/data/panel_c_availability_degradation.csv"):
                raise ValueError(f"Unrelated publication file changed {rel}")
            changed.append(dict(original_path=rel,original_checksum=h,replacement_path=rel,replacement_checksum=newhash,
                                date="2026-10-03",finding="A/B" if "availability" in rel or rel.startswith("figure/") else "C/D",
                                reason="Derived publication summary/source selection corrected to frozen protocol"))
    (archive/"supersession_manifest.json").write_text(json.dumps(changed,indent=2)+"\n")
    # Preserve historical master bindings. Add an explicit correction overlay.
    master["publication_correction"]={"record":"provenance/protocol_correction.json","historical_package":"superseded_pre_protocol_correction/2026-10-03",
                                     "corrected_panel_sources":{ds:str(v[2]) for ds,v in staged.items()}}
    master["tables"]["availability_panel_confidence_intervals"]="tables/availability_panel_confidence_intervals.csv"
    (pub/"FINAL_RESULTS.json").write_text(json.dumps(master,indent=2,sort_keys=True)+"\n")
    current={str(p.relative_to(pub)):sha(p) for p in pub.rglob("*") if p.is_file() and "superseded_pre_protocol_correction" not in p.parts and p.name!="checksums.json" and p.name!=".DS_Store"}
    (pub/"provenance/checksums.json").write_text(json.dumps(current,indent=2,sort_keys=True)+"\n")
    print("Authorized corrections completed; unrelated registered files preserved.",flush=True)


if __name__=="__main__":main()
