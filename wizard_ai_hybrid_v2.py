# wizard_ai_hybrid_v2.py
#!/usr/bin/env python3
"""
Wizard AI Hybrid v2 – Dynamic Grid Optimizer + Dip Buyback (no UI changes)
(Safe env parsing version — handles blanks gracefully)

Design:
- Stateful helper you call ONCE per cycle from the orchestrator.
- Reads toggles from the environment each use (hot-reloads safely).
- Returns live tuners (step/offsets/levels_delta) before manage_grid_once().
- Optionally triggers a conservative IOC dip-buyback after run-ups.
"""

import os
import time
from collections import deque
from decimal import Decimal
from typing import Dict

from dotenv import load_dotenv
D = Decimal


# ============================================================
# Safe helpers for env parsing (inline — no extra file)
# ============================================================

def _env_int(v: str, default: int) -> int:
    try:
        if v is None or v.strip() == "":
            return default
        return int(float(v.strip()))
    except Exception:
        return default

def _env_dec(v: str, default: str) -> D:
    try:
        if v is None or v.strip() == "":
            return D(default)
        return D(v.strip())
    except Exception:
        return D(default)


# ============================================================
# Main class
# ============================================================

class AIHybridV2:
    _singleton = None

    @classmethod
    def get(cls) -> "AIHybridV2":
        if cls._singleton is None:
            cls._singleton = AIHybridV2()
        return cls._singleton

    def __init__(self):
        self.mids = deque(maxlen=200)     # rolling mids (used by AI_VOL_WINDOW slice)
        self.rolling_max_mid = None
        self.last_dip_buy_ts = 0.0
        self._last_env_reload = 0.0
        self._env_cache = {}

    # ---- Env helpers (hot-reload aware) ----
    def _env(self) -> Dict[str, str]:
        now = time.time()
        if now - self._last_env_reload > 5:
            load_dotenv(override=True)
            keys = [
                "AI_OPTIMIZER_ENABLE", "AI_VOL_WINDOW", "AI_VOL_HIGH_BPS", "AI_VOL_LOW_BPS",
                "AI_STEP_UP_MULT", "AI_STEP_DOWN_MULT", "AI_OFFSETS_DELTA_BPS", "AI_LEVELS_MAX_DELTA",
                "AI_DIP_BUYBACK_ENABLE", "AI_DIP_BB_TRIGGER_BPS", "AI_DIP_BB_SIZE_PCT",
                "AI_DIP_BB_SLIP_BPS", "AI_COOLDOWN_SEC",
                "SELL_TRANCHE_RLUSD", "MIN_NOTIONAL_RLUSD"
            ]
            self._env_cache = {k: (os.environ.get(k, "") or "").strip() for k in keys}

            # Fill sensible defaults
            defaults = {
                "AI_OPTIMIZER_ENABLE": "1",
                "AI_VOL_WINDOW": "20",
                "AI_VOL_HIGH_BPS": "60",
                "AI_VOL_LOW_BPS": "20",
                "AI_STEP_UP_MULT": "1.4",
                "AI_STEP_DOWN_MULT": "0.8",
                "AI_OFFSETS_DELTA_BPS": "10",
                "AI_LEVELS_MAX_DELTA": "1",
                "AI_DIP_BUYBACK_ENABLE": "1",
                "AI_DIP_BB_TRIGGER_BPS": "60",
                "AI_DIP_BB_SIZE_PCT": "30",
                "AI_DIP_BB_SLIP_BPS": "20",
                "AI_COOLDOWN_SEC": "300",
                "SELL_TRANCHE_RLUSD": os.environ.get("SELL_TRANCHE_RLUSD", "10"),
                "MIN_NOTIONAL_RLUSD": os.environ.get("MIN_NOTIONAL_RLUSD", "10"),
            }
            for k, v in defaults.items():
                if self._env_cache.get(k, "") == "":
                    self._env_cache[k] = v

            self._last_env_reload = now
        return self._env_cache

    # ---- Math helpers ----
    @staticmethod
    def _pct_diff(a: D, b: D) -> D:
        return D(0) if b == 0 else (a - b) / b

    def _compute_vol_bps(self, window: int) -> D:
        if len(self.mids) < max(3, window):
            return D(0)
        series = list(self.mids)[-window:]
        avg = sum(series) / D(len(series))
        if avg <= 0:
            return D(0)
        var = sum((x - avg) ** 2 for x in series) / D(len(series))
        stdev = var.sqrt() if var > 0 else D(0)
        return (stdev / avg) * D(10000)  # in bps

    # ---- Public API ----
    def update_and_get_tuners(self, mid: D) -> Dict[str, D]:
        """Compute volatility & tuning deltas/multipliers."""
        if mid and mid > 0:
            self.mids.append(D(mid))
            if self.rolling_max_mid is None or mid > self.rolling_max_mid:
                self.rolling_max_mid = D(mid)

        env = self._env()
        if env.get("AI_OPTIMIZER_ENABLE", "1") != "1":
            return {"step_mult": D(1), "buy_offset_bps_delta": D(0),
                    "sell_offset_bps_delta": D(0), "levels_delta": 0}

        window = max(5, _env_int(env.get("AI_VOL_WINDOW", ""), 20))
        vol_bps = self._compute_vol_bps(window)
        high = _env_dec(env.get("AI_VOL_HIGH_BPS", ""), "60")
        low = _env_dec(env.get("AI_VOL_LOW_BPS", ""), "20")
        step_up = _env_dec(env.get("AI_STEP_UP_MULT", ""), "1.4")
        step_dn = _env_dec(env.get("AI_STEP_DOWN_MULT", ""), "0.8")
        offs = _env_dec(env.get("AI_OFFSETS_DELTA_BPS", ""), "10")
        lvl_delta_max = _env_int(env.get("AI_LEVELS_MAX_DELTA", ""), 1)

        out = {"step_mult": D(1), "buy_offset_bps_delta": D(0),
               "sell_offset_bps_delta": D(0), "levels_delta": 0}

        # Three regimes: high-vol, low-vol, normal
        if vol_bps >= high:
            out["step_mult"] = step_up
            out["buy_offset_bps_delta"] = offs
            out["sell_offset_bps_delta"] = offs
            out["levels_delta"] = min(+lvl_delta_max, +1)
        elif vol_bps <= low:
            out["step_mult"] = step_dn
            out["buy_offset_bps_delta"] = -offs
            out["sell_offset_bps_delta"] = -offs
            out["levels_delta"] = max(-lvl_delta_max, -1)
        return out

    # ---- Dip-buyback logic ----
    def maybe_dip_buyback(self, client, wallet, issuer: str, mid: D,
                          rlusd_balance: D, tag: str, log) -> None:
        """If price retraces trigger_bps from max, fire small IOC buy."""
        env = self._env()
        if env.get("AI_DIP_BUYBACK_ENABLE", "1") != "1":
            return
        try:
            trigger_bps = _env_dec(env.get("AI_DIP_BB_TRIGGER_BPS", ""), "60")
            size_pct = _env_dec(env.get("AI_DIP_BB_SIZE_PCT", ""), "30") / D(100)
            slip_bps = _env_dec(env.get("AI_DIP_BB_SLIP_BPS", ""), "20")
            cooldown = _env_int(env.get("AI_COOLDOWN_SEC", ""), 300)
            min_notional = _env_dec(env.get("MIN_NOTIONAL_RLUSD", ""), "10")
            sell_tranche = _env_dec(env.get("SELL_TRANCHE_RLUSD", ""), "10")
        except Exception:
            return

        if mid is None or mid <= 0 or self.rolling_max_mid is None:
            return
        if time.time() - self.last_dip_buy_ts < cooldown:
            return

        drop_bps = (self.rolling_max_mid - mid) / self.rolling_max_mid * D(10000)
        if drop_bps < trigger_bps:
            return

        notional = (sell_tranche * size_pct).quantize(D("0.000001"))
        if notional < min_notional:
            notional = min_notional
        if rlusd_balance is not None and rlusd_balance < notional:
            if callable(log):
                log(f"[AI] Dip buyback skipped – insufficient RLUSD {rlusd_balance:.6f} < {notional:.6f}")
            return

        from wizard_rlusd_grid_v2 import market_buy_xrp
        slip_frac = slip_bps / D(10000)
        try:
            market_buy_xrp(client, wallet, notional, slip_frac, issuer, tag, log)
            self.last_dip_buy_ts = time.time()
            if callable(log):
                log(f"[AI] Dip buyback executed: {notional:.6f} RLUSD at ~{mid:.6f} (-{slip_bps}bps) | drop={drop_bps:.0f}bps from max {self.rolling_max_mid:.6f}")
        except Exception as e:
            if callable(log):
                log(f"[AI] Dip buyback error: {e}")
        self.rolling_max_mid = mid
