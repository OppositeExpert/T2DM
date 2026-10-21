# Computational cost

Final-fit/calibration SUMS in seconds over reduced-schema tasks; loaded original-artifact D inference in ms per call (batch is 256 records); exemplar storage in MiB=2^20 bytes. These columns describe different workloads, not one model's training-to-deployment lifecycle. Historical environment is unknown; see A4 publication summary.

Display values use six significant figures; the adjacent CSV retains the exact source strings.

| dataset | reduced_tasks | successor_final_fit_sum_s | successor_calibration_sum_s | D_single_median_ms | D_batch256_median_ms | exemplar_model_MiB | exemplar_calibrator_MiB | exemplar_prediction_triple_MiB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pidd | 125 | 13.0258 | 0.889598 | 2.13562 | 6.27158 | 0.0554867 | 0.000576019 | 0.0569286 |
| sylhet | 100 | 19.0643 | 3.79167 | 28.0335 | 52.9328 | 0.81616 | 0.000576973 | 0.817732 |
| brfss | 5 | 51.4581 | 3.80137 | 2.14658 | 11.2605 | 0.759795 | 8.86917e-05 | 0.761136 |
| hospital130 | 4 | 14.6965 | 67.0703 | 30.6046 | 45.9091 | 27.1382 | 0.000575066 | 27.1416 |
