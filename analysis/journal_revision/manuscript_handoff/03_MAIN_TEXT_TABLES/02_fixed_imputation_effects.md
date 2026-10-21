# Complete framework minus fixed imputation

D minus A; intervals/p-values come from the five-contrast ablation family, not the original three-policy family.

Display values use six significant figures; the adjacent CSV retains the exact source strings.

| dataset | metric | observed_difference_a_minus_b | ci_lower_a_minus_b | ci_upper_a_minus_b | holm_adjusted_p_value |
| --- | --- | --- | --- | --- | --- |
| pidd | auroc | 0.00193284 | -0.00110448 | 0.00488806 | 0.794603 |
| pidd | average_precision | 0.00426487 | -0.00310856 | 0.0125108 | 1 |
| pidd | brier_score | -0.000867983 | -0.00222479 | 0.000505404 | 0.698651 |
| pidd | log_loss | -0.00259912 | -0.00594816 | 0.000809013 | 0.77961 |
| sylhet | auroc | 0.0035 | -0.00251324 | 0.0099059 | 0.716642 |
| sylhet | average_precision | 0.00248926 | -0.00102614 | 0.00711519 | 0.527736 |
| sylhet | brier_score | -0.00774583 | -0.017598 | 0.000354512 | 0.25987 |
| sylhet | log_loss | -0.0202666 | -0.0424898 | 0.000392147 | 0.152924 |
| brfss | auroc | 0.00321238 | 0.00228257 | 0.00418681 | 0.0049975 |
| brfss | average_precision | 0.00509563 | 0.00279262 | 0.00737335 | 0.0049975 |
| brfss | brier_score | -0.000899962 | -0.00110578 | -0.000695259 | 0.0049975 |
| brfss | log_loss | -0.00276968 | -0.00340687 | -0.00216249 | 0.0049975 |
| hospital130 | auroc | -0.00712204 | -0.0129636 | -0.00140701 | 0.0849575 |
| hospital130 | average_precision | -0.0014828 | -0.00560004 | 0.0024599 | 1 |
| hospital130 | brier_score | -0.000527354 | -0.000783545 | -0.000270523 | 0.0049975 |
| hospital130 | log_loss | -0.00269962 | -0.00399133 | -0.00147221 | 0.0049975 |
