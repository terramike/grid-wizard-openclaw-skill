# Grid Wizard Backend Reference

Backend root: repository root

## Entrypoints

- Runner: `skill/skill_runner.py`
- Engine shim: `wizard_core/wizard_orchestrator_v2.py`
- Current command pattern: `python -m skill.skill_runner <action>`

## Action Surface

Read-first actions:

- `health_check`
- `show_config`
- `validate_env`
- `simulate_cycle`
- `dry_run_place_preview`

Experimental or incomplete actions:

- `show_balances`
- `show_open_offers`
- `show_grid_status`
- `run_one_cycle`
- `cancel_stale_offers`

## Environment Variables

Required runtime variables:

- `XRPL_RPC_URL`
- `XRPL_WS_URL`
- `WALLET_ADDRESS`

Live-required variables:

- `WALLET_SEED`

Safety and behavior flags:

- `DRY_RUN`
- `LIVE_TRADING_ENABLED`
- `AUTO_CANCEL_ENABLED`
- `RESERVE_RELIEF_ENABLED`
- `DYN_TRANCHE_ENABLE`

Optional strategy placeholders:

- `BASE_ASSET`
- `QUOTE_ASSET`
- `GRID_LEVELS`
- `GRID_SPREAD_BPS`

## Current Safety Behavior

- Default mode is dry-run.
- Write or live behavior is blocked unless `DRY_RUN=0` and `LIVE_TRADING_ENABLED=1`.
- `validate_env` reports missing runtime variables and whether live mode is allowed.
- `run_one_cycle` remains stubbed even after safety checks pass.
- `cancel_stale_offers` can preview in dry-run mode, but live cancellation is still not fully wired.
- Public v1 should advertise only `health_check`, `show_config`, `validate_env`, `simulate_cycle`, and `dry_run_place_preview`.

## Operator Notes

- Never expose `WALLET_SEED` or private-key material.
- Treat missing or broken Python as an environment issue, not as a backend health result.
- Clearly label placeholder outputs so users do not mistake them for live XRPL state.
