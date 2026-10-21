# Original runtime router minus robust fixed policy

Literal router minus robust difference; negative loss differences favor router. 95% paired percentile intervals; Holm adjusts three original policy contrasts within cohort/metric. Robust here is B, not fixed-imputation A.

Display values use six significant figures; the adjacent CSV retains the exact source strings.

| dataset | metric | observed_difference_a_minus_b | ci_lower_a_minus_b | ci_upper_a_minus_b | holm_adjusted_p_value |
| --- | --- | --- | --- | --- | --- |
| pidd | auroc | 0.00145522 | -0.000612127 | 0.00365672 | 0.512744 |
| pidd | average_precision | 0.00119088 | -0.00627471 | 0.00851829 | 1 |
| pidd | brier_score | -0.000763772 | -0.00178121 | 0.00017213 | 0.395802 |
| pidd | log_loss | -0.00180871 | -0.00434755 | 0.000668889 | 0.497751 |
| sylhet | auroc | 0.00579688 | -0.00034964 | 0.0135145 | 0.2009 |
| sylhet | average_precision | 0.00382281 | 9.54828e-05 | 0.00939605 | 0.131934 |
| sylhet | brier_score | -0.00847095 | -0.018154 | -0.000474587 | 0.113943 |
| sylhet | log_loss | -0.0268817 | -0.0491533 | -0.00734689 | 0.0269865 |
| brfss | auroc | 0.000230945 | -0.00012361 | 0.000599826 | 0.213893 |
| brfss | average_precision | 0.000337315 | -0.000934162 | 0.00159763 | 0.621689 |
| brfss | brier_score | -5.75264e-05 | -0.000132455 | 1.68528e-05 | 0.150925 |
| brfss | log_loss | -0.000105972 | -0.000346086 | 0.000128014 | 0.388806 |
| hospital130 | auroc | -0.0063715 | -0.0117129 | -0.000914854 | 0.0749625 |
| hospital130 | average_precision | 0.00656517 | 0.00257197 | 0.0116778 | 0.005997 |
| hospital130 | brier_score | -3.86719e-05 | -0.000249459 | 0.00016224 | 0.708646 |
| hospital130 | log_loss | 0.000135256 | -0.000745163 | 0.0010069 | 0.811594 |
