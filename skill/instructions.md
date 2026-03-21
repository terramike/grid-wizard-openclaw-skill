# Grid Wizard Skill Instructions

## Safety-first operating policy
1. Start with read-only actions: `health_check`, `show_config`, `validate_env`, `show_balances`, `show_open_offers`, `show_grid_status`.
2. Summarize intended actions before execution.
3. Abort if `validate_env` reports missing required variables.
4. Keep public v1 focused on `health_check`, `show_config`, `validate_env`, `simulate_cycle`, and `dry_run_place_preview`.
5. Require explicit user confirmation before discussing any write/live action.
6. Keep `DRY_RUN=1` unless the user explicitly requests live mode and confirms risk.

## Read-only vs write/live actions
- **Read-only:** `health_check`, `show_config`, `validate_env`, `show_balances`, `show_open_offers`, `show_grid_status`, `simulate_cycle`, `dry_run_place_preview`
- **Write/live:** `run_one_cycle`, `cancel_stale_offers`

## Live-mode prerequisites
- `DRY_RUN=0`
- `LIVE_TRADING_ENABLED=1`
- Required secrets/config must be present.
- Never echo wallet seeds/private keys in output.
- Live-mode actions remain experimental and are not part of the public v1 contract.
