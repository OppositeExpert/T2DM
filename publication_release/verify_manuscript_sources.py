#!/usr/bin/env python3
"""Verify the recovered paper's numeric ledgers against exact saved aggregate sources.

Optional manuscript-directory checks confirm display strings occur in source;
they do not replace a complete semantic or PDF layout review.
"""
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "publication_release/paper_evidence"
HANDOFF = ROOT / "analysis/journal_revision/manuscript_handoff"


def source_path(name):
    if name.startswith(("03_MAIN_TEXT_TABLES/", "04_SUPPLEMENTARY_TABLES/")):
        path = HANDOFF / name
    elif name.startswith("frozen_tables/"):
        path = ROOT / "results/final_publication/tables" / Path(name).name
    elif name.startswith("runtime_intervals/"):
        path = PAPER / name
    else:
        raise ValueError(f"Unmapped ledger source: {name}")
    path = path.resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError("Missing or unsafe ledger source")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manuscript-dir", type=Path)
    args = parser.parse_args()
    cache = {}
    result = {}
    for ledger_name, tex_name in [("NUMERIC_CELL_LEDGER.json", "sn-article.tex"),
                                  ("SUPPLEMENT_NUMERIC_CELL_LEDGER.json", "ESM_1_Supplement.tex")]:
        ledger = json.loads((PAPER / ledger_name).read_text())
        tex = (args.manuscript_dir / tex_name).read_text() if args.manuscript_dir else None
        comparator_batch = {}
        for cell in ledger:
            name = cell["source"]
            if name not in cache:
                with source_path(name).open(newline="", encoding="utf-8-sig") as f:
                    cache[name] = list(csv.DictReader(f))
            matched = [r for r in cache[name] if all(r.get(k, "") == v for k, v in cell["row_keys"].items())]
            # The retained comparator ledger omits batch_n from row_keys. Each
            # displayed row starts with its explicit batch_n cell, then costs.
            # Use that context; never silently select an arbitrary duplicate.
            if name.endswith("A4_COMPARATOR_COSTS.csv"):
                dataset = cell["row_keys"]["dataset"]
                if cell["column"] == "batch_n":
                    comparator_batch[dataset] = cell["source_value"]
                if dataset not in comparator_batch:
                    raise ValueError("Comparator ledger lacks preceding batch identity")
                matched = [r for r in matched if r["batch_n"] == comparator_batch[dataset]]
            if len(matched) != 1 or matched[0][cell["column"]] != cell["source_value"]:
                raise ValueError(f"Non-unique row or changed exact source value: {name}/{cell['column']}")
            value = float(cell["source_value"])
            if cell["integer"]:
                expected = f"{int(round(value)):,}"
            elif cell["percent"]:
                expected = f"{100 * value:.{cell['decimals']}f}" + r"\%"
            else:
                expected = f"{value:.{cell['decimals']}f}"
            if expected != cell["display"]:
                raise ValueError(f"Display rounding differs: {name}/{cell['column']}")
            # Macro definitions used in prose may live in verified_values.tex.
            if tex is not None and cell["display"] not in tex:
                macro_file = args.manuscript_dir / "verified_values.tex"
                if not macro_file.is_file() or cell["display"] not in macro_file.read_text():
                    raise ValueError("Ledger display absent from supplied manuscript source/macros")
        result[tex_name] = len(ledger)
    print(json.dumps({"passed": True, "source_cells": result,
                      "distinct_aggregate_sources": len(cache),
                      "exact_source_strings_and_rounding_verified": True,
                      "source_display_presence_checked": args.manuscript_dir is not None,
                      "all_prose_and_pdf_cells_independently_verified": False}, indent=2))


if __name__ == "__main__":
    main()
