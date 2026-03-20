"""Local entrypoint for running smoke checks against the skill manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_KEYS = ("name", "version", "entrypoint", "description")


def load_manifest(manifest_path: Path) -> dict:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = [key for key in REQUIRED_KEYS if key not in data]
    if missing:
        missing_keys = ", ".join(missing)
        raise ValueError(f"Manifest is missing required keys: {missing_keys}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Run local Grid Wizard skill smoke check")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("manifest/skill_manifest.json"),
        help="Path to the skill manifest JSON file.",
    )
    args = parser.parse_args()

    manifest = load_manifest(args.manifest)
    print(
        "Skill manifest loaded successfully:\n"
        f"- name: {manifest['name']}\n"
        f"- version: {manifest['version']}\n"
        f"- entrypoint: {manifest['entrypoint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
