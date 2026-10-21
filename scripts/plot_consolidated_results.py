#!/usr/bin/env python3
"""Rebuild the consolidated journal figure from final study directories."""

from __future__ import annotations

import argparse
from pathlib import Path

from diabetes_pipeline.publication.figure import build_consolidated_figure


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", action="append", required=True, metavar="DATASET=PATH")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    studies = {}
    for value in args.study:
        dataset, path = value.split("=", 1)
        studies[dataset] = Path(path)
    for path in build_consolidated_figure(studies, args.output_dir):
        print(path)


if __name__ == "__main__":
    main()
