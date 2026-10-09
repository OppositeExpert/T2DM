# Final-execution deviation: runtime-policy group-ID dtype

## Scope

The frozen final internal-validation execution reached the PIDD runtime-policy
evaluation only after the complete PIDD benchmark and availability-routing
analysis had finished. No runtime-policy result was written.

## Failure

The policy evaluator passed a pandas object array to `numpy.char.str_len` while
testing whether participant group IDs were present. NumPy rejected that dtype
with `UFuncNoLoopError`. The affected operation was a provenance/resampling-unit
guard; no model, endpoint, metric, threshold, feature panel, resampling count,
or statistical decision rule was changed.

## Disposition

- The failed PIDD study and its one-way execution receipt are retained.
- The in-progress Sylhet and Hospital130 executions were stopped once the source
  defect was known, because any source correction would invalidate their frozen
  source-tree binding. Their partial artifacts and receipts are retained. The
  Hospital130 directory was moved without deletion to
  `hospital130_final_internal_validation_holdout_c7b255d6e90d_invalidated_source_e814b50d`
  before replacement execution because holdout study IDs do not encode the
  source-tree hash.
- The implementation now converts group IDs explicitly to a NumPy Unicode array
  before applying NumPy string operations, and a regression test covers object
  dtype, missing values, and the no-groups case.
- The full test suite must pass and all source/configuration/protocol bindings
  must be recomputed before any replacement final execution begins.

This is a software-correctness deviation, not an outcome-informed analytical
change. Replacement runs remain governed by the originally prespecified
scientific protocol.
