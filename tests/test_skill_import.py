"""Basic import and CLI smoke checks for the skill package."""

from __future__ import annotations

import unittest
from pathlib import Path

from grid_wizard_openclaw_skill import __version__
from grid_wizard_openclaw_skill.__main__ import load_manifest


class TestSkillImport(unittest.TestCase):
    def test_package_imports(self) -> None:
        self.assertEqual(__version__, "0.1.0")

    def test_load_manifest_smoke(self) -> None:
        manifest = load_manifest(Path("manifest/skill_manifest.json"))
        self.assertEqual(manifest["name"], "grid-wizard-openclaw-skill")


if __name__ == "__main__":
    unittest.main()
