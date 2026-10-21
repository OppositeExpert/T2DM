# Fixed imputation versus complete framework

A: fixed robust family with original full-schema mapping. D: development-selected panel family and panel mapping. Identical eligible records and training-fitted imputation.

Display values use six significant figures; the adjacent CSV retains the exact source strings.

| dataset | system | evaluation_n | coverage | auroc | average_precision | brier_score | log_loss |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pidd | A | 768 | 1 | 0.834933 | 0.702955 | 0.155736 | 0.472273 |
| pidd | D | 768 | 1 | 0.836866 | 0.70722 | 0.154868 | 0.469674 |
| sylhet | A | 520 | 1 | 0.969141 | 0.981579 | 0.0680246 | 0.224178 |
| sylhet | D | 520 | 1 | 0.972641 | 0.984068 | 0.0602788 | 0.203911 |
| brfss | A | 84632 | 0.98556 | 0.832677 | 0.424636 | 0.0939934 | 0.303948 |
| brfss | D | 84632 | 0.98556 | 0.835889 | 0.429731 | 0.0930934 | 0.301178 |
| hospital130 | A | 19868 | 1 | 0.634262 | 0.188885 | 0.0988425 | 0.345959 |
| hospital130 | D | 19868 | 1 | 0.62714 | 0.187402 | 0.0983152 | 0.343259 |
