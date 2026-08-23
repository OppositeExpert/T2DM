# Block J Checkpoint: Multi-Dataset and Mixed-Attribute Routing

## Status

Availability routing now covers PIDD, Sylhet, BRFSS, and Hospital130. The same
inference contract selects the largest evaluated panel contained in a patient's
available fields and abstains when no evaluated panel is satisfied.

- PIDD and Sylhet use repeated outer-fold router ensembles.
- BRFSS and Hospital130 use development-fold routing selection and one locked
  holdout evaluation.
- Integer, floating-point, and categorical columns can all be masked safely.
- Every saved router contains panel-specific model choices, calibrators, and
  development quality metadata.

## One patient with mixed attributes

The mixed input format is one JSON object keyed first by dataset and then by
feature. This preserves dataset semantics for colliding names. In particular,
PIDD/Sylhet `Age` is measured in years, BRFSS `Age` is an age-group code, and
Hospital130 `age` is a ten-year category.

PIDD, Sylhet, and BRFSS routers may all evaluate the same patient. The output is
still one percentage. It is obtained by selecting one eligible expert using a
transparent priority and panel-coverage policy. The system does not average or
otherwise pool cohort probabilities, because there is no matched multi-source
patient cohort on which such fusion has been trained and validated. Attributes
from unselected experts are preserved in the audit output as not used in the
selected percentage.

Hospital130 is excluded from mixed diabetes screening because it predicts
30-day readmission for encounters involving people who already have diabetes.

## Future age prediction

Schema version 2.0 separates prediction targets:

- `diabetes_probability` is available now.
- `onset_age` is present with `status: not_implemented` and a null age.

This lets a future survival/time-to-event or age-at-onset model be added as a
separate validated target without changing the probability contract or
silently deriving an onset age from a cross-sectional diabetes classifier.

## Verification

- All automated tests pass, including mixed-expert selection, age-target
  reservation, readmission-endpoint isolation, and integer-column masking.
- Reloadable routing artifacts were generated successfully for Sylhet, BRFSS,
  and Hospital130 in addition to the existing PIDD artifacts.
- The synthetic mixed input completed end to end and produced one calibrated
  percentage from the selected PIDD expert while reporting the other supplied
  dataset fields as non-fused.
