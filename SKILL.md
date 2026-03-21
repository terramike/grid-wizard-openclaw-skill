---
name: grid-wizard
description: Safely inspect, validate, simulate, and summarize the Grid Wizard XRP/RLUSD trading wrapper from this repository. Use when Codex needs to check trading health, review non-secret config, validate environment variables, simulate one cycle, or preview dry-run behavior without exposing secrets. Treat live or write-oriented actions as experimental and out of scope for the public v1 release.
---

# Grid Wizard

Operate the Grid Wizard trading wrapper through the Python backend bundled in this repository. Treat this skill as an operator guide for safe inspection and dry-run workflows. Public v1 is intentionally limited to non-destructive health, config, validation, simulation, and preview tasks.

## Backend

Use the backend that ships in this repo.

- Main command surface: `python -m skill.skill_runner <action>`
- Backend entrypoints:
  - `skill/skill_runner.py`
  - `wizard_core/wizard_orchestrator_v2.py`
- Run commands from the repository root so the `skill` package resolves correctly.
- If no usable Python interpreter exists, report that the environment is not ready instead of improvising around it.

## Safe Workflow

Follow this sequence unless the user explicitly narrows the request:

1. Confirm the task is read-only or dry-run by default.
2. Start with one or more read-only actions:
   - `health_check`
   - `show_config`
   - `validate_env`
   - `simulate_cycle`
   - `dry_run_place_preview`
3. Summarize results in plain language and call out any stubbed backend areas.
4. Before any risky step, run `validate_env` or explain why it cannot run.
5. Treat live or write-oriented actions as experimental and out of scope for the public v1 release.
6. Never reveal secret values even if they exist in environment files.

## Actions

Prefer these actions for normal operation:

- `health_check`: confirm the wrapper is reachable and whether it is in dry-run or live-enabled mode
- `show_config`: summarize non-secret runtime flags
- `validate_env`: identify missing required and live-required variables
- `simulate_cycle`: run the safe simulation surface
- `dry_run_place_preview`: preview dry-run order placement output

Treat these actions as experimental or non-release:

- `show_balances`: partial/stubbed backend adapter
- `show_open_offers`: partial/stubbed backend adapter
- `show_grid_status`: partial/stubbed backend adapter
- `run_one_cycle`: live-gated and currently stubbed after safety checks
- `cancel_stale_offers`: dry-run preview exists; live cancel wiring is still partial

Do not advertise the experimental actions as part of the public v1 promise. If a user asks about them, explain that they are incomplete and may return placeholder data instead of live XRPL results.

## Safety Policy

Treat `run_one_cycle` and live cancellation as experimental write actions.

- Keep `DRY_RUN=1` unless the user explicitly asks for live mode.
- Require `LIVE_TRADING_ENABLED=1` and a successful `validate_env` outcome before even discussing a live action.
- Public v1 should stop at guidance and previews rather than executing live commands.
- Never print `WALLET_SEED`, private keys, or full secret material in logs or summaries.
- If safety flags do not permit the action, stop and explain the block rather than trying to bypass it.

## Command Execution Guidance

When you need to invoke the backend, use the repository root as the working directory. Try the most direct interpreter available in the environment and do not guess secret values.

Typical command shape:

```powershell
python -m skill.skill_runner health_check
python -m skill.skill_runner validate_env
python -m skill.skill_runner simulate_cycle
python -m skill.skill_runner dry_run_place_preview
```

If `python` is unavailable but the repo has a working virtual environment, use that interpreter. If the virtual environment is broken or points to a missing base interpreter, stop and report the environment problem clearly.

## Output Style

- Summarize trading state and risk flags clearly.
- Separate confirmed facts from limitations.
- Call out missing env vars by name, but never expose their values.
- If an action is blocked by dry-run or live-mode policy, say so explicitly.
- If a command cannot run because Python is unavailable, report that as an environment blocker rather than a trading-system failure.

## Extra Reference

For action names, required variables, and backend limitations, read [references/backend.md](./references/backend.md) as needed.
