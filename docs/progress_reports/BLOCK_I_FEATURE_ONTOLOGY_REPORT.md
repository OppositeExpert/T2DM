# Block I Checkpoint: Master Feature and Endpoint Ontology

## Status

The master cross-dataset feature dictionary is implemented, validated, and
exported in machine-readable and manuscript-readable forms.

- Dictionary: `feature_ontology/master_feature_dictionary.csv`
- Human report: `feature_ontology/master_feature_dictionary.md`
- Metadata: `feature_ontology/feature_ontology_metadata.json`

## Why this is necessary

The four datasets do not form one interchangeable table. Similar labels often
represent different measurements:

- PIDD `Age` and Sylhet `Age` are years, BRFSS `Age` is an ordered five-year
  group code, and Hospital130 `age` is an ordered ten-year group code.
- PIDD `BMI` and BRFSS `BMI` are quantitative body-mass index, while Sylhet
  `Obesity` is a binary proxy.
- PIDD `BloodPressure` is a diastolic measurement; BRFSS `HighBP` is a binary
  status indicator.
- PIDD `Insulin` is a serum measurement; Hospital130 `insulin` records an
  inpatient medication-change category.
- PIDD `Glucose` is quantitative; Hospital130 `max_glu_serum` is a categorical
  test result and belongs to a different endpoint.

Treating these fields as equivalent would create false harmonization and
misleading patient probabilities.

## Endpoint-first routing contract

The ontology encodes two endpoint families:

1. `diabetes_screening`: PIDD, Sylhet, and BRFSS. Their labels and populations
   are related but not identical, so probabilities cannot be averaged without a
   separately trained and validated harmonized model.
2. `hospital_readmission`: Hospital130 only. Its result is probability of
   readmission within 30 days among encounters involving patients with diabetes,
   never probability of diabetes.

The runtime order is therefore:

`endpoint -> eligible dataset/schema -> evaluated feature panel -> calibrated model`

It is not permitted to choose a dataset solely because its columns happen to
match the patient's fields.

## Coverage

The generated dictionary contains one row for every configured feature:

| Dataset | Endpoint | Features | Explicitly shared/related | Dataset-specific |
|---|---|---:|---:|---:|
| PIDD | Diabetes screening | 8 | 5 | 3 |
| Sylhet | Diabetes screening | 16 | 3 | 13 |
| BRFSS | Diabetes screening | 21 | 6 | 15 |
| Hospital130 | 30-day readmission | 46 | 5 | 41 |
| **Total** |  | **91** | **19 mapping rows** | **72** |

Each mapping records endpoint, source feature, configured type, canonical
concept, semantic relation, measurement scale, and harmonization policy.

## Validation rules

- Every configured feature must appear exactly once.
- Every dataset must belong to exactly one endpoint contract.
- Manual mappings must reference real configured features.
- Proxy/binned semantics must remain explicit.
- Missingness cannot be converted into a fabricated measurement.
- Hospital readmission and diabetes-screening probabilities cannot be pooled.

Two dedicated ontology tests cover full feature coverage and the deliberately
non-comparable PIDD/Hospital insulin semantics.

## Deterministic artifacts

- Ontology YAML SHA-256:
  `8fc0db7300f5b253a05d8d89e1c25dab60f187ede92fe87e57bc12fa1ff95e26`
- Master dictionary SHA-256:
  `ae80751c51e83e113a1d6867bcc64041064958c6012c8286e11a08bd622a9c40`
- Human report SHA-256:
  `e0822d737f1e11fb43ef561d75ae0e9a252fab622b80dd64e6ad9748d2c1617b`
- Source-tree SHA-256 after verification:
  `e1a6f7fe5bf4fd39d7ebe40345f6f148bd9bc09dc3bfbe30ad77862e3aef8cff`

## Publication value

This dictionary prevents an easy-to-miss methodological error and supplies a
reproducible table for the Methods section. It supports a defensible
availability-aware system without pretending that different cohorts,
measurements, or endpoints are directly interchangeable.
