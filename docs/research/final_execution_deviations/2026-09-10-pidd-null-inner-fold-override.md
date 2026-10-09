# Final Execution Deviation: PIDD Null Inner-Fold Override

**Attempted analysis hash:**
`f7f7e6b6e3b327a9cdeab38c3bf9171c01878e63ef653c713ae95e5e439a0cfa`

**Receipt:**
`outputs/publication_pipeline/final_execution_receipts/pidd_f7f7e6b6e3b3.json`

**Observed failure:** The finalized profile correctly encoded
`inner_folds_override: null` to mean that the dataset-native five-fold setting
must be used. The nested runner attempted `int(None)` instead of falling back to
the dataset configuration and stopped with `TypeError`.

**Scientific exposure:** The failure occurred before model tuning, prediction,
metric calculation, or result inspection. An empty study directory was created;
it is retained as failed-attempt provenance and is not eligible for export.

**Correction:** Null overrides are now interpreted as “use the dataset-native
setting” in the benchmark and dependent-analysis paths. The frozen budget,
splits, outcomes, model bank, search spaces, metrics, and selection rules were
not changed.

**Recovery:** The failed receipt is retained permanently. Tests and all frozen
hashes must be regenerated. A new analysis hash and receipt are required for a
replacement execution.
