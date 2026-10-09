import json
from pathlib import Path
from unittest.mock import patch
from diabetes_pipeline import runner
from diabetes_pipeline.data.manifests import write_audit
from diabetes_pipeline.splitting.registry import create_and_write_split_manifest

out=Path('/private/tmp/t2dm-final-audit-20260905/isolated_smoke')
with patch.object(runner,'DEFAULT_OUTPUT_ROOT',out), patch.object(runner,'write_audit',side_effect=lambda dataset:write_audit(dataset,output_root=out)), patch.object(runner,'create_and_write_split_manifest',side_effect=lambda dataset,seed:create_and_write_split_manifest(dataset,seed=seed,output_root=out)):
    result=runner.run_nested_benchmark('pidd',profile_name='smoke',models=['logistic_regression'])
    print(json.dumps(vars(result),indent=2,default=str))
