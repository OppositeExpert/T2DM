#!/usr/bin/env python3
"""Read-only verification of frozen publication and retained correction evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def verify_manifest(directory: Path, manifest: Path) -> dict[str, object]:
    expected = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(expected, dict) or not expected:
        raise ValueError(f"Expected a nonempty fingerprint mapping: {manifest}")
    failures = []
    verified = 0
    for relative, fingerprint in expected.items():
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory.resolve()) or not path.is_file():
            failures.append(f"missing_or_unsafe:{relative}")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != fingerprint:
            failures.append(f"sha256:{relative}")
        else:
            verified += 1
    return {"manifest": str(manifest), "expected": len(expected),
            "verified": verified, "failures": failures}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-root", type=Path,
                        default=ROOT / "results" / "final_publication")
    parser.add_argument("--support-root", type=Path,
                        default=ROOT / "evidence" / "publication_correction")
    parser.add_argument(
        "--historical-results-root", type=Path,
        help="Optionally verify the complete restored superseded package against its original 87-file manifest.",
    )
    args = parser.parse_args()
    directory = args.results_root.resolve()
    support = args.support_root.resolve()
    results = [
        verify_manifest(directory, directory / "provenance" / "checksums.json"),
        verify_manifest(support, support / "retained_checksums.json"),
    ]
    if args.historical_results_root is not None:
        historical = args.historical_results_root.resolve()
        results.append(verify_manifest(
            historical, historical / "original_publication_checksums.json"
        ))
    passed = all(not result["failures"] for result in results)
    print(json.dumps({"passed": passed, "packages": results,
                      "historical_package_requested": args.historical_results_root is not None}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
