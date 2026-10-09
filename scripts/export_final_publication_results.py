#!/usr/bin/env python3
"""Build the canonical publication package from four frozen studies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from diabetes_pipeline.publication.exporter import export_final_publication_results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", action="append", required=True, metavar="DATASET=PATH")
    parser.add_argument("--output-dir", type=Path, default=Path("results/final_publication"))
    args = parser.parse_args()
    studies = {}
    for value in args.study:
        dataset, path = value.split("=", 1)
        studies[dataset] = Path(path)
    result = export_final_publication_results(studies, output_dir=args.output_dir)
    print(
        json.dumps(
            {
                "output_dir": str(result.output_dir),
                "master": str(result.master_path),
                "summary": str(result.summary_path),
                "figures": [str(path) for path in result.figure_paths],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
