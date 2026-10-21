"""Additional release tests; all 37 inherited test files are kept byte-identical."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_complete_manifest_original_implementation_and_exclusion_boundary():
    spec = importlib.util.spec_from_file_location("public_snapshot_verifier", ROOT / "publication_release/verify_snapshot.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.verify()
    assert result["passed"]
    assert result["excluded_originals_present"] == 0


def test_public_fingerprint_scope_is_explicit_and_preserves_original_hashes():
    origin = json.loads((ROOT / "publication_release/SNAPSHOT_PROVENANCE.json").read_text())
    original = json.loads((ROOT / "results/final_publication/provenance/research_original_101_checksums.json").read_text())
    retained = json.loads((ROOT / "results/final_publication/provenance/checksums.json").read_text())
    assert len(original) == 101
    assert len(retained) == 85
    assert retained == origin["preserved_publication_hashes"]
    assert {p: original[p] for p in retained} == retained
    assert set(original) - set(retained) == set(origin["original_publication_omissions"])


def test_prepared_mit_attribution_is_exact_without_university_approval_claim():
    license_text = (ROOT / "LICENSE").read_text()
    assert license_text.startswith("MIT License\n\nCopyright (c) 2026 T2DM Project Contributors\n")
    assert "MIT Manipal" not in license_text
    assert "Permission is hereby granted, free of charge" in license_text
    assert "THE SOFTWARE IS PROVIDED" in license_text
