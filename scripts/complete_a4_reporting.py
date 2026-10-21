#!/usr/bin/env python3
"""Entry point for the separately versioned A4-only cost supplement."""
import runpy

if __name__ == "__main__":
    runpy.run_module("diabetes_pipeline.journal_revision.a4", run_name="__main__")
