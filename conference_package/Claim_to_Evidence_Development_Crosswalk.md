# Claim-to-Evidence Development Crosswalk

**State:** Complete for the current development manuscript; must be revalidated
against locked final artifacts before submission

This table prevents a polished sentence from outrunning its evidence. “Supported”
means supported as a development finding, not authorized as a final claim.

| Claim ID | Proposed manuscript claim | Evidence artifact | Current disposition | Final action |
|---|---|---|---|---|
| C01 | The pipeline evaluates five model families with leakage-controlled nested or grouped validation. | PIDD and Sylhet experiment metadata, split manifests, tuning tables, saved outer models | Supported | Confirm hashes and final-profile metadata |
| C02 | PIDD model-family performance is tightly clustered rather than dominated by one complex learner. | `pidd_development_072cd2104089/participant_confidence_intervals.csv` and participant comparisons | Supported | Replace with locked estimates and intervals |
| C03 | The full PIDD router and robust fixed baseline have nearly identical probability performance. | PIDD `availability_routing/summary_metrics.csv` and paired contrasts | Supported; no superiority claim | Retain negative result unless the frozen comparison changes it |
| C04 | Reduced panels show measurable descriptive degradation, but no matched PIDD comparison survives Holm correction. | PIDD `matched_panel_contrasts/paired_contrasts.csv` | Supported | Confirm the frozen comparison family |
| C05 | PIDD panel-specific retraining does not establish corrected superiority over masked full-panel inference. | PIDD `ablations/panel_specific_training/paired_contrasts.csv` | Supported | Recheck after protocol freeze |
| C06 | PIDD missingness indicators do not establish corrected benefit. | PIDD `ablations/missing_indicator_retraining/paired_contrasts.csv` | Supported | Recheck after protocol freeze |
| C07 | Certainty-based selective prediction improves retained-case metrics while disproportionately excluding positive events. | PIDD and Sylhet `selective_prediction/risk_coverage_metrics.csv` | Supported and qualified | Always report positive-event coverage and accepted prevalence |
| C08 | Severe simulated missingness sharply reduces supported-panel coverage and worsens probability loss. | PIDD and Sylhet `missingness_stress/summary_metrics.csv` | Supported as sensitivity analysis | Do not describe as real-world MNAR validation |
| C09 | Sylhet participant-level internal discrimination is high, but the small symptom-enriched cohort limits transportability. | `sylhet_development_b52477910fe6/participant_confidence_intervals.csv` with identical-profile cluster inference | Supported and cautionary | Preserve transportability qualification in abstract and discussion |
| C10 | No completed Sylhet routing, artifact-ablation, or panel-retraining family supports a Holm-corrected superiority claim. | Sylhet routing, matched-panel, and ablation contrast tables, including `ablations/panel_specific_training/paired_contrasts.csv` | Supported | Preserve the negative/inconclusive result in the locked analysis |
| C11 | Mixed namespaced input never fuses probabilities across datasets and abstains when the environment is ambiguous or unsupported. | Routing contracts, patient report schema, tests | Supported as engineering behavior | Keep outside efficacy claim |
| C12 | Returned percentages estimate the configured recorded status label, not future incidence or age at onset. | Dataset contracts, endpoint hierarchy, patient-report wording | Supported boundary | Preserve verbatim meaning in all submission material |
| C13 | The full BRFSS development study shows near-identical boosted-tree performance, panel degradation, and a materially different survey-weighted estimand. | `brfss_development_holdout_56407ef53bba` metrics, intervals, routing, and survey-sensitivity artifacts | Supported as full development only | Replace or explicitly retain as development after an authorized one-time final holdout execution |
| C14 | Hospital130 full-development evidence evaluates a separate 30-day readmission endpoint with patient-grouped inference and is excluded from diabetes-status efficacy claims. | `hospital130_development_holdout_c3aa5fb84a7a` metadata, metrics, intervals, routing, and explanation artifacts | Supported as full development only | Retain endpoint and evidence-tier separation in supplement and code release |
| C15 | The work is not externally or temporally validated and is not clinically deployable. | Protocol flags and blocker register | Supported limitation | Remove only after independent compatible validation |

## Claim rules

- No abstract, table, caption, conclusion, cover letter, or presentation may use a
  stronger interpretation than the corresponding row above.
- Development point estimates must not be relabelled as locked or final.
- “No corrected difference detected” must not be rewritten as equivalence.
- AUROC must be accompanied by probability/calibration evidence and applicability.
- Selective-prediction gains must be accompanied by overall coverage and positive-
  event coverage.
- Every numerical claim must be regenerated from an immutable artifact rather than
  manually copied from terminal output.
