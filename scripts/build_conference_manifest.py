"""Create a checksum manifest for the development conference package."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "conference_package"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    authoritative = yaml.safe_load(
        (ROOT / "config" / "authoritative_studies.yaml").read_text(encoding="utf-8")
    )["studies"]
    included = []
    for path in sorted(PACKAGE.rglob("*")):
        if not path.is_file() or path.name == "package_manifest.json":
            continue
        included.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    manifest = {
        "manifest_version": 1,
        "created_date": date.today().isoformat(),
        "evidence_role": "development_only_not_submission_authorized",
        "development_studies": {
            dataset: declaration["study_id"]
            for dataset, declaration in authoritative.items()
        },
        "protocol_frozen": False,
        "final_execution_authorized": False,
        "files": included,
    }
    (PACKAGE / "package_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
