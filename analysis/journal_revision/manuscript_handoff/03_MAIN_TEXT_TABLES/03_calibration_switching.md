# Frozen-family 2 × 2 ablation

A/B: robust fixed family; C/D: panel-selected family. A/C: full-schema mapping; B/D: panel mapping. B equals historical robust policy and D equals historical router. Five declared paired contrasts per cohort/metric are in the supplement.

Display values use six significant figures; the adjacent CSV retains the exact source strings.

| dataset | system | evaluation_n | auroc | average_precision | brier_score | log_loss |
| --- | --- | --- | --- | --- | --- | --- |
| pidd | A | 768 | 0.834933 | 0.702955 | 0.155736 | 0.472273 |
| pidd | B | 768 | 0.83541 | 0.706029 | 0.155632 | 0.471483 |
| pidd | C | 768 | 0.836552 | 0.704993 | 0.154946 | 0.470365 |
| pidd | D | 768 | 0.836866 | 0.70722 | 0.154868 | 0.469674 |
| sylhet | A | 520 | 0.969141 | 0.981579 | 0.0680246 | 0.224178 |
| sylhet | B | 520 | 0.966844 | 0.980246 | 0.0687497 | 0.230793 |
| sylhet | C | 520 | 0.972125 | 0.98384 | 0.0599277 | 0.203317 |
| sylhet | D | 520 | 0.972641 | 0.984068 | 0.0602788 | 0.203911 |
| brfss | A | 84632 | 0.832677 | 0.424636 | 0.0939934 | 0.303948 |
| brfss | B | 84632 | 0.835658 | 0.429394 | 0.093151 | 0.301284 |
| brfss | C | 84632 | 0.832822 | 0.425572 | 0.0938552 | 0.3036 |
| brfss | D | 84632 | 0.835889 | 0.429731 | 0.0930934 | 0.301178 |
| hospital130 | A | 19868 | 0.634262 | 0.188885 | 0.0988425 | 0.345959 |
| hospital130 | B | 19868 | 0.633512 | 0.180837 | 0.0983538 | 0.343124 |
| hospital130 | C | 19868 | 0.62714 | 0.187402 | 0.0989353 | 0.34599 |
| hospital130 | D | 19868 | 0.62714 | 0.187402 | 0.0983152 | 0.343259 |
