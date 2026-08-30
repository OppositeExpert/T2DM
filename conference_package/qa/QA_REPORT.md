# Conference Document QA Report

**Date:** 30 August 2026

## Final verdict

Both generated Word documents pass structural, accessibility, and page-render
inspection for the current development package. This is a document-quality
verdict, not scientific authorization for submission.

## Automated checks

- Both DOCX files open successfully through `python-docx`.
- OOXML ZIP integrity checks return no corrupt members.
- Page geometry is US Letter portrait with 1-inch margins.
- Manuscript structure: 116 paragraphs, 21 styled headings, four tables, five
  inline figures, and one section.
- Supplement structure: 62 paragraphs, 12 styled headings, four tables, no
  figures, and one section.
- All tables use fixed DXA geometry, non-splitting rows, and repeating headers.
- Lists use Word numbering definitions with explicit hanging indentation.
- All five manuscript figures contain descriptive alternative text.
- Accessibility audit: zero high-, medium-, or low-severity findings in both
  documents.
- Development-evidence CSV contains 20 rows (five models for each of PIDD,
  Sylhet, BRFSS, and Hospital130), no non-finite numeric values, and a
  provenance record with source-study and file hashes.

## Visual inspection

- The canonical renderer produced a 13-page manuscript and an eight-page
  supplement, plus PDFs and individual page PNGs.
- Every rendered page was inspected. No text, table, figure, header, footer, or
  list is clipped or overlapped.
- Headings remain on their own lines; table rows no longer split across pages;
  wrapped numbered and bulleted items retain their indentation.
- All five figures were inspected at rendered-page scale and original image
  resolution. Axes, legends, labels, uncertainty marks, and captions are legible.
- The final supplement page contains the complete locked-evidence reservation
  list; no stale blank page remains.

## Archived QA artifacts

- `a11y/manuscript.json`
- `a11y/supplement.json`
- `rendered/manuscript/Conference_Manuscript_Development_Draft.pdf`
- `rendered/manuscript/page-1.png` through `page-13.png`
- `rendered/supplement/Supplementary_Appendix_Development_Draft.pdf`
- `rendered/supplement/page-1.png` through `page-8.png`
