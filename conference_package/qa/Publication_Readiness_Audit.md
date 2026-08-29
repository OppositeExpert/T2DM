# Publication Readiness Audit

**Verdict:** NOT READY

**Blocking checks:** 15

**Warnings:** 1

| Check | Status | Evidence | Required action |
|---|---|---|---|
| `primary_dataset_coverage` | **PASS** | expected=['brfss', 'pidd', 'sylhet'] supplied=['brfss', 'pidd', 'sylhet'] duplicates=[] |  |
| `brfss_final_profile` | **FAIL** | profile=development | Run the full prespecified final profile; pilot and smoke estimates cannot enter the paper's primary table. |
| `brfss_profile_locked` | **FAIL** | locked=False | Freeze the protocol and set locked=true before the one permitted final run. |
| `brfss_full_sample` | **PASS** | sample_limit_per_partition=None |  |
| `brfss_test_access` | **FAIL** | test_access=development_test_previously_accessed_not_final_eligible | For holdout studies, create a fresh locked final study whose test set is accessed exactly once after every choice is frozen; nested-CV studies must report test_access=not_applicable. |
| `brfss_required_artifacts` | **PASS** | missing=[] |  |
| `pidd_final_profile` | **FAIL** | profile=development | Run the full prespecified final profile; pilot and smoke estimates cannot enter the paper's primary table. |
| `pidd_profile_locked` | **FAIL** | locked=False | Freeze the protocol and set locked=true before the one permitted final run. |
| `pidd_full_sample` | **PASS** | sample_limit_per_partition=None |  |
| `pidd_test_access` | **PASS** | test_access=not_applicable |  |
| `pidd_required_artifacts` | **PASS** | missing=[] |  |
| `sylhet_final_profile` | **FAIL** | profile=development | Run the full prespecified final profile; pilot and smoke estimates cannot enter the paper's primary table. |
| `sylhet_profile_locked` | **FAIL** | locked=False | Freeze the protocol and set locked=true before the one permitted final run. |
| `sylhet_full_sample` | **PASS** | sample_limit_per_partition=None |  |
| `sylhet_test_access` | **PASS** | test_access=not_applicable |  |
| `sylhet_required_artifacts` | **PASS** | missing=[] |  |
| `leakage_demonstrations` | **PASS** | missing=[] |  |
| `protocol_frozen` | **FAIL** | protocol_frozen=False | Approve and freeze the statistical analysis plan before final execution. |
| `novelty_review_complete` | **FAIL** | novelty_review_complete=False | Complete the structured literature matrix and narrow the novelty claim. |
| `claim_evidence_table_complete` | **FAIL** | claim_evidence_table_complete=False | Link every abstract/conclusion claim to a frozen result, figure, or citation. |
| `tripod_ai_checklist_complete` | **FAIL** | tripod_ai_checklist_complete=False | Complete the TRIPOD+AI checklist and manuscript crosswalk. |
| `probast_ai_assessment_complete` | **FAIL** | probast_ai_assessment_complete=False | Complete and disclose the PROBAST+AI risk-of-bias/applicability assessment. |
| `ablation_study_complete` | **FAIL** | ablation_study_complete=False | Complete the prespecified component ablations on identical folds and tuning budgets. |
| `selective_prediction_evaluation_complete` | **FAIL** | selective_prediction_evaluation_complete=False | Report risk-coverage behavior and performance at prespecified acceptance levels. |
| `subgroup_analysis_complete` | **FAIL** | subgroup_analysis_complete=False | Report supported subgroup performance and abstention coverage with uncertainty. |
| `mixed_router_claim_scope` | **PASS** | mixed_router_role=software_demonstration_only selector_validated=False |  |
| `dynamic_model_selection_claim_scope` | **PASS** | dynamic_model_selection_role=secondary_negative_result |  |
| `external_or_temporal_validation` | **WARN** | external_or_temporal_validation_complete=False | Add independent or temporal validation before journal-strength, transportability, or clinical-generalization claims. |

A passing software test suite is necessary but not sufficient for a publishable clinical-prediction study. Final locked experiments, a frozen protocol, claim-to-evidence traceability, and reporting/bias checklists are separate requirements.
