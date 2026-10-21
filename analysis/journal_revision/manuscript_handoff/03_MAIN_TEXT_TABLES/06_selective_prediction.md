# Selective prediction at approximately 70% observation coverage

Coverage is a fraction of the complete evaluation population/events. Metrics condition on accepted cases. Availability abstention differs from confidence rejection. All targets and uncertainty are supplied in the supplement.

Display values use six significant figures; the adjacent CSV retains the exact source strings.

| dataset | actual_observation_coverage | positive_event_coverage | accepted_n | rejected_n | accepted_positive_events | rejected_positive_events | accepted_prevalence | rejected_prevalence | auroc | average_precision | brier_score | log_loss |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pidd | 0.700521 | 0.548507 | 538 | 230 | 147 | 121 | 0.273234 | 0.526087 | 0.874541 | 0.727187 | 0.113902 | 0.373471 |
| sylhet | 0.7 | 0.76875 | 364 | 156 | 246 | 74 | 0.675824 | 0.474359 | 0.995659 | 0.998019 | 0.0247082 | 0.0967901 |
| brfss | 0.700007 | 0.269409 | 60111 | 25761 | 3085 | 8366 | 0.0513217 | 0.324754 | 0.777973 | 0.131409 | 0.0461962 | 0.177186 |
| hospital130 | 0.700121 | 0.385942 | 13910 | 5958 | 873 | 1389 | 0.0627606 | 0.233132 | 0.5058 | 0.0603456 | 0.0602787 | 0.242339 |
