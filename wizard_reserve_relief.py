#!/usr/bin/env python3
"""
The Grid Wizard Reserve Relief v2 – Prune Excess Offers to Free Reserves
"""

from decimal import Decimal
from typing import List, Dict, Callable

D = Decimal

from wizard_rlusd_grid_v2 import offer_side_vs_xrp, price_vs_xrp, cancel_offers_by_seq

def prune_reserve(client, wallet, issuer: str, mid: D, existing: List[dict], 
                  side_caps: Dict[str, int], grace_bps: D, 
                  max_per_cycle: int, strategy: str, tag: str, 
                  log: Callable[[str], None]) -> int:
    to_prune = []
    buys = [of for of in existing if offer_side_vs_xrp(of) == "buy"]
    sells = [of for of in existing if offer_side_vs_xrp(of) == "sell"]
    
    if len(buys) > side_caps.get("buy", 0):
        for of in buys:
            price = price_vs_xrp(of)
            if price is None: continue
            bps_diff = (mid - price) / mid * D(10000)
            if bps_diff > grace_bps:
                to_prune.append((of["seq"], bps_diff, "buy"))
    
    if len(sells) > side_caps.get("sell", 0):
        for of in sells:
            price = price_vs_xrp(of)
            if price is None: continue
            bps_diff = (price - mid) / mid * D(10000)
            if bps_diff > grace_bps:
                to_prune.append((of["seq"], bps_diff, "sell"))
    
    if not to_prune:
        return 0
    
    # Sort by strategy: farthest (highest BPS) or oldest (lowest seq)
    to_prune.sort(key=lambda x: x[1] if strategy == "farthest" else -x[0])
    to_prune = to_prune[:max_per_cycle]
    
    seqs = [seq for seq, _, _ in to_prune]
    cancel_offers_by_seq(client, wallet, seqs, tag, log)
    return len(seqs)