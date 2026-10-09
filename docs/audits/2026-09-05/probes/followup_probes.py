import json, hashlib, subprocess
from pathlib import Path
import pandas as pd
import numpy as np
import yaml, joblib
from diabetes_pipeline.settings import get_dataset_config
from diabetes_pipeline.data.loaders import load_dataset, load_hospital130
from diabetes_pipeline.data.validators import validate_dataset
from diabetes_pipeline.reporting.patient_results import generate_patient_result
from diabetes_pipeline.reporting.publication_readiness import audit_publication_readiness

ROOT=Path('/Users/pranavprabhu/Codex/Minor Proj/T2DM');OUT=Path('/private/tmp/t2dm-final-audit-20260905')
decl=yaml.safe_load((ROOT/'config/authoritative_studies.yaml').read_text())['studies']
panels=yaml.safe_load((ROOT/'config/availability_scenarios.yaml').read_text())['datasets']
report={'panel_missingness':{}}
for name in decl:
    ds=load_dataset(name)
    counts={key:int(ds.X[scenario['available_features']].notna().all(axis=1).sum()) for key,scenario in panels[name]['scenarios'].items()}
    any_supported=np.zeros(len(ds.X),dtype=bool)
    for scenario in panels[name]['scenarios'].values():any_supported |= ds.X[scenario['available_features']].notna().all(axis=1).to_numpy()
    report['panel_missingness'][name]={'cohort_n':len(ds.X),'eligible_by_panel':counts,'any_supported':int(any_supported.sum())}
    if name=='hospital130':hospital=ds
report['actual_readiness']=audit_publication_readiness([ROOT/'outputs/publication_pipeline/studies'/decl[name]['study_id'] for name in ('pidd','sylhet','brfss')])
cfg=get_dataset_config('hospital130');fixture=pd.read_csv(cfg['raw_path'],nrows=100)
fixture.loc[0,'readmitted']='<30';fixture.loc[1,'readmitted']='INVALID'
path=OUT/'hospital_invalid_target_only.csv';fixture.to_csv(path,index=False)
bad_cfg={**cfg,'raw_path':path}
try:
    ds=load_hospital130(bad_cfg);validate_dataset(ds,bad_cfg)
    report['invalid_hospital_target_only']={'accepted':True,'encoded_as':int(ds.y.loc[1])}
except Exception as e:report['invalid_hospital_target_only']={'error':repr(e)}
study=ROOT/'outputs/publication_pipeline/studies'/decl['hospital130']['study_id']
bundle=joblib.load(next((study/'availability_routing/router_bundles').glob('*.joblib')))
features=panels['hospital130']['scenarios']['admission_clinical']['available_features']
patient=hospital.X.loc[hospital.X[features].notna().all(axis=1)].iloc[[0]].copy()
patient['admission_type_id']='NONEXISTENT_CATEGORY'
try:
    res=generate_patient_result([bundle],patient,hospital,scenario_name='admission_clinical',top_k=1)
    report['real_hospital_unknown_category']={'status':res['status'],'reason':res.get('reason'),'selected_scenario':res.get('feature_availability',{}).get('selected_scenario')}
except Exception as e:report['real_hospital_unknown_category']={'error':repr(e)}

# Find whether each historical source hash has a reconstructable Git commit.
targets={}
for name,entry in decl.items():
    meta=json.loads((ROOT/'outputs/publication_pipeline/studies'/entry['study_id']/'experiment_metadata.json').read_text())
    targets.setdefault(meta.get('pipeline_source_tree_sha256',meta.get('source_tree_sha256')),[]).append(name)
matches={}
revisions=subprocess.check_output(['git','rev-list','--all','--','src/diabetes_pipeline'],cwd=ROOT,text=True).splitlines()
for rev in revisions:
    paths=sorted(subprocess.check_output(['git','ls-tree','-r','--name-only',rev,'src/diabetes_pipeline'],cwd=ROOT,text=True).splitlines())
    digest=hashlib.sha256()
    for file in paths:
        if not file.endswith('.py'):continue
        digest.update(file.encode());digest.update(subprocess.check_output(['git','show',f'{rev}:{file}'],cwd=ROOT))
    h=digest.hexdigest()
    if h in targets:matches[h]=rev
report['source_history']={'targets':targets,'matching_commits':matches,'commits_checked':len(revisions)}
(OUT/'followup_probe_results.json').write_text(json.dumps(report,indent=2,default=str))
print(json.dumps(report,indent=2,default=str))
