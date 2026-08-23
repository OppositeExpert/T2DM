# Conference Document QA Report

**Date:** 24 August 2026

## Passed checks

- Both DOCX files open successfully through `python-docx`.
- OOXML ZIP integrity checks return no corrupt members.
- Page geometry is US Letter portrait with 1-inch margins.
- Manuscript structure: 82 paragraphs, 19 styled headings, one table, three
  inline figures, and one section.
- Supplement structure: 47 paragraphs, 10 styled headings, four tables, no
  figures, and one section.
- All tables use explicit fixed DXA geometry and repeating header rows.
- Lists use Word numbering definitions rather than typed bullet/number prefixes.
- All three figures contain descriptive `descr` alternative text.
- Accessibility audit: zero high-, medium-, or low-severity findings in both
  documents.
- All three source figures were inspected at original resolution; labels,
  legends, axes, and plotted values are legible with no clipping or overlap.

## Visual-render limitation

The canonical DOCX renderer could not run because LibreOffice/`soffice` is not
installed. A Microsoft Word export fallback was attempted, but Word required an
interactive file-access grant and the permission was not accepted. Therefore,
the package has not passed page-by-page DOCX render inspection. The documents
meet structural and accessibility checks, but a final human should open both in
Word and inspect every page before submission. This limitation must remain
disclosed until a successful render is archived.

## Generated audit files

- `manuscript/a11y_report.json`
- `supplement/a11y_report.json`
