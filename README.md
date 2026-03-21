# Grid Wizard

Codex skill and Python backend for safely inspecting and simulating the Grid Wizard XRP/RLUSD trading wrapper.

## Financial Risk Warning

This repository contains trading software. Public v1 is for safe inspection and dry-run workflows only. Do not treat it as production-ready live trading software.

- Default mode is `DRY_RUN=1`
- Live-oriented actions remain experimental and are not part of the public v1 contract
- Never commit real wallet seeds or private keys

## What Ships in v1

Supported public workflows:

- `health_check`
- `show_config`
- `validate_env`
- `simulate_cycle`
- `dry_run_place_preview`

Experimental or non-release actions still exist in the backend for future work, but they are not part of the public promise:

- `show_balances`
- `show_open_offers`
- `show_grid_status`
- `run_one_cycle`
- `cancel_stale_offers`

## Repository Layout

```text
grid-wizard/
  SKILL.md
  README.md
  requirements.txt
  .env.example
  agents/
    openai.yaml
  references/
    backend.md
  skill/
    manifest.json
    instructions.md
    skill_runner.py
    schemas.py
    safety.py
  wizard_core/
    wizard_orchestrator_v2.py
    wizard_rlusd_grid_v2.py
    wizard_metrics.py
    wizard_reserve_relief.py
```

## Local Setup

1. Bootstrap the local environment:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

This script creates `.venv`, installs dependencies, and pins temporary files into a repo-local `.tmp` directory so Python bootstrap works even on machines where profile temp permissions are restrictive.

2. Copy `.env.example` to `.env` and fill in only the values you need for validation and dry-run workflows.

## Validate the Skill

Run the skill validator from the repository root using your local copy of the `skill-creator` helper:

```powershell
python path\to\quick_validate.py .
```

## Smoke Tests

Run these commands from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1
```

Expected safe behavior:

- `health_check` reports dry-run mode by default
- `show_config` shows non-secret runtime flags
- `validate_env` reports missing variables by name only
- `simulate_cycle` and `dry_run_place_preview` return preview-style outputs without placing orders

## Codex Invocation

Use the skill as `$grid-wizard`.

Example prompts:

- `Use $grid-wizard to check whether the trading setup is healthy and summarize the safe config.`
- `Use $grid-wizard to validate the environment and tell me what is missing for dry-run and live mode.`
- `Use $grid-wizard to simulate one cycle and summarize what would happen.`

## Install for Codex

Publish this folder as a public GitHub repository named `grid-wizard`. Users can then install the skill from that GitHub repo path using the existing skill installer flow.
