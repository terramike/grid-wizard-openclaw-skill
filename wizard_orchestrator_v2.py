#!/usr/bin/env python3
"""
The Grid Wizard Orchestrator v2 – Runner + Tk UI + Env Hot-Reload + Metrics Hooks
(With AI Hybrid v2: Dynamic Grid Optimizer + "DipsCount" Dip Buyback)

Notes:
- New UI fields (all hot-reloadable):
  * AI_OPTIMIZER_ENABLE
  * AI_VOL_WINDOW
  * AI_VOL_HIGH_BPS
  * AI_VOL_LOW_BPS
  * AI_STEP_UP_MULT
  * AI_STEP_DOWN_MULT
  * AI_OFFSETS_DELTA_BPS
  * AI_LEVELS_MAX_DELTA
  * AI_DIPSCOUNT_ENABLE          <-- user-facing toggle (inside joke)
  * AI_DIP_BB_TRIGGER_BPS
  * AI_DIP_BB_SIZE_PCT
  * AI_DIP_BB_SLIP_BPS
  * AI_COOLDOWN_SEC

- ENV bridge:
  We mirror AI_DIPSCOUNT_ENABLE -> AI_DIP_BUYBACK_ENABLE so that wizard_ai_hybrid_v2.py
  works unmodified.
"""

import argparse
import os
import sys
import time
from decimal import Decimal
from typing import Optional
from dotenv import load_dotenv, find_dotenv
import tkinter as tk
from tkinter import ttk, scrolledtext
from threading import Thread, Event

# XRPL helper for rendering order amounts in logs
from xrpl.utils import drops_to_xrp

D = Decimal

from wizard_rlusd_grid_v2 import (
    manage_grid_once, load_wallet_from_env, connect_clients, healthy_client,
    get_balance_xrp, get_iou_balance, get_reserves_xrp, get_account_objects_count, fetch_orderbook_prices
)
from wizard_metrics import log_balances_and_stats
from wizard_ai_hybrid_v2 import AIHybridV2

# -------------------------
# Environment loader (+defaults)
# -------------------------
def load_env():
    load_dotenv(override=True)
    # Allowed keys (both core + AI)
    allowed = {
        "CLASSIC_ADDRESS", "PRIVATE_KEY_HEX", "KEY_ALGO",
        "RLUSD_ISSUER", "RLUSD_CURRENCY_CODE",
        "XRPL_RPC_PRIMARY", "XRPL_RPC_FALLBACK",
        "MAX_OPEN_BUYS", "MAX_OPEN_SELLS",
        "BUY_OFFSET_BPS", "SELL_OFFSET_BPS",
        "STEP_PCT", "BUY_TRANCHE_RLUSD", "SELL_TRANCHE_RLUSD",
        "MIN_NOTIONAL_RLUSD", "SAFETY_BUFFER_XRP",
        "GLOBAL_SL_RLUSD", "SL_DISCOUNT_BPS",
        "INTERVAL", "LEVELS",
        "AUTO_CANCEL_ENABLED", "AUTO_CANCEL_BUY_BPS_FROM_MID", "AUTO_CANCEL_SELL_BPS_FROM_MID",
        "AUTO_CANCEL_MAX_PER_CYCLE", "AUTO_CANCEL_STRATEGY",
        "RESERVE_RELIEF_ENABLED", "RESERVE_RELIEF_BUY_CAP", "RESERVE_RELIEF_SELL_CAP",
        "RESERVE_RELIEF_MAX_PER_CYCLE", "RESERVE_RELIEF_GRACE_BPS", "RESERVE_RELIEF_STRATEGY",
        "PENDING_TTL_SEC", "BUY_THROTTLE_SEC", "SELL_THROTTLE_SEC",
        "PRICE_FETCH_RETRIES", "ENV_RELOAD_EVERY_SEC",
        "LICENSE_NFT_ISSUER", "WIZARD_ENV_PATH",

        # --- AI Hybrid v2 (Optimizer + DipsCount Buyback) ---
        "AI_OPTIMIZER_ENABLE",
        "AI_VOL_WINDOW",
        "AI_VOL_HIGH_BPS",
        "AI_VOL_LOW_BPS",
        "AI_STEP_UP_MULT",
        "AI_STEP_DOWN_MULT",
        "AI_OFFSETS_DELTA_BPS",
        "AI_LEVELS_MAX_DELTA",
        "AI_DIPSCOUNT_ENABLE",     # user-facing
        "AI_DIP_BB_TRIGGER_BPS",
        "AI_DIP_BB_SIZE_PCT",
        "AI_DIP_BB_SLIP_BPS",
        "AI_COOLDOWN_SEC",
    }

    env = {k: v.strip() for k, v in os.environ.items() if k in allowed}

    # Core defaults
    env.setdefault("AUTO_CANCEL_ENABLED", "1")
    env.setdefault("RESERVE_RELIEF_ENABLED", "0")
    env.setdefault("SELL_TRANCHE_RLUSD", "10")
    env.setdefault("AUTO_CANCEL_MAX_PER_CYCLE", "1")
    env.setdefault("AUTO_CANCEL_STRATEGY", "farthest")
    env.setdefault("RESERVE_RELIEF_MAX_PER_CYCLE", "3")
    env.setdefault("RESERVE_RELIEF_GRACE_BPS", "8")
    env.setdefault("RESERVE_RELIEF_STRATEGY", "farthest")
    env.setdefault("PENDING_TTL_SEC", "120")
    env.setdefault("BUY_THROTTLE_SEC", "10")
    env.setdefault("SELL_THROTTLE_SEC", "10")
    env.setdefault("PRICE_FETCH_RETRIES", "3")

    # AI defaults
    env.setdefault("AI_OPTIMIZER_ENABLE", "1")
    env.setdefault("AI_VOL_WINDOW", "20")
    env.setdefault("AI_VOL_HIGH_BPS", "60")
    env.setdefault("AI_VOL_LOW_BPS", "20")
    env.setdefault("AI_STEP_UP_MULT", "1.4")
    env.setdefault("AI_STEP_DOWN_MULT", "0.8")
    env.setdefault("AI_OFFSETS_DELTA_BPS", "10")
    env.setdefault("AI_LEVELS_MAX_DELTA", "1")

    env.setdefault("AI_DIPSCOUNT_ENABLE", "1")      # user-facing toggle
    env.setdefault("AI_DIP_BB_TRIGGER_BPS", "60")
    env.setdefault("AI_DIP_BB_SIZE_PCT", "30")
    env.setdefault("AI_DIP_BB_SLIP_BPS", "20")
    env.setdefault("AI_COOLDOWN_SEC", "300")

    return env

