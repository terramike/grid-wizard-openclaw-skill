"""Safety gates for Grid Wizard actions."""

from __future__ import annotations

from typing import Dict

WRITE_ACTIONS = {"run_one_cycle", "cancel_stale_offers"}


def is_write_action(action: str) -> bool:
    return action in WRITE_ACTIONS


def enforce_safety(action: str, config: Dict[str, object]) -> Dict[str, object]:
    dry_run = bool(config.get("dry_run", True))
    live_enabled = bool(config.get("live_trading_enabled", False))

    if action in WRITE_ACTIONS and (dry_run or not live_enabled):
        return {
            "allowed": False,
            "reason": "Write/live action blocked by safe defaults. Use DRY_RUN=0 and LIVE_TRADING_ENABLED=1.",
        }

    return {"allowed": True}
