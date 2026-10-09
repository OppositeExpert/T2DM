# Final End-to-End Leakage Audit

**Verdict:** PASS

**Evidence boundary:** finalized internal validation; not external, temporal, prospective, clinical, or causal validation.

| Check | Status | Evidence |
|---|---|---|
| `brfss_split_identity_binding` | **PASS** | 429360 rows validated against /Users/pranavprabhu/Codex/Minor Proj/T2DM/outputs/publication_pipeline/splits/brfss/d48716267cc6/splits_seed_42.csv |
| `brfss_group_boundary` | **PASS** | maximum prohibited-boundary group overlap=0 |
| `brfss_preprocessor_factory_unfitted` | **PASS** | preprocessing factory returned an unfitted graph |
| `hospital130_split_identity_binding` | **PASS** | 99343 rows validated against /Users/pranavprabhu/Codex/Minor Proj/T2DM/outputs/publication_pipeline/splits/hospital130/c26f5eba292f/splits_seed_42.csv |
| `hospital130_group_boundary` | **PASS** | maximum prohibited-boundary group overlap=0 |
| `hospital130_preprocessor_factory_unfitted` | **PASS** | preprocessing factory returned an unfitted graph |
| `pidd_split_identity_binding` | **PASS** | 19200 rows validated against /Users/pranavprabhu/Codex/Minor Proj/T2DM/outputs/publication_pipeline/splits/pidd/c000944c58f8/splits_seed_42.csv |
| `pidd_group_boundary` | **PASS** | maximum prohibited-boundary group overlap=0 |
| `pidd_preprocessor_factory_unfitted` | **PASS** | preprocessing factory returned an unfitted graph |
| `sylhet_split_identity_binding` | **PASS** | 13000 rows validated against /Users/pranavprabhu/Codex/Minor Proj/T2DM/outputs/publication_pipeline/splits/sylhet/88fad5bc58b2/splits_seed_42.csv |
| `sylhet_group_boundary` | **PASS** | maximum prohibited-boundary group overlap=0 |
| `sylhet_preprocessor_factory_unfitted` | **PASS** | preprocessing factory returned an unfitted graph |
| `pidd_zero_sentinel_handling` | **PASS** | surviving physiological zero sentinels=0 |
| `sylhet_identical_profile_grouping` | **PASS** | unique predictor profiles=251, unique groups=251 |
| `brfss_partition_position_disjointness` | **PASS** | position overlap=0; evidence remains internal validation |
| `hospital130_partition_position_disjointness` | **PASS** | position overlap=0; evidence remains internal validation |
| `hospital130_encounter_identity` | **PASS** | encounters=99343, unique=99343 |
| `brfss_final_identity` | **PASS** | dataset=brfss, endpoint=self_reported_diagnosed_diabetes, tier=final_internal_validation, role=locked_internal_validation |
| `brfss_final_budgets` | **PASS** | profile=final_internal_validation, trials=75, bootstrap=2000 |
| `brfss_required_final_artifacts` | **PASS** | missing_or_empty=none |
| `brfss_bootstrap_accounting` | **PASS** | columns_present=['failed_replicates', 'interval_status', 'valid_replicates'] |
| `brfss_shap_reconstruction` | **PASS** | maximum_absolute_error=5.441428584163077e-06 |
| `hospital130_final_identity` | **PASS** | dataset=hospital130, endpoint=readmission_within_30_days, tier=final_internal_validation, role=locked_internal_validation |
| `hospital130_final_budgets` | **PASS** | profile=final_internal_validation, trials=75, bootstrap=2000 |
| `hospital130_required_final_artifacts` | **PASS** | missing_or_empty=none |
| `hospital130_bootstrap_accounting` | **PASS** | columns_present=['failed_replicates', 'interval_status', 'valid_replicates'] |
| `hospital130_shap_reconstruction` | **PASS** | maximum_absolute_error=4.586467184708454e-06 |
| `pidd_final_identity` | **PASS** | dataset=pidd, endpoint=diabetes_positive_label, tier=final_internal_validation, role=locked_internal_validation |
| `pidd_final_budgets` | **PASS** | profile=final_internal_validation, trials=75, bootstrap=2000 |
| `pidd_required_final_artifacts` | **PASS** | missing_or_empty=none |
| `pidd_bootstrap_accounting` | **PASS** | columns_present=['failed_replicates', 'interval_status', 'valid_replicates'] |
| `pidd_shap_reconstruction` | **PASS** | maximum_absolute_error=9.869690984487534e-06 |
| `sylhet_final_identity` | **PASS** | dataset=sylhet, endpoint=early_stage_diabetes_positive_label, tier=final_internal_validation, role=locked_internal_validation |
| `sylhet_final_budgets` | **PASS** | profile=final_internal_validation, trials=75, bootstrap=2000 |
| `sylhet_required_final_artifacts` | **PASS** | missing_or_empty=none |
| `sylhet_bootstrap_accounting` | **PASS** | columns_present=['failed_replicates', 'interval_status', 'valid_replicates'] |
| `sylhet_shap_reconstruction` | **PASS** | maximum_absolute_error=1.3250857591629028e-05 |
