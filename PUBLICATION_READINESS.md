# Publication Readiness

The canonical current audit is
[`conference_package/qa/Publication_Readiness_Audit.md`](conference_package/qa/Publication_Readiness_Audit.md).
Its machine-readable counterpart is
[`conference_package/qa/publication_readiness.json`](conference_package/qa/publication_readiness.json).

Regenerate both from the authoritative study registry with:

```bash
python scripts/run_publication_readiness_audit.py
```

Historical readiness records may remain in progress reports for provenance, but
they are not the current gate.
