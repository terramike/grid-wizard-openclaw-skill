"""Validate the skill manifest structure for CI usage."""

from __future__ import annotations

import json
from pathlib import Path

REQUIRED_KEYS = {
    "name": str,
    "version": str,
    "entrypoint": str,
    "description": str,
}


def validate_manifest(path: Path) -> None:
    raw = json.loads(path.read_text(encoding="utf-8"))

    for key, expected_type in REQUIRED_KEYS.items():
        if key not in raw:
            raise ValueError(f"Missing required key: {key}")
        if not isinstance(raw[key], expected_type):
            raise TypeError(f"Key '{key}' must be of type {expected_type.__name__}")


if __name__ == "__main__":
    validate_manifest(Path("manifest/skill_manifest.json"))
    print("Manifest validation passed.")
