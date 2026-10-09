from __future__ import annotations
import ast, json, copy, warnings
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import yaml
from tests.test_patient_results import _fixture
from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.data.loaders import load_hospital130, _collapse_icd9
from diabetes_pipeline.data.validators import validate_dataset
from diabetes_pipeline.settings import get_dataset_config
from diabetes_pipeline.reporting.patient_results import generate_patient_result, render_patient_result_markdown, _load_router_bundles
from diabetes_pipeline.reporting.mixed_patient_results import generate_mixed_patient_result
from diabetes_pipeline.reporting.publication_readiness import audit_publication_readiness
from diabetes_pipeline.routing.inference import route_patient
from diabetes_pipeline.calibration import calibrators
from diabetes_pipeline.evaluation.selective_prediction import run_selective_prediction_analysis
from diabetes_pipeline.evaluation.subgroup_analysis import run_subgroup_analysis

ROOT=Path('/Users/pranavprabhu/Codex/Minor Proj/T2DM')
OUT=Path('/private/tmp/t2dm-final-audit-20260905')
report={}
def run(name, fn):
    try:
        value=fn()
        report[name]=value
    except Exception as e:
        report[name]={'exception':type(e).__name__,'message':str(e)}
    print(name,json.dumps(report[name],default=str),flush=True)

routers,reference=_fixture()
def compact(result):
    return {key:result.get(key) for key in ('status','reason','dataset','task','endpoint','routing','research_evidence') if key in result}
for name,value in [('valid',1),('fractional_binary',0.5),('nan',np.nan),('infinity',np.inf),('text','bogus'),('nested_list',[0,1]),('nested_object',{'a':1}),('out_of_range',20)]:
    run('patient_'+name,lambda value=value:compact(generate_patient_result(routers,pd.DataFrame([{'a':1,'b':value}]),reference,top_k=1)))
for name,patient,scenario in [('no_features',{},None),('partial',{'a':1},None),('unknown_feature',{'alien':1},None),('extra_feature',{'a':1,'alien':999},None),('unsupported_panel',{'a':1},'bogus'),('missing_required',{'a':1},'full')]:
    run('route_'+name,lambda patient=patient,scenario=scenario:compact(route_patient(routers[0],pd.DataFrame([patient]),scenario_name=scenario)))
references={name:LoadedDataset(name=name,X=reference.X,y=reference.y,row_ids=reference.row_ids,metadata={**reference.metadata,'task':'diabetes_screening','endpoint':name+'_status'}) for name in ('pidd','sylhet','brfss')}
bundles={name:routers for name in references}
for name,patient,preferred in [('one',{'pidd':{'a':1}},None),('multiple',{'pidd':{'a':1},'sylhet':{'a':1}},None),('none',{'pidd':{'b':1}},None),('preferred',{'pidd':{'a':1},'sylhet':{'a':1}},'sylhet'),('invalid_preference',{'pidd':{'a':1}},'invalid')]:
    run('mixed_'+name,lambda patient=patient,preferred=preferred:compact(generate_mixed_patient_result(bundles,patient,references,preferred_dataset=preferred,top_k=1)))
hospital=LoadedDataset(name='hospital130',X=reference.X,y=reference.y,row_ids=reference.row_ids,metadata={'task':'hospital_readmission','endpoint':'readmission_within_30_days'})
run('mixed_hospital',lambda:compact(generate_mixed_patient_result({'pidd':routers,'hospital130':routers},{'pidd':{'a':1},'hospital130':{'a':1}},{'pidd':references['pidd'],'hospital130':hospital},top_k=1)))
bad_bundles=copy.copy(routers)
bad_bundles[1]={**routers[1],'dataset':'wrong_cohort','endpoint':'unrelated_outcome','experiment_id':'other_study','repeat':0,'outer_fold':0,'raw_data_sha256':'WRONG'}
run('mismatched_study_and_duplicate_fold',lambda:compact(generate_patient_result(bad_bundles,pd.DataFrame([{'a':1,'b':1}]),reference,top_k=1)))
run('reference_endpoint_relabels_bundle',lambda:compact(generate_patient_result(routers,pd.DataFrame([{'a':1,'b':1}]),hospital,top_k=1)))
result=generate_patient_result(routers,pd.DataFrame([{'a':1,'b':1}]),reference,top_k=1)
rendered=render_patient_result_markdown(result)
report['markdown_provenance']={'contains_study_id':'fixture_study' in rendered,'contains_cohort_name':'Fixture cohort' in rendered,'contains_endpoint':'fixture_endpoint' in rendered,'contains_development_evidence_word':'development' in rendered.lower(),'contains_disclaimer':'not a diagnosis' in rendered}

# Invalid target and identity after a fixture with both classes has been assured.
cfg=get_dataset_config('hospital130')
raw=pd.read_csv(cfg['raw_path'],low_memory=False)
fixture=raw.head(100).copy(); fixture.loc[0,'readmitted']='<30'; fixture.loc[1,'readmitted']='INVALID'; fixture.loc[1,'patient_nbr']=np.nan
path=OUT/'hospital_invalid.csv';fixture.to_csv(path,index=False)
bad_cfg={**cfg,'raw_path':path}
def hospital_invalid():
    data=load_hospital130(bad_cfg);validate_dataset(data,bad_cfg)
    return {'accepted':True,'invalid_target_encoded_as':int(data.y.loc[1]),'missing_patient_encoded_as':str(data.groups.loc[1])}
