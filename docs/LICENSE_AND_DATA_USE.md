# Code and Data Use Status

No repository-level software license has been approved or added. A public clone
therefore does not, by itself, grant a software-use license beyond applicable
law. The project owner and research supervisor must choose and approve a code
license before presenting this repository as reusable open-source software.
`LICENSE_STATUS.md` is the canonical short-form governance notice. The
development `CITATION.cff` deliberately uses a contributor-entity placeholder;
the approved author list must replace it before a public release.

Raw datasets are separate works and are never covered by a future repository
code license. `config/data_sources.yaml` records their sources and known terms:

- Sylhet and Hospital130: their current UCI pages state CC BY 4.0 and provide
  dataset DOIs. Attribution remains required.
- BRFSS 2015: obtained from CDC's annual survey-data release; users must follow
  CDC documentation and survey-analysis guidance.
- PIDD: the historical UCI source record is no longer directly downloadable at
  its former URL. The acquisition helper reconstructs the verified file from an
  OpenML preservation copy, but the original licensing record remains less
  explicit than the two current UCI datasets.

Do not redistribute raw data from this repository. Do not interpret public
availability as consent for clinical deployment, patient-level inference, or
cross-dataset probability pooling. Hospital130 includes demographic attributes
and predicts 30-day readmission, not diabetes status.
