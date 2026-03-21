"""Metrics helpers for skill-level status reporting."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def minimal_metrics_snapshot() -> Dict[str, object]:
    return {
        "timestamp_utc": now_utc_iso(),
        "pnl": None,
        "active_offers": None,
        "notes": "Metrics wiring pending core integration.",
    }
