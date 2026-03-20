"""Manifest integrity smoke checks."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


MANIFEST_PATH = Path("manifest/skill_manifest.json")


class TestManifestIntegrity(unittest.TestCase):
    def test_manifest_file_exists(self) -> None:
        self.assertTrue(MANIFEST_PATH.exists())

    def test_manifest_contains_required_fields(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "grid-wizard-openclaw-skill")
        self.assertTrue(manifest["version"])
        self.assertTrue(manifest["entrypoint"].startswith("python -m"))
        self.assertTrue(manifest["description"])


if __name__ == "__main__":
    unittest.main()
