"""Core grid strategy placeholder module.

Keep this filename stable for migration from original Grid Wizard sources.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class GridLevel:
    price: float
    side: str
    amount: float


def build_grid_preview(mid_price: float, spread_bps: float = 20.0, levels: int = 3) -> List[GridLevel]:
    """Return a deterministic preview of bid/ask levels for dry-run visibility."""
    step = mid_price * (spread_bps / 10_000)
    out: List[GridLevel] = []
    for n in range(1, levels + 1):
        out.append(GridLevel(price=mid_price - (step * n), side="buy", amount=10.0))
        out.append(GridLevel(price=mid_price + (step * n), side="sell", amount=10.0))
    return out


def preview_as_dict(mid_price: float) -> Dict[str, object]:
    return {
        "mid_price": mid_price,
        "levels": [lvl.__dict__ for lvl in build_grid_preview(mid_price)],
    }
