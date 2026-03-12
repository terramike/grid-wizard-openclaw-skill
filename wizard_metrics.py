#!/usr/bin/env python3
"""
The Grid Wizard Metrics v2 – Balance, Order, Pending, Cycle Logging
"""

import os
import time
from decimal import Decimal
from typing import Callable, List, Optional, Dict

D = Decimal

def log_balances_and_stats(address: str, balances: dict, orders: List[str], cycle_stats: Dict[str, int], log: Callable[[str], None]) -> None:
    log_path = os.path.join(os.path.dirname(os.environ.get("WIZARD_ENV_PATH", ".env")), "profits.log")

    # Initialize log file
    if not os.path.exists(log_path):
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | [State] Initialized profits.log\n")
        log(f"[State] Initialized profits.log")

    # Log balances, orders, stats
    bal_xrp = balances.get("spendable_xrp", 0)
    bal_rlusd = balances.get("rlusd", 0)
    total_xrp_equiv = balances.get("total_xrp_equiv", 0)
    orders_str = "; ".join(orders) if orders else "none"
    stats_str = f"placed={cycle_stats['placed']} skipped={cycle_stats['skipped']} (throttle={cycle_stats['throttle_skips']} pending={cycle_stats['pending_skips']}) cancelled={cycle_stats['cancelled']} pending_buy={cycle_stats['pending_buy']} pending_sell={cycle_stats['pending_sell']}"
    log_msg = f"[State] XRP={bal_xrp:.6f}, RLUSD={bal_rlusd:.6f}, Total XRP equiv={total_xrp_equiv:.6f}, Orders={orders_str}, Cycle={stats_str}"
    log(log_msg)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {log_msg}\n")