from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_publication_results", ROOT / "scripts/verify_publication_results.py"
)
VERIFIER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(VERIFIER)


class PublicationFingerprintTests(unittest.TestCase):
    def test_current_and_retained_evidence_match_without_conference_files(self) -> None:
        publication = ROOT / "results/final_publication"
        support = ROOT / "evidence/publication_correction"
        for directory, manifest in (
            (publication, publication / "provenance/checksums.json"),
            (support, support / "retained_checksums.json"),
        ):
            result = VERIFIER.verify_manifest(directory, manifest)
            self.assertFalse(result["failures"])
            self.assertEqual(result["verified"], result["expected"])

    def test_changed_missing_and_escaping_files_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "table.csv"
            artifact.write_bytes(b"original")
            manifest = root / "checksums.json"
            expected = hashlib.sha256(b"original").hexdigest()
            manifest.write_text(json.dumps({"table.csv": expected}))
            self.assertFalse(VERIFIER.verify_manifest(root, manifest)["failures"])
            artifact.write_bytes(b"changed")
            self.assertEqual(VERIFIER.verify_manifest(root, manifest)["failures"],
                             ["sha256:table.csv"])
            artifact.unlink()
            self.assertEqual(VERIFIER.verify_manifest(root, manifest)["failures"],
                             ["missing_or_unsafe:table.csv"])
            manifest.write_text(json.dumps({"../outside.csv": expected}))
            self.assertEqual(VERIFIER.verify_manifest(root, manifest)["failures"],
                             ["missing_or_unsafe:../outside.csv"])

    def test_empty_manifest_cannot_certify_a_package(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "checksums.json"
            manifest.write_text("{}")
            with self.assertRaises(ValueError):
                VERIFIER.verify_manifest(root, manifest)
