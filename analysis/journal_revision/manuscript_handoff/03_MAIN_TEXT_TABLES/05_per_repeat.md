# Five-repeat sensitivity versus primary estimate

Pair repeat_metric_mean with repeat_metric_sample_sd as mean ± descriptive sample SD (five dependent repeats). Primary metrics first average five OOF probabilities per participant. SD is not a confidence interval.

Display values use six significant figures; the adjacent CSV retains the exact source strings.

| dataset | summary | evaluation_n | positive_events | auroc | average_precision | brier_score | log_loss |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pidd | repeat_metric_mean | 768 | 268 | 0.832639 | 0.699255 | 0.157324 | 0.476492 |
| pidd | repeat_metric_sample_sd | 768 | 268 | 0.00569258 | 0.0158828 | 0.00332862 | 0.00726042 |
| pidd | participant_mean_probability_metric | 768 | 268 | 0.836866 | 0.70722 | 0.154868 | 0.469674 |
| sylhet | repeat_metric_mean | 520 | 320 | 0.962944 | 0.9784 | 0.0665965 | 0.241065 |
| sylhet | repeat_metric_sample_sd | 520 | 320 | 0.00766712 | 0.00545379 | 0.00415086 | 0.0304336 |
| sylhet | participant_mean_probability_metric | 520 | 320 | 0.972641 | 0.984068 | 0.0602788 | 0.203911 |
