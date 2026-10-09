# Publication Export Context-Column Deviation

Date: 2026-09-11

## Scope

This deviation affects only post-execution publication packaging. It does not
change model fitting, hyperparameter selection, calibration, thresholds,
predictions, bootstrap samples, subgroup analysis, routing evaluation, SHAP
values, or any completed study artifact.

## Observed failure

After all four frozen studies completed and passed their eligibility checks,
the canonical exporter stopped while reading the BRFSS performance table:

```text
ValueError: cannot insert endpoint, already exists
```

Nested-validation tables do not carry endpoint context, while locked
internal-validation tables already carry it. The exporter assumed the former
schema for every dataset and unconditionally inserted duplicate context
columns.

After that mismatch was corrected, export exposed a second packaging-only
dependency issue: Pandas' `DataFrame.to_latex` requires optional Jinja2, which
is not present in the frozen requirements lock. The environment was not
modified or supplemented. The first figure-build attempt then exposed the same
mixed-schema assumption for an already-present `dataset` column in the
availability-routing table. A subsequent native abort showed that macOS had
selected an interactive Matplotlib backend for the headless export process.

## Resolution

The exporter now attaches `dataset`, `task`, and `endpoint` exactly once. It
preserves matching source columns, supplies missing columns, and fails closed
if a source artifact contains contradictory endpoint identity. Regression
tests cover both the existing-column and contradictory-column cases. A small,
deterministic LaTeX serializer now emits the required tabular files without an
optional dependency; it escapes LaTeX-special characters and formats floats
to four decimal places. The figure builder applies the same preserve-or-reject
rule for dataset identity, with regression coverage for matching and
contradictory inputs, and explicitly selects the deterministic non-interactive
`Agg` backend. The canonical package records both the frozen study-source hash
and the post-execution packaging-source hash, copies this deviation record, and
checksums all copied provenance files. It also snapshots each study's metadata,
execution log, and one-way outcome-access receipt and exports the finalized
confidence-interval, decision-curve, model-comparison, subgroup, selective-
prediction, and BRFSS survey-sensitivity source tables required for manuscript
traceability.

The four completed studies remain bound to the source-tree hash recorded in
the frozen protocol. This packaging-only repair is intentionally documented
as post-execution source drift and is not used to reinterpret or regenerate
their scientific results.
