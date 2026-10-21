#!/usr/bin/env python3
"""Verify a local or restored artifact tree against the tracked release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "evidence" / "artifact_release_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--artifact-root", type=Path, default=ROOT)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    failures: list[str] = []
    verified = 0
    for artifact in manifest["artifacts"]:
        path = args.artifact_root / artifact["relative_local_path"]
        if not path.exists():
            failures.append(f"missing:{artifact['relative_local_path']}")
            continue
        if path.stat().st_size != int(artifact["file_size_bytes"]):
            failures.append(f"size:{artifact['relative_local_path']}")
            continue
        if sha256(path) != artifact["sha256"]:
            failures.append(f"sha256:{artifact['relative_local_path']}")
            continue
        verified += 1
    result = {
        "manifest": str(args.manifest.resolve()),
        "artifact_root": str(args.artifact_root.resolve()),
        "expected": len(manifest["artifacts"]),
        "verified": verified,
        "failures": failures,
        "passed": not failures,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
