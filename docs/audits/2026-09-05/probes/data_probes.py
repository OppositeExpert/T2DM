from __future__ import annotations
import json, hashlib
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pandas as pd
import yaml
from diabetes_pipeline.contracts import LoadedDataset
from diabetes_pipeline.data.loaders import load_dataset, load_hospital130, _collapse_icd9
from diabetes_pipeline.data.validators import validate_dataset
from diabetes_pipeline.evaluation.subgroup_analysis import subgroup_membership, _age_groups
from diabetes_pipeline.settings import get_dataset_config
from diabetes_pipeline.splitting.strategies import build_split_manifest
from diabetes_pipeline.splitting.registry import validate_split_manifest

ROOT=Path('/Users/pranavprabhu/Codex/Minor Proj/T2DM')
OUT=Path('/private/tmp/t2dm-final-audit-20260905')
decl=yaml.safe_load((ROOT/'config/authoritative_studies.yaml').read_text())['studies']
report={}
for name in ('pidd','sylhet','brfss','hospital130'):
    ds=load_dataset(name); cfg=get_dataset_config(name)
    validate_dataset(ds,cfg)
    study=ROOT/'outputs/publication_pipeline/studies'/decl[name]['study_id']
    meta=json.loads((study/'experiment_metadata.json').read_text())
    original_split=Path(meta['split_manifest'])
    local_split=ROOT/'outputs/publication_pipeline/splits'/name/meta['dataset_configuration_sha256'][:12]/f"splits_seed_{meta['profile']['seed']}.csv"
    detail={'rows':len(ds.X),'events':int(ds.y.sum()),'groups':int(ds.groups.nunique()) if ds.groups is not None else None,
      'duplicates':int(ds.X.duplicated().sum()),'non_contiguous_index':not ds.X.index.equals(pd.RangeIndex(len(ds.X))),
      'stored_split_exists':original_split.exists(),'local_split_exists':local_split.exists(),
      'local_split_hash_matches':hashlib.sha256(local_split.read_bytes()).hexdigest()==meta['split_manifest_sha256'] if local_split.exists() else None}
    # Compare actual persisted subgroup assignments with positionally aligned source fields.
    if name in ('brfss','hospital130'):
        membership=subgroup_membership(name)
        persisted=pd.read_csv(study/'subgroup_analysis/subgroup_membership.csv',dtype={'row_id':str})
        detail['subgroups']={}
        raw_values={
          'age_group':_age_groups(name,ds.X['Age' if name=='brfss' else 'age']).reset_index(drop=True),
          'sex': (ds.X['Sex'].map({0.0:'female',1.0:'male'}) if name=='brfss' else ds.X['gender'].astype('string').str.strip().str.lower().map({'male':'male','female':'female'})).reset_index(drop=True)}
        if name=='hospital130': raw_values['race']=ds.X['race'].astype('string').str.strip().reset_index(drop=True)
        for variable,expected_values in raw_values.items():
            expected=pd.DataFrame({'row_id':ds.row_ids.astype(str).to_numpy(),'expected':expected_values})
            actual=membership[membership.subgroup_variable==variable][['row_id','subgroup_value']]
            joined=expected.merge(actual,on='row_id',how='left',validate='one_to_one')
            known=joined.expected.notna()
            same=joined.expected.fillna('<missing>')==joined.subgroup_value.fillna('<missing>')
            p=persisted[persisted.subgroup_variable==variable][['row_id','subgroup_value']]
            persisted_join=expected.merge(p,on='row_id',how='left',validate='one_to_one')
            persisted_same=persisted_join.expected.fillna('<missing>')==persisted_join.subgroup_value.fillna('<missing>')
            detail['subgroups'][variable]={'expected_known':int(known.sum()),'assigned':len(actual),
              'wrong_nonmissing':int((known&joined.subgroup_value.notna()&~same).sum()),
              'known_dropped':int((known&joined.subgroup_value.isna()).sum()),
              'persisted_disagreements':int((~persisted_same).sum())}
    # Check actual split groups directly against dataset positions rather than trusting saved group strings.
    manifest=pd.read_csv(local_split,keep_default_na=False)
    if ds.groups is not None:
        if name=='hospital130':
            group=ds.groups.iloc[manifest.row_position.to_numpy(int)].astype(str).to_numpy()
            detail['actual_holdout_group_overlap']=len(set(group[manifest.role.eq('development')])&set(group[manifest.role.eq('test')]))
        else:
            overlaps=[]
            for _,f in manifest.groupby(['repeat','outer_fold']):
                tr=ds.groups.iloc[f.loc[f.role.eq('train'),'row_position'].to_numpy(int)]
                va=ds.groups.iloc[f.loc[f.role.eq('validation'),'row_position'].to_numpy(int)]
                overlaps.append(len(set(tr)&set(va)))
            detail['max_actual_outer_group_overlap']=max(overlaps)
    report[name]=detail
    print(name,json.dumps(detail),flush=True)

# CDC codebook says _CHOLCHK=2 is no check within five years.
raw=pd.read_csv(ROOT/'data/raw/brfss.csv',usecols=['DIABETE3','_CHOLCHK'])
retained=raw[raw.DIABETE3.isin([1,3])]
report['cholcheck']={'raw_counts':raw._CHOLCHK.value_counts().to_dict(),'retained_code_2':int(retained._CHOLCHK.eq(2).sum()),'retained_n':len(retained)}

# Counterexample: role/identity text is intact, but every validation row points at a training row.
ds=load_dataset('pidd'); cfg=get_dataset_config('pidd'); manifest=build_split_manifest(ds,cfg)
bad=manifest.copy()
for _, f in bad.groupby(['repeat','outer_fold']):
    training_position=int(f.loc[f.role.eq('train'),'row_position'].iloc[0])
    bad.loc[f.index[f.role.eq('validation')],'row_position']=training_position
try: validate_split_manifest(ds,bad,cfg); report['invalid_row_positions_accepted']=True
except Exception as e: report['invalid_row_positions_accepted']=str(e)

# Hospital invalid outcomes and null patient identities should fail their contract.
hospital_cfg=get_dataset_config('hospital130')
fixture=pd.read_csv(hospital_cfg['raw_path'],nrows=10)
fixture.loc[1,'readmitted']='INVALID'; fixture.loc[1,'patient_nbr']=np.nan
temp=OUT/'hospital_invalid.csv'; fixture.to_csv(temp,index=False)
temporary_cfg={**hospital_cfg,'raw_path':temp}
try:
    invalid=load_hospital130(temporary_cfg); validate_dataset(invalid,temporary_cfg)
    report['hospital_invalid_raw_accepted']={'target_at_invalid_row':int(invalid.y.loc[1]),'group_at_missing_patient':str(invalid.groups.loc[1])}
except Exception as e: report['hospital_invalid_raw_accepted']={'error':repr(e)}
report['icd_decimal_examples']={k:_collapse_icd9(k) for k in ['459.0','459.9','785.0','785.9','519.9','239.9','250.13']}
(OUT/'data_probe_results.json').write_text(json.dumps(report,indent=2,default=str))
print(json.dumps({k:v for k,v in report.items() if k not in decl},indent=2,default=str),flush=True)
