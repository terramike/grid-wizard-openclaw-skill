"""Grid Wizard orchestrator adapter layer.

This module is intentionally thin: it provides import-friendly callables for the
OpenClaw skill without rewriting strategy internals.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any, Dict, List


REQUIRED_ENV_VARS = [
    "XRPL_RPC_URL",
    "XRPL_WS_URL",
    "WALLET_ADDRESS",
]

LIVE_REQUIRED_ENV_VARS = [
    "WALLET_SEED",
]


@dataclass
class WizardConfig:
    dry_run: bool = True
    live_trading_enabled: bool = False
    auto_cancel_enabled: bool = True
    reserve_relief_enabled: bool = False
    dyn_tranche_enable: bool = False

    @classmethod
    def from_env(cls) -> "WizardConfig":
        return cls(
            dry_run=os.getenv("DRY_RUN", "1") == "1",
            live_trading_enabled=os.getenv("LIVE_TRADING_ENABLED", "0") == "1",
            auto_cancel_enabled=os.getenv("AUTO_CANCEL_ENABLED", "1") == "1",
            reserve_relief_enabled=os.getenv("RESERVE_RELIEF_ENABLED", "0") == "1",
            dyn_tranche_enable=os.getenv("DYN_TRANCHE_ENABLE", "0") == "1",
        )


class GridWizardEngine:
    """Import-friendly orchestration shim for the original Grid Wizard engine files."""

    def __init__(self) -> None:
        self.config = WizardConfig.from_env()

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "dry_run": self.config.dry_run,
            "live_trading_enabled": self.config.live_trading_enabled,
            "engine": "grid-wizard",
        }

    def show_config(self) -> Dict[str, Any]:
        return asdict(self.config)

    def validate_env(self) -> Dict[str, Any]:
        missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
        missing_live = [k for k in LIVE_REQUIRED_ENV_VARS if not os.getenv(k)]
        return {
            "ok": not missing,
            "missing_required": missing,
            "missing_live_required": missing_live,
            "live_mode_allowed": self.config.live_trading_enabled and not missing_live,
        }

    def show_balances(self) -> Dict[str, Any]:
        # Placeholder until full XRPL account fetch wiring is added.
        return {
            "status": "stub",
            "message": "Balance adapter exists but is not yet connected to XRPL account queries.",
            "wallet_address": os.getenv("WALLET_ADDRESS", ""),
        }

    def show_open_offers(self) -> Dict[str, Any]:
        return {
            "status": "stub",
            "message": "Open-offer adapter exists but is not yet connected to orderbook queries.",
            "offers": [],
        }

    def show_grid_status(self) -> Dict[str, Any]:
        return {
            "status": "stub",
            "message": "Grid-status adapter exists but strategy state introspection is not yet wired.",
        }

    def simulate_cycle(self) -> Dict[str, Any]:
        # Read-only simulation entrypoint.
        return {
            "status": "ok",
            "mode": "simulation",
            "dry_run": True,
            "actions": [],
        }

    def run_one_cycle(self) -> Dict[str, Any]:
        if self.config.dry_run or not self.config.live_trading_enabled:
            return {
                "status": "blocked",
                "reason": "Live cycle blocked. Set DRY_RUN=0 and LIVE_TRADING_ENABLED=1.",
            }

        env_check = self.validate_env()
        if not env_check["live_mode_allowed"]:
            return {
                "status": "blocked",
                "reason": "Missing live-trading secrets/config.",
                "details": env_check,
            }

        return {
            "status": "stub",
            "message": "Live cycle adapter exists; strategy execution wiring pending.",
        }

    def cancel_stale_offers(self) -> Dict[str, Any]:
        if self.config.dry_run:
            return {
                "status": "preview",
                "message": "Dry-run mode active; no offers cancelled.",
                "candidates": [],
            }
        return {
            "status": "stub",
            "message": "Cancel adapter exists; core cancel wiring pending.",
        }

    def dry_run_place_preview(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "mode": "dry_run",
            "preview_orders": [],
        }


def available_actions() -> List[str]:
    return [
        "health_check",
        "show_config",
        "validate_env",
        "show_balances",
        "show_open_offers",
        "show_grid_status",
        "simulate_cycle",
        "run_one_cycle",
        "cancel_stale_offers",
        "dry_run_place_preview",
    ]
