# Agent Usage Examples

## Check balances (read-only)
```text
Run `show_balances` and summarize available XRP/RLUSD balances. Do not place orders.
```

## Show grid state
```text
Run `show_grid_status` and explain the current grid posture and risk flags.
```

## Simulate one cycle
```text
Run `simulate_cycle` with current config and summarize what orders would be placed in dry-run.
```

## Intentionally enable live mode
```text
I explicitly confirm I want live trading. Validate env first, then set DRY_RUN=0 and LIVE_TRADING_ENABLED=1, and run `run_one_cycle`.
```

## Cancel stale offers safely
```text
Preview stale-offer cancellation first. Only execute cancellation if I confirm and live mode is explicitly enabled.
```