run('hospital_invalid_source',hospital_invalid)
retained=raw.loc[~raw.discharge_disposition_id.isin(cfg['excluded_discharge_disposition_ids'])]
icd={}
affected_rows=set()
for field in ('diag_1','diag_2','diag_3'):
    mapping={}
    for value in retained[field].dropna().unique():
        try:
            number=float(value)
            if not np.isfinite(number):continue
        except ValueError:continue
        before=_collapse_icd9(value);after=_collapse_icd9(str(int(number)))
        if before!=after:mapping[str(value)]=(before,after)
    bad=retained[field].astype(str).isin(mapping)
    affected_rows.update(retained.index[bad].tolist())
    icd[field]={'affected_values':mapping,'affected_cells':int(bad.sum())}
report['hospital_icd_boundary']={'fields':icd,'affected_rows':len(affected_rows)}
print('hospital_icd_boundary',json.dumps(report['hospital_icd_boundary']),flush=True)

# Real categorical Hospital130 router: use a reference row and substitute an unseen category.
import joblib
decl=yaml.safe_load((ROOT/'config/authoritative_studies.yaml').read_text())['studies']
hospital_dir=ROOT/'outputs/publication_pipeline/studies'/decl['hospital130']['study_id']
paths=list((hospital_dir/'availability_routing/router_bundles').glob('*.joblib'))
if not paths: paths=list((hospital_dir/'availability_routing').glob('*.joblib'))
if paths:
    real_router=joblib.load(paths[0]);real_reference=load_hospital130(cfg)
    row=real_reference.X.iloc[[0]].copy();row['admission_type_id']='NONEXISTENT_CATEGORY'
    run('real_hospital_unknown_category',lambda:compact(generate_patient_result([real_router],row,real_reference,scenario_name='admission_clinical',top_k=1)))
else:report['real_hospital_unknown_category']={'skipped':'router bundle path not found'}

# Isotonic threshold is applied to total N, not the fitting fold size.
original=calibrators.fit_calibrator; fit_sizes=[]
def traced(method,p,y):
    if method=='isotonic':fit_sizes.append(len(y))
    return original(method,p,y)
y=np.array([0,1]*500);p=np.linspace(.05,.95,1000)
with patch.object(calibrators,'fit_calibrator',side_effect=traced):
    selection=calibrators.select_calibrator(['identity','isotonic'],p,y,n_splits=5,minimum_samples_by_method={'isotonic':1000})
report['isotonic_minimum']={'configured_minimum':1000,'actual_fit_sizes':fit_sizes,'eligible':next(x['eligible'] for x in selection.scores if x['method']=='isotonic')}
run('single_class_group_calibration',lambda:calibrators.select_calibrator(['identity','sigmoid'],np.linspace(.1,.9,20),np.array([0]*10+[1]*10),groups=np.array(['negative']*10+['positive']*10),n_splits=5).method)

# Controlled empty final-artifact fixture: no real metadata, flags or outputs modified.
fake=OUT/'fake_readiness';fake.mkdir(exist_ok=True)
protocol=yaml.safe_load((ROOT/'config/publication_protocol.yaml').read_text())
for key in ('protocol_frozen','novelty_review_complete','claim_evidence_table_complete','tripod_ai_checklist_complete','probast_ai_assessment_complete','ablation_study_complete','selective_prediction_evaluation_complete','subgroup_analysis_complete'):protocol[key]=True
protocol['analysis_plan']['final_execution_authorized']=False
protocol_path=fake/'protocol.yaml';protocol_path.write_text(yaml.safe_dump(protocol))
tree=ast.parse((ROOT/'src/diabetes_pipeline/reporting/publication_readiness.py').read_text())
required={node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str) and node.value.endswith(('.csv','.json','.md')) and not node.value.startswith('#')}
studies=[]
for name in protocol['primary_datasets']:
    directory=fake/name;directory.mkdir(exist_ok=True);studies.append(directory)
    for relative in required:
        file=directory/relative;file.parent.mkdir(parents=True,exist_ok=True);file.touch()
    meta={'dataset':name,'profile':{'name':'final','locked':True},'evidence_tier':'execution_only_smoke','sample_limit_per_partition':None,'runner':'nested_cv','test_access':'not_applicable'}
    (directory/'experiment_metadata.json').write_text(json.dumps(meta))
run('empty_unauthorized_final_readiness',lambda:audit_publication_readiness(studies,protocol_path=protocol_path))
run('required_selective_final_command',lambda:run_selective_prediction_analysis(studies[0]))
run('required_subgroup_final_command',lambda:run_subgroup_analysis(studies[0]))
(OUT/'runtime_probe_results.json').write_text(json.dumps(report,indent=2,default=str))
