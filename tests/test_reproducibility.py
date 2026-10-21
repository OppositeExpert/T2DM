from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import tomllib
import unittest
from importlib import metadata
from urllib.parse import unquote, urlparse

import yaml


ROOT = Path(__file__).resolve().parents[1]


class ReproducibilityTests(unittest.TestCase):
    def test_pidd_openml_reconstruction_is_byte_deterministic(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "acquire_data", ROOT / "scripts/acquire_data.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        source = (
            '"preg","plas","pres","skin","insu","mass","pedi","age","class"\n'
            "3,78,50,32,88,31,0.248,26,tested_positive\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "openml.csv"
            output_path = Path(directory) / "pidd.csv"
            input_path.write_text(source, encoding="utf-8")
            module._write_pidd(input_path, output_path)
            self.assertEqual(
                output_path.read_bytes(), b"3,78,50,32,88,31.0,0.248,26,1"
            )

    def test_data_source_manifest_covers_every_dataset_with_sha256(self) -> None:
        sources = yaml.safe_load(
            (ROOT / "config/data_sources.yaml").read_text(encoding="utf-8")
        )["datasets"]
        datasets = yaml.safe_load(
            (ROOT / "config/datasets.yaml").read_text(encoding="utf-8")
        )["datasets"]
        self.assertEqual(set(sources), set(datasets))
        for name, source in sources.items():
            self.assertEqual(source["expected_path"], datasets[name]["raw_path"])
            self.assertRegex(source["expected_sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(source["source_page"].startswith("https://"))
            path = ROOT / source["expected_path"]
            if path.exists():
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                        digest.update(chunk)
                actual = digest.hexdigest()
                self.assertEqual(actual, source["expected_sha256"])

    def test_locked_environment_contains_every_direct_dependency(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        direct = {
            re.split(r"[<=>!~]", value, maxsplit=1)[0].lower().replace("_", "-")
            for value in project["project"]["dependencies"]
        }
        locked = {
            line.split("==", 1)[0].lower().replace("_", "-")
            for line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines()
            if "==" in line and not line.lstrip().startswith("#")
        }
        self.assertFalse(direct - locked)
        self.assertIn("setuptools", locked)
        self.assertIn("wheel", locked)

    def test_editable_install_points_to_this_repository(self) -> None:
        distribution = metadata.distribution("diabetes-publication-pipeline")
        payload = json.loads(distribution.read_text("direct_url.json"))
        project_path = Path(unquote(urlparse(payload["url"]).path)).resolve()
        self.assertEqual(project_path, ROOT.resolve())

    def test_authoritative_registry_preserves_final_internal_claim_boundary(self) -> None:
        payload = yaml.safe_load(
            (ROOT / "config/authoritative_studies.yaml").read_text(encoding="utf-8")
        )
        self.assertFalse(payload["independent_holdout_claim_allowed"])
        for declaration in payload["studies"].values():
            self.assertEqual(
                declaration["evidence_tier"], "final_internal_validation"
            )
            self.assertIn("run_final_internal_validation.py", declaration["command"])
            self.assertEqual(declaration["evaluation_role"], "locked_internal_validation")

    def test_tracked_registry_matches_authoritative_declarations(self) -> None:
        declarations = yaml.safe_load(
            (ROOT / "config/authoritative_studies.yaml").read_text(encoding="utf-8")
        )["studies"]
        registry = json.loads(
            (ROOT / "evidence/study_registry.json").read_text(encoding="utf-8")
        )
        self.assertEqual(set(registry["studies"]), set(declarations))
        for dataset, declaration in declarations.items():
            study = registry["studies"][dataset]
            self.assertEqual(study["study_id"], declaration["study_id"])
            self.assertEqual(study["evidence_tier"], "final_internal_validation")
            self.assertTrue(study["eligible_for_final_internal_validation_claims"])
            self.assertFalse(study["independent_holdout_claim_allowed"])
            self.assertIsInstance(study["test_access"], str)
            self.assertTrue(study["test_access"])
            self.assertRegex(study["raw_data_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(study["source_tree_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
