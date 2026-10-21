#!/usr/bin/env python3
"""Run isolated post-review analyses without changing frozen study artifacts."""
from __future__ import annotations

import argparse

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["audit", "saved", "ablation", "pilot", "train", "panels", "statistics", "benchmark", "report", "verify"])
    parser.add_argument("--dataset", choices=["pidd", "sylhet", "brfss", "hospital130", "all"], default="all")
    args = parser.parse_args()
    if args.phase == "audit":
        from diabetes_pipeline.journal_revision.audit import run_audit
        run_audit()
    elif args.phase == "verify":
        from diabetes_pipeline.journal_revision.audit import verify_protected
        print(verify_protected())
    else:
        from importlib import import_module
        module = {"saved": "saved", "ablation": "experiments", "pilot": "experiments", "train": "experiments",
                  "panels": "experiments", "statistics": "verification", "benchmark": "benchmark", "report": "reporting"}[args.phase]
        getattr(import_module(f"diabetes_pipeline.journal_revision.{module}"), f"run_{args.phase}")(args.dataset)

if __name__ == "__main__":
    main()
