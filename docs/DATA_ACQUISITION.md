# Data Acquisition and Verification

Raw datasets are intentionally excluded from Git. Their licenses, privacy
context, and size make a source-and-hash manifest safer than redistributing
local copies. `config/data_sources.yaml` is the byte-level authority for the
development inputs used by this repository.

## Verify an existing data directory

```bash
python scripts/acquire_data.py --dataset all
```

The command must report `OK` for all four files before any study is treated as
reproducible. A mismatch is not repaired silently.

## Acquire public source files

```bash
python scripts/acquire_data.py --dataset pidd --download
python scripts/acquire_data.py --dataset sylhet --download
python scripts/acquire_data.py --dataset hospital130 --download
python scripts/acquire_data.py --dataset brfss --download
```

The helper downloads into a temporary directory, verifies the source archive
where applicable, converts or extracts the expected member, verifies the final
SHA-256, and only then moves the file to `data/raw/`. Pass `--force` only after
manually investigating an existing mismatched file.

BRFSS is the largest acquisition: CDC's official 2015 SAS transport archive is
about 97 MB compressed, expands to about 1.17 GB, and produces an approximately
516 MB CSV. The conversion requires pandas and preserves byte-valued SAS string
columns because that is the representation used by the verified development
input. CDC's annual page, codebook, weighting documentation, and the exact
download URL are recorded in the manifest.

PIDD requires special provenance handling. Its historical UCI raw-file URL was
rechecked on 28 August 2026 and returned HTTP 404. OpenML dataset 37 retains the
same 768 records but normalizes numeric display and class labels. The helper
performs the documented, deterministic inverse formatting and verifies the
exact historical project hash. This is a source-recovery path, not a claim that
the original UCI licensing metadata is clearer than it was.

The two current UCI datasets are acquired from their official dataset pages:
Sylhet (DOI `10.24432/C5VG8H`) and Hospital130 (DOI `10.24432/C5230J`). Both
pages currently state CC BY 4.0. Hospital130 contains demographic information
that UCI marks potentially sensitive; retain the raw file locally and keep its
30-day-readmission endpoint separate from diabetes-status studies.

## Loader and cohort assumptions

- PIDD: headerless nine-column file; physiological zeros in glucose, blood
  pressure, skin thickness, insulin, and BMI become missing before fold-local
  imputation.
- Sylhet: 520 questionnaire rows; identical 16-feature profiles are grouped in
  every split.
- BRFSS: 441,456 source rows; only `DIABETE3` responses 1 and 3 are retained,
  yielding 429,360 rows. Responses 2, 4, 7, and 9 are excluded. Survey design
  variables remain available for the separate weighted sensitivity analysis.
- Hospital130: 101,766 source encounters; death/hospice discharge dispositions
  are excluded, yielding 99,343 encounters. Splits and inference are grouped by
  patient. The endpoint is readmission within 30 days.

Do not commit any file under `data/raw/`. Regenerated results are valid only
when their metadata records the expected raw-data hash.