# -------------------------
# UI
# -------------------------
class UI:
    def __init__(self, stop_event):
        self.root = tk.Tk()
        self.root.title("The Grid Wizard v2")
        self.root.configure(bg="black")

        # Size: 80% of screen width, fixed height
        screen_width = self.root.winfo_screenwidth()
        window_width = int(screen_width * 0.8)
        window_height = 600
        self.root.geometry(f"{window_width}x{window_height}")

        self.stop_event = stop_event
        self.clients = connect_clients()
        self.wallet = load_wallet_from_env()
        self.issuer = os.environ.get("RLUSD_ISSUER", "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De")
        self.tag = "WIZARD"

        # Dark theme
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TFrame", background="black")
        style.configure("TLabel", background="black", foreground="white")
        style.configure("TEntry", fieldbackground="black", foreground="white", insertcolor="white")
        style.map("TEntry", background=[('focus', 'black')], foreground=[('focus', 'white')])
        style.configure("Black.TFrame", background="black")
        style.configure("Horizontal.TPanedWindow", background="black")
        style.configure("Vertical.TPanedWindow", background="black")

        # Tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Grid Control Tab
        grid_tab = ttk.Frame(self.notebook)
        self.notebook.add(grid_tab, text="Grid Control")

        paned = ttk.PanedWindow(grid_tab, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Log (top)
        log_frame = ttk.Frame(paned)
        paned.add(log_frame, weight=3)
        self.log = scrolledtext.ScrolledText(log_frame, bg="black", fg="white", font=("Courier", 10), height=10)
        self.log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Lower split (settings left, balances right)
        lower_frame = ttk.Frame(paned)
        paned.add(lower_frame, weight=1)

        lower_paned = ttk.PanedWindow(lower_frame, orient=tk.HORIZONTAL)
        lower_paned.pack(fill=tk.BOTH, expand=True)

        # Settings (scrollable)
        settings_outer_frame = ttk.Frame(lower_paned)
        lower_paned.add(settings_outer_frame, weight=3)

        self.settings_canvas = tk.Canvas(settings_outer_frame, bg="black")
        scrollbar = ttk.Scrollbar(settings_outer_frame, orient="vertical", command=self.settings_canvas.yview)
        self.settings_frame = ttk.Frame(self.settings_canvas)

        self.settings_frame.bind(
            "<Configure>",
            lambda e: self.settings_canvas.configure(scrollregion=self.settings_canvas.bbox("all"))
        )

        self.settings_canvas.create_window((0, 0), window=self.settings_frame, anchor="nw")
        self.settings_canvas.configure(yscrollcommand=scrollbar.set)
        self.settings_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.entries = {}

        # Base settings
        base_labels = [
            "MAX_OPEN_BUYS", "MAX_OPEN_SELLS", "BUY_OFFSET_BPS", "SELL_OFFSET_BPS",
            "STEP_PCT", "BUY_TRANCHE_RLUSD", "SELL_TRANCHE_RLUSD", "GLOBAL_SL_RLUSD",
            "SL_DISCOUNT_BPS", "INTERVAL", "LEVELS", "AUTO_CANCEL_BUY_BPS_FROM_MID",
            "AUTO_CANCEL_SELL_BPS_FROM_MID", "AUTO_CANCEL_MAX_PER_CYCLE", "AUTO_CANCEL_STRATEGY",
            "AUTO_CANCEL_ENABLED", "RESERVE_RELIEF_ENABLED", "RESERVE_RELIEF_BUY_CAP",
            "RESERVE_RELIEF_SELL_CAP", "RESERVE_RELIEF_MAX_PER_CYCLE", "RESERVE_RELIEF_GRACE_BPS",
            "RESERVE_RELIEF_STRATEGY", "PENDING_TTL_SEC", "SAFETY_BUFFER_XRP", "MIN_NOTIONAL_RLUSD"
        ]

        # AI settings (new in UI)
        ai_labels = [
            "AI_OPTIMIZER_ENABLE",
            "AI_VOL_WINDOW",
            "AI_VOL_HIGH_BPS",
            "AI_VOL_LOW_BPS",
            "AI_STEP_UP_MULT",
            "AI_STEP_DOWN_MULT",
            "AI_OFFSETS_DELTA_BPS",
            "AI_LEVELS_MAX_DELTA",
            "AI_DIPSCOUNT_ENABLE",
            "AI_DIP_BB_TRIGGER_BPS",
            "AI_DIP_BB_SIZE_PCT",
            "AI_DIP_BB_SLIP_BPS",
            "AI_COOLDOWN_SEC",
        ]

        labels = base_labels + ai_labels

        for i, lbl in enumerate(labels):
            ttk.Label(self.settings_frame, text=lbl).grid(row=i, column=0, padx=5, pady=3, sticky="e")
            e = ttk.Entry(self.settings_frame, width=20)
            e.grid(row=i, column=1, padx=5, pady=3)
            self.entries[lbl] = e

        # Save button
        save_button = ttk.Button(self.settings_frame, text="Save Settings", command=self.save)
        save_button.grid(row=len(labels), column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Balances (right)
        balance_frame = ttk.Frame(lower_paned, style="Black.TFrame")
        lower_paned.add(balance_frame, weight=1)
        self.xrp_grand_total_label = ttk.Label(balance_frame, text="XRP Grand Total: Calculating...")
        self.xrp_grand_total_label.pack(pady=5)
        self.total_xrp_label = ttk.Label(balance_frame, text="Total XRP: Calculating...")
        self.total_xrp_label.pack(pady=5)
        self.xrp_reserve_label = ttk.Label(balance_frame, text="Reserved XRP: Calculating...")
        self.xrp_reserve_label.pack(pady=5)
        self.spendable_xrp_label = ttk.Label(balance_frame, text="Spendable XRP: Calculating...")
        self.spendable_xrp_label.pack(pady=5)
        self.rlusd_balance_label = ttk.Label(balance_frame, text="RLUSD Balance: Calculating...")
        self.rlusd_balance_label.pack(pady=5)

        # Manual Purchase Tab
        manual_tab = ttk.Frame(self.notebook)
        self.notebook.add(manual_tab, text="Manual Purchase")

        ttk.Label(manual_tab, text="Buy Currency:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.buy_currency = ttk.Combobox(manual_tab, values=["RLUSD", "XRP"], width=20)
        self.buy_currency.grid(row=0, column=1, padx=5, pady=5)
        self.buy_currency.set("RLUSD")

        ttk.Label(manual_tab, text="Amount:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.amount_entry = ttk.Entry(manual_tab, width=20)
        self.amount_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(manual_tab, text="Slippage Tolerance (%):").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.slip_entry = ttk.Entry(manual_tab, width=20)
        self.slip_entry.grid(row=2, column=1, padx=5, pady=5)
        self.slip_entry.insert(0, "1")

        purchase_button = ttk.Button(manual_tab, text="Execute Purchase", command=self.execute_purchase)
        purchase_button.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.root.update()
        self.log_msg("[UI] Initialized with tabs")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def log_msg(self, msg):
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)

    def load_settings(self, env):
        for k, v in env.items():
            if k in self.entries:
                self.entries[k].delete(0, tk.END)
                self.entries[k].insert(0, v)

    def update_balances(self, bal_xrp, reserved_xrp, spendable_xrp, rlusd_bal, total_xrp_equiv):
        self.xrp_grand_total_label.config(text=f"XRP Grand Total: {total_xrp_equiv:.6f}")
        self.total_xrp_label.config(text=f"Total XRP: {bal_xrp:.6f}")
        self.xrp_reserve_label.config(text=f"Reserved XRP: {reserved_xrp:.6f}")
        self.spendable_xrp_label.config(text=f"Spendable XRP: {spendable_xrp:.6f}")
        self.rlusd_balance_label.config(text=f"RLUSD Balance: {rlusd_bal:.6f}")

    def save(self):
        env_path = find_dotenv() or os.environ.get("WIZARD_ENV_PATH", ".env")
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        out = []
        saved = set()
        for line in lines:
            if "=" in line:
                k = line.split("=", 1)[0].strip()
                if k in self.entries:
                    v = self.entries[k].get().strip()
                    out.append(f"{k}={v}\n")
                    saved.add(k)
                    continue
            out.append(line)
        for k in set(self.entries) - saved:
            v = self.entries[k].get().strip()
            out.append(f"{k}={v}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(out)
        load_dotenv(override=True)
        self.log_msg("[UI] Settings saved & reloaded.")

    def execute_purchase(self):
        try:
            client = healthy_client(self.clients)
            currency = self.buy_currency.get()
            amount = D(self.amount_entry.get())
            slip = D(self.slip_entry.get()) / D(100)
            if currency == "RLUSD":
                from wizard_rlusd_grid_v2 import market_buy_rlusd
                market_buy_rlusd(client, self.wallet, amount, slip, self.issuer, self.tag, self.log_msg)
            elif currency == "XRP":
                from wizard_rlusd_grid_v2 import market_buy_xrp
                market_buy_xrp(client, self.wallet, amount, slip, self.issuer, self.tag, self.log_msg)
            self.log_msg(f"[Purchase] Executed {amount} {currency} with {slip*100}% slip tolerance")
        except Exception as e:
            self.log_msg(f"[Purchase] Error: {str(e)}")

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()

# -------------------------
# Main runner loop
# -------------------------
def run_loop(args, stop_event, ui=None):
    def log(msg):
        print(msg)
        if ui:
            ui.log_msg(msg)

    env = load_env()
    clients = connect_clients()
    wallet = load_wallet_from_env()
    issuer = env.get("RLUSD_ISSUER", "rMxCKbEDwqr76QuheSUMdEGf4B9xJ8m5De")
    tag = "WIZARD"

    # AI singleton
    ai = AIHybridV2.get()

    last_reload = 0
    while not stop_event.is_set():
        now = time.time()
        # Hot reload env
        if now - last_reload >= int(env.get("ENV_RELOAD_EVERY_SEC", "10")):
            env = load_env()
            last_reload = now
            # Bridge user-facing AI_DIPSCOUNT_ENABLE -> AI_DIP_BUYBACK_ENABLE (module expects old name)
            os.environ["AI_DIP_BUYBACK_ENABLE"] = env.get("AI_DIPSCOUNT_ENABLE", "0")
            if ui:
                ui.load_settings(env)

        # Log select settings
        settings_str = "[Settings] " + " | ".join(
            f"{k}={v}" for k, v in sorted(env.items()) if k in [
                "MAX_OPEN_BUYS", "MAX_OPEN_SELLS", "BUY_OFFSET_BPS", "SELL_OFFSET_BPS",
                "STEP_PCT", "BUY_TRANCHE_RLUSD", "SELL_TRANCHE_RLUSD", "GLOBAL_SL_RLUSD",
                "SL_DISCOUNT_BPS", "INTERVAL", "LEVELS", "AUTO_CANCEL_BUY_BPS_FROM_MID",
                "AUTO_CANCEL_SELL_BPS_FROM_MID", "AUTO_CANCEL_MAX_PER_CYCLE", "AUTO_CANCEL_STRATEGY",
                "AUTO_CANCEL_ENABLED", "RESERVE_RELIEF_ENABLED", "RESERVE_RELIEF_BUY_CAP",
                "RESERVE_RELIEF_SELL_CAP", "RESERVE_RELIEF_MAX_PER_CYCLE", "RESERVE_RELIEF_GRACE_BPS",
                "RESERVE_RELIEF_STRATEGY", "PENDING_TTL_SEC", "SAFETY_BUFFER_XRP", "MIN_NOTIONAL_RLUSD",
                # AI keys
                "AI_OPTIMIZER_ENABLE", "AI_VOL_WINDOW", "AI_VOL_HIGH_BPS", "AI_VOL_LOW_BPS",
                "AI_STEP_UP_MULT", "AI_STEP_DOWN_MULT", "AI_OFFSETS_DELTA_BPS", "AI_LEVELS_MAX_DELTA",
                "AI_DIPSCOUNT_ENABLE", "AI_DIP_BB_TRIGGER_BPS", "AI_DIP_BB_SIZE_PCT", "AI_DIP_BB_SLIP_BPS", "AI_COOLDOWN_SEC"
            ]
        )
        log(settings_str)

        client = healthy_client(clients)
        classic = env["CLASSIC_ADDRESS"]
        safety_buffer_xrp = D(env["SAFETY_BUFFER_XRP"])

        try:
            # Balances + prices
            bal_xrp = get_balance_xrp(client, classic)
            rlusd_bal = get_iou_balance(client, classic, issuer)
            base, owner = get_reserves_xrp(client)
            num_objs = get_account_objects_count(client, classic)
            reserved_xrp = base + owner * D(num_objs) + safety_buffer_xrp
            spendable_xrp = max(D(0), bal_xrp - reserved_xrp)

            px = fetch_orderbook_prices(client, issuer, int(env.get("PRICE_FETCH_RETRIES", "3")))
            mid = px["mid"]

            rlusd_in_xrp = rlusd_bal / mid if mid and mid > 0 else D(0)
            total_xrp_equiv = bal_xrp + rlusd_in_xrp
            if ui:
                ui.update_balances(bal_xrp, reserved_xrp, spendable_xrp, rlusd_bal, total_xrp_equiv)
        except Exception as e:
            log(f"[Error] Failed to fetch balances: {str(e)}")
            time.sleep(10)
            continue

        # === AI Optimizer: compute tuners (step/offsets/levels) ===
        tuners = ai.update_and_get_tuners(mid)
        # Apply tuners
        step_pct_eff = D(env["STEP_PCT"]) / D(100) * tuners["step_mult"]
        buy_offset_eff  = D(env["BUY_OFFSET_BPS"])  + tuners["buy_offset_bps_delta"]
        sell_offset_eff = D(env["SELL_OFFSET_BPS"]) + tuners["sell_offset_bps_delta"]
        levels_eff = max(1, int(env.get("LEVELS", str(args.levels))) + int(tuners["levels_delta"]))
        log(f"[AI] vol-tuned step={step_pct_eff*100:.3f}% | buyΔ={tuners['buy_offset_bps_delta']}bps | sellΔ={tuners['sell_offset_bps_delta']}bps | levelsΔ={tuners['levels_delta']}")

        try:
            res = manage_grid_once(
                client, wallet, issuer, tag,
                levels_eff, step_pct_eff,                 # tuned levels/step
                buy_offset_eff, sell_offset_eff,          # tuned offsets
                D(env["BUY_TRANCHE_RLUSD"]), D(env["SELL_TRANCHE_RLUSD"]),
                D(env["MIN_NOTIONAL_RLUSD"]), safety_buffer_xrp,
                int(env.get("MAX_OPEN_BUYS", "12")), int(env.get("MAX_OPEN_SELLS", "1")),
                D(env.get("GLOBAL_SL_RLUSD", "0")), D(env.get("SL_DISCOUNT_BPS", "10")),
                env.get("AUTO_CANCEL_ENABLED", "1") == "1",
                D(env.get("AUTO_CANCEL_BUY_BPS_FROM_MID", "150")),
                D(env.get("AUTO_CANCEL_SELL_BPS_FROM_MID", "150")),
                int(env.get("AUTO_CANCEL_MAX_PER_CYCLE", "1")),
                env.get("AUTO_CANCEL_STRATEGY", "farthest"),
                log
            )
        except Exception as e:
            log(f"[Error] Grid cycle failed: {str(e)}")
            time.sleep(10)
            continue

        if res:
            mid = res.get("mid")
            orders = []
            existing = res.get("existing_offers", [])
            for of in existing:
                side = offer_side_vs_xrp(of)
                price = price_vs_xrp(of)
                if price is None:
                    continue
                if side == "buy":
                    xrp_amt = D(drops_to_xrp(of.get("TakerPays", of.get("taker_pays", "0"))))
                    orders.append(f"BUY seq={of['seq']}, {xrp_amt:.6f} XRP @ {price:.6f} RLUSD")
                elif side == "sell":
                    xrp_amt = D(drops_to_xrp(of.get("TakerGets", of.get("taker_gets", "0"))))
                    orders.append(f"SELL seq={of['seq']}, {xrp_amt:.6f} XRP @ {price:.6f} RLUSD")

            balances = {"spendable_xrp": spendable_xrp, "rlusd": rlusd_bal, "total_xrp_equiv": total_xrp_equiv}
            cycle_stats = {
                "placed": res.get("placed", 0),
                "skipped": res.get("skipped", 0),
                "throttle_skips": res.get("throttle_skips", 0),
                "pending_skips": res.get("pending_skips", 0),
                "cancelled": res.get("cancelled", 0),
                "pending_buy": res.get("pending_buy", 0),
                "pending_sell": res.get("pending_sell", 0)
            }
            try:
                log_balances_and_stats(classic, balances, orders, cycle_stats, log)
            except Exception as e:
                log(f"[Error] Logging failed: {str(e)}")
                time.sleep(10)
                continue

            log(f"[Cycle] mid={mid} placed={cycle_stats['placed']} skipped={cycle_stats['skipped']} (throttle={cycle_stats['throttle_skips']} pending={cycle_stats['pending_skips']}) cancelled={cycle_stats['cancelled']}")
            log(f"[Balances] Spendable XRP: {spendable_xrp:.6f} | RLUSD: {rlusd_bal:.6f} | Total XRP equiv: {total_xrp_equiv:.6f} (Reserved XRP: {reserved_xrp:.6f})")

            # === AI Dip Buyback ("DipsCount") ===
            try:
                ai.maybe_dip_buyback(client, wallet, issuer, mid, rlusd_bal, tag, log)
            except Exception as e:
                log(f"[AI] Dip buyback check error: {str(e)}")

        interval = int(env.get("INTERVAL", str(args.interval)))
        time.sleep(interval)

# -------------------------
# Helpers (offer decoding)
# -------------------------
def offer_side_vs_xrp(of: dict) -> str:
    g = of.get("taker_gets", of.get("TakerGets", {}))
    p = of.get("taker_pays", of.get("TakerPays", {}))
    if isinstance(g, dict) and isinstance(p, str):
        return "buy"
    if isinstance(g, str) and isinstance(p, dict):
        return "sell"
    return "other"

def price_vs_xrp(of: dict) -> Optional[D]:
    g = of.get("taker_gets", of.get("TakerGets", {}))
    p = of.get("taker_pays", of.get("TakerPays", {}))
    try:
        if isinstance(g, dict) and isinstance(p, str):
            xrp_amt = D(drops_to_xrp(p))
            iou_val = D(g.get("value", "0"))
            return iou_val / xrp_amt if xrp_amt > 0 else None
        if isinstance(g, str) and isinstance(p, dict):
            xrp_amt = D(drops_to_xrp(g))
            iou_val = D(p.get("value", "0"))
            return iou_val / xrp_amt if xrp_amt > 0 else None
    except Exception:
        return None
    return None

# -------------------------
# CLI
# -------------------------
def main():
    p = argparse.ArgumentParser(description="The Grid Wizard v2 – Grid Trader")
    p.add_argument("--levels", type=int, default=3)
    p.add_argument("--step", type=float, default=0.3)
    p.add_argument("--buy-offset-bps", type=float, default=0.1)
    p.add_argument("--sell-offset-bps", type=float, default=0.15)
    p.add_argument("--interval", type=int, default=60)
    p.add_argument("--ui", action="store_true")
    args = p.parse_args()

    stop_event = Event()
    if args.ui:
        ui = UI(stop_event)
        ui.load_settings(load_env())
        Thread(target=run_loop, args=(args, stop_event, ui), daemon=True).start()
        ui.root.mainloop()
    else:
        run_loop(args, stop_event)

if __name__ == "__main__":
    main()