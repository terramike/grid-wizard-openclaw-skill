# Grid Wizard OpenClaw Skill

## Purpose
This skill provides a lightweight, reusable entrypoint for bootstrapping Grid Wizard OpenClaw integrations.

## What this module includes
- A Python package (`grid_wizard_openclaw_skill`)
- A module entrypoint (`python -m grid_wizard_openclaw_skill`)
- A simple manifest with dependency metadata

## Usage
```bash
python -m grid_wizard_openclaw_skill --help
python -m grid_wizard_openclaw_skill --dry-run
```

## Notes
- The default behavior is non-destructive and prints startup diagnostics.
- Extend `grid_wizard_openclaw_skill/entrypoint.py` to wire real trading logic.
