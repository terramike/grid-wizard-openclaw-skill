#!/usr/bin/env bash
set -euo pipefail

# Lint-like syntax check
python -m compileall -q src tests scripts

# Manifest/schema validation
python scripts/validate_manifest.py

# Test suite (smoke checks)
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py' -v
