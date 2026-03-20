# Grid Wizard OpenClaw Skill

OpenClaw wrapper and safety layer for a Grid Wizard XRP/RLUSD trading engine.

## ⚠️ Financial Risk Warning
This repository contains trading software. Live trading can lose funds. Use at your own risk.

- Default mode is **dry-run**.
- Live actions require explicit enablement (`DRY_RUN=0` and `LIVE_TRADING_ENABLED=1`).
- Never commit real wallet seeds or private keys.

## Repository Layout

```text
grid-wizard-openclaw-skill/
  README.md
  LICENSE
  .gitignore
  .env.example
  requirements.txt
  wizard_core/
    wizard_orchestrator_v2.py
    wizard_rlusd_grid_v2.py
    wizard_metrics.py
    wizard_reserve_relief.py
  skill/
    manifest.json
    instructions.md
    skill_runner.py
    schemas.py
    safety.py
  examples/
    agent_usage.md
```

## Core Analysis (Current `wizard_core/`)

### Entrypoints
- `wizard_core.wizard_orchestrator_v2.GridWizardEngine` is the callable engine shim.
- `skill/skill_runner.py` dispatches OpenClaw-style actions to `GridWizardEngine` methods.

### Environment Variables
Discovered/used env variables:
- Required runtime: `XRPL_RPC_URL`, `XRPL_WS_URL`, `WALLET_ADDRESS`
- Live-required secrets: `WALLET_SEED`
- Safety/feature flags: `DRY_RUN`, `LIVE_TRADING_ENABLED`, `AUTO_CANCEL_ENABLED`, `RESERVE_RELIEF_ENABLED`, `DYN_TRANCHE_ENABLE`
- Optional strategy placeholders: `BASE_ASSET`, `QUOTE_ASSET`, `GRID_LEVELS`, `GRID_SPREAD_BPS`

### External Dependencies
- `python-dotenv` (expected for env loading)
- `xrpl-py` (for full XRP ledger account/offer wiring)

### Dangerous / Live Operations
Write/live actions are:
- `run_one_cycle`
- `cancel_stale_offers`

These are safety-gated and blocked unless live mode is intentionally enabled.

### Status / Introspection Operations
Read-only actions:
- `health_check`
- `show_config`
- `validate_env`
- `show_balances`
- `show_open_offers`
- `show_grid_status`
- `simulate_cycle`
- `dry_run_place_preview`

### What is wired now vs stubbed
- **Wired:** action dispatch, safety gates, config/env validation, dry-run simulation surface.
- **Partially stubbed:** real XRPL balance/offer fetching and live order placement/cancellation execution.

## OpenClaw Skill Actions

- `health_check`
- `show_config`
- `validate_env`
- `show_balances`
- `show_open_offers`
- `show_grid_status`
- `simulate_cycle`
- `run_one_cycle`
- `cancel_stale_offers`
- `dry_run_place_preview`

## Usage

```bash
python -m skill.skill_runner health_check
python -m skill.skill_runner validate_env
python -m skill.skill_runner simulate_cycle
```

## Assumed Manifest Design
`skill/manifest.json` uses a simple, extensible schema with:
- identity (`name`, `version`, `description`)
- runtime entrypoint
- safety policy
- action list

This can be evolved later to match stricter OpenClaw runtime contracts.

## Future Modularization Suggestions
1. Add a dedicated XRPL client adapter in `wizard_core/` for balances/offers and transaction submission.
2. Introduce structured strategy-state snapshots to power `show_grid_status` without parsing logs.
3. Separate read-path and write-path adapters for easier auditability and testing.
