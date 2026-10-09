import json, hashlib
from pathlib import Path
import pandas as pd
import numpy as np
import yaml
from sklearn.metrics import brier_score_loss, roc_auc_score, average_precision_score, log_loss

ROOT=Path('/Users/pranavprabhu/Codex/Minor Proj/T2DM');OUT=Path('/private/tmp/t2dm-final-audit-20260905')
decl=yaml.safe_load((ROOT/'config/authoritative_studies.yaml').read_text())['studies']
report={}
for name,entry in decl.items():
    study=ROOT/'outputs/publication_pipeline/studies'/entry['study_id'];r={}
    pred_path=study/('participant_predictions.csv' if name in ('pidd','sylhet') else 'test_predictions.csv')
    preds=pd.read_csv(pred_path); r['primary_prediction_rows']=len(preds)
    r['primary']={}
    for model,frame in preds.groupby('model'):
        y=frame.target;p=frame.probability_calibrated
        r['primary'][model]={'n':len(frame),'events':int(y.sum()),'auroc':roc_auc_score(y,p),'average_precision':average_precision_score(y,p),'brier_score':brier_score_loss(y,p),'log_loss':log_loss(y,p)}
    wanted=['system','scenario','row_id','target','probability_calibrated','repeat']
    source=pd.concat([c.loc[(c.system=='availability_router')&(c.scenario=='full')].copy() for c in pd.read_csv(study/'availability_routing/system_predictions.csv',chunksize=100000,usecols=lambda c:c in wanted)])
    if 'repeat' not in source:source['repeat']=0
    grouped=source.groupby('row_id',as_index=False).agg(target=('target','first'),probability_calibrated=('probability_calibrated','mean'),repeats=('repeat','nunique'))
    saved=pd.read_csv(study/'selective_prediction/acceptance_decisions.csv')
    saved=saved.loc[(saved.system=='availability_router')&(saved.scenario=='full')&(saved.target_coverage==1)]
    joined=grouped.merge(saved,on='row_id',suffixes=('_current','_saved'),validate='one_to_one')
    delta=np.abs(joined.probability_calibrated_current-joined.probability_calibrated_saved)
    r['selective_source_consistency']={'current_participants':len(grouped),'saved_participants':len(saved),'matched':len(joined),'different_probabilities_gt_1e_12':int((delta>1e-12).sum()),'max_probability_difference':float(delta.max()),'current_brier':brier_score_loss(grouped.target,grouped.probability_calibrated),'current_auroc':roc_auc_score(grouped.target,grouped.probability_calibrated),'saved_brier':brier_score_loss(saved.target,saved.probability_calibrated),'current_repeat_counts':grouped.repeats.value_counts().to_dict()}
    if name in ('pidd','sylhet'):
        local=study/'explanations/local_top_contributors_original_features.csv'
        if local.exists():
            f=pd.read_csv(local);counts=f.groupby(['model','row_id']).repeat.nunique()
            r['local_shap_repeat_mix']={'records':len(f),'explanations':len(counts),'mixing_repeats':int((counts>1).sum())}
    report[name]=r
    print(name,json.dumps(r),flush=True)
(OUT/'artifact_probe_results.json').write_text(json.dumps(report,indent=2,default=str))
