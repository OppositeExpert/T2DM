# Final End-to-End Leakage Audit Protocol

This audit is executed against the frozen final internal-validation studies and
its machine-readable companion before publication export. The executable audit
is `diabetes_pipeline.publication.leakage_audit`.

The audit verifies the following boundaries rather than inferring safety from a
passing model test suite:

1. raw identity, outcome encoding, row-position, row-ID, target, and group
   bindings agree with each deterministic split manifest;
2. PIDD physiological zero sentinels are converted to missing values before any
   learned imputation, and preprocessors remain fold-fitted;
3. Sylhet identical predictor profiles stay within one side of every prohibited
   fold boundary;
4. BRFSS development/evaluation positions do not overlap, while the result is
   still classified as internal validation because the historical labels were
   accessed;
5. Hospital130 encounter IDs are unique, raw target values are validated, and
   patient identities never cross prohibited partitions;
6. imputation, scaling, categorical vocabulary, calibration, threshold
   selection, model selection, and panel selection are learned from training or
   cross-fitted development predictions only;
7. final study metadata match the frozen raw-data, split, dataset configuration,
   executable analysis, dependency-lock, source-tree, profile, model-registry,
   75-trial, and 2,000-bootstrap bindings;
8. bootstrap outputs record valid and failed replicate counts;
9. SHAP uses evaluation observations and training/development background rows,
   with reconstruction checks;
10. the runtime policy evaluates the largest fully supported prespecified panel,
    reports abstention and event retention, preserves endpoint/protocol
    provenance, and compares the router with fixed comparators on paired rows;
11. publication export rejects smoke, pilot, ordinary development, wrong-endpoint,
    sample-limited, incomplete, or mismatched artifacts.

The audit does not convert retrospective internal validation into clinical,
external, prospective, or causal evidence. The Sylhet naive-split experiment
remains an illustrative leakage demonstration and is never a candidate final
model.
