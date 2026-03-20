---
name: grid-wizard-openclaw-skill
description: Operate and tune the Grid Wizard OpenClaw RLUSD⇄XRP grid-trading skill through environment configuration and control APIs. Use when setting up the bot, validating installation, running the first API-driven flow, adjusting risk caps/queues, or enabling optional Dynamic Grid Optimizer and DipsCount behaviors.
---

# Grid Wizard OpenClaw Skill

Configure and run the RLUSD⇄XRP grid engine in a safe, verification-first order.

## 1) Prepare environment

1. Copy `.env.example` to `.env`.
2. Set API credentials, wallet settings, and risk caps before starting the engine.
3. Keep `DRY_RUN=true` for first boot and verification.

## 2) Startup checklist

1. Start the engine service.
2. Wait for health endpoint to report `ok`.
3. Confirm market connectivity and account balance checks pass.
4. Confirm risk guards are loaded from `.env`.

## 3) First API-only flow

Run the minimal control sequence:

1. `GET /health` to validate process status.
2. `POST /control/start` to arm the strategy.
3. `GET /state` to verify grid levels, pending queues, and caps.
4. `POST /control/pause` to stop safely.

Use this sequence for smoke tests after every deployment.

## 4) Safety defaults

- Enforce max open orders and pending queue limits.
- Keep auto-cancel distance enabled when latency increases.
- Use conservative notional and ladder spacing until behavior is stable.
- Enable optimizer and dip-buyback only after baseline behavior is verified.

## 5) Operator guidance

- Treat environment values as the source of truth for risk.
- Change one parameter group at a time (grid, risk, AI layer).
- Record before/after values and observed fill behavior.
- Re-run the first API-only flow after every configuration update.
