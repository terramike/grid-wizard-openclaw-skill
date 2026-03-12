#!/usr/bin/env python3
"""
The Grid Wizard Engine v2 – XRP/RLUSD Grid Trader with Pending Queue, Throttles, Reserve Relief
"""

import os
import sys
import time
import random
from decimal import Decimal, ROUND_DOWN
from typing import List, Dict, Optional, Union, Callable

from dotenv import load_dotenv
from xrpl.clients import JsonRpcClient
from xrpl.models.transactions import OfferCreate, OfferCancel, TrustSet, Memo
from xrpl.models.transactions.offer_create import OfferCreateFlag
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import AccountInfo, AccountLines, BookOffers, AccountOffers, ServerInfo, AccountObjects, Tx
from xrpl.wallet import Wallet
from xrpl.transaction import sign_and_submit as xrpl_sign_and_submit
from xrpl.utils import xrp_to_drops, drops_to_xrp
from xrpl.models.currencies import XRP
from ecdsa import SigningKey, SECP256k1

from wizard_license import check_license  # <-- NEW

D = Decimal
PRICE_PREC = D("0.000001")

pendings = {"buy": [], "sell": []}  # [{"timestamp": float, "hash": str, "tranche": D}]
last_place = {"buy": 0.0, "sell": 0.0}

def derive_pubkey_hex_from_privkey_hex(priv_hex: str) -> str:
    sk = SigningKey.from_string(bytes.fromhex(priv_hex), curve=SECP256k1)
    vk = sk.get_verifying_key()
    x = vk.pubkey.point.x(); y = vk.pubkey.point.y()
    prefix = b"\x03" if (y & 1) else b"\x02"
    return (prefix + x.to_bytes(32, "big")).hex().upper()

def load_wallet_from_env() -> Wallet:
    load_dotenv(override=True)
    classic = os.environ.get("CLASSIC_ADDRESS", "").strip()
    priv_hex = os.environ.get("PRIVATE_KEY_HEX", "").strip()
    algo = os.environ.get("KEY_ALGO", "secp256k1").strip().lower()
    if not classic or not priv_hex or algo != "secp256k1":
        sys.exit(2)
    pub_hex = derive_pubkey_hex_from_privkey_hex(priv_hex)
    return Wallet(public_key=pub_hex, private_key=priv_hex)

def connect_clients() -> List[JsonRpcClient]:
    prim = os.environ.get("XRPL_RPC_PRIMARY", "https://s1.ripple.com:51234").strip()
    fb = os.environ.get("XRPL_RPC_FALLBACK", "https://s2.ripple.com:51234").strip()
    urls = [u for u in [prim, fb] if u]
    return [JsonRpcClient(u) for u in urls]

def healthy_client(clients: List[JsonRpcClient]) -> JsonRpcClient:
    from xrpl.models.requests import ServerInfo
    for c in clients:
        try:
            if c.request(ServerInfo()).is_successful():
                return c
        except Exception:
            pass
    raise RuntimeError("No healthy RPC.")

def request_with_backoff_on(client: JsonRpcClient, req, retries: int = 3):
    base = 0.6
    maxs = 6.0
    for k in range(retries):
        try:
            resp = client.request(req)
            if resp.is_successful():
                return resp
        except Exception:
            pass
        time.sleep(min(maxs, base * (2 ** k)) + random.random() * 0.2)
    raise RuntimeError("Request failed.")

def get_balance_xrp(client: JsonRpcClient, address: str) -> D:
    r = request_with_backoff_on(client, AccountInfo(account=address, ledger_index="validated"))
    return D(drops_to_xrp(r.result["account_data"]["Balance"]))

def get_reserves_xrp(client: JsonRpcClient) -> tuple[D, D]:
    info = request_with_backoff_on(client, ServerInfo())
    v = info.result["info"]["validated_ledger"]
    return D(v.get("reserve_base_xrp", "10")), D(v.get("reserve_inc_xrp", "2"))

def get_account_objects_count(client: JsonRpcClient, address: str) -> int:
    r = request_with_backoff_on(client, AccountObjects(account=address, ledger_index="validated", limit=400))
    return len(r.result.get("account_objects", [])) if r.is_successful() else 0

def currency_to_hex20(code: str) -> str:
    raw = code.encode("ascii")
    return (raw + b"\x00" * (20 - len(raw))).hex().upper()

def get_iou_balance(client: JsonRpcClient, address: str, issuer: str) -> D:
    r = request_with_backoff_on(client, AccountLines(account=address, peer=issuer, ledger_index="validated"))
    desired_hex = currency_to_hex20("RLUSD")
    for line in r.result.get("lines", []):
        cur = line.get("currency", "").upper()
        if cur == "RLUSD" or cur == desired_hex:
            return D(line.get("balance", "0"))
    return D("0")

def has_trustline(client: JsonRpcClient, address: str, issuer: str) -> bool:
    r = request_with_backoff_on(client, AccountLines(account=address, peer=issuer, ledger_index="validated"))
    desired_hex = currency_to_hex20("RLUSD")
    for line in r.result.get("lines", []):
        cur = line.get("currency", "").upper()
        if cur == "RLUSD" or cur == desired_hex:
            return True
    return False

def is_xrp_amount(a: Union[str, int, dict]) -> bool:
    return isinstance(a, (str, int))

def _gets(of: dict): return of.get("taker_gets") if "taker_gets" in of else of.get("TakerGets")
def _pays(of: dict): return of.get("taker_pays") if "taker_pays" in of else of.get("TakerPays")

def offer_side_vs_xrp(of: dict) -> str:
    g = _gets(of); p = _pays(of)
    if isinstance(g, dict) and is_xrp_amount(p):
        return "buy"  # BUY XRP (sell RLUSD)
    if is_xrp_amount(g) and isinstance(p, dict):
        return "sell"  # SELL XRP (buy RLUSD)
    return "other"

def price_vs_xrp(of: dict) -> Optional[D]:
    g = _gets(of); p = _pays(of)
    try:
        if isinstance(g, dict) and is_xrp_amount(p):
            xrp_amt = D(drops_to_xrp(p)); iou_val = D(g.get("value", "0"))
            return iou_val / xrp_amt if xrp_amt > 0 else None
        if is_xrp_amount(g) and isinstance(p, dict):
            xrp_amt = D(drops_to_xrp(g)); iou_val = D(p.get("value", "0"))
            return iou_val / xrp_amt if xrp_amt > 0 else None
    except Exception:
        return None
    return None

def list_pair_offers(client: JsonRpcClient, address: str, issuer: str) -> List[dict]:
    r = request_with_backoff_on(client, AccountOffers(account=address, limit=400))
    offers = r.result.get("offers", []); out = []
    desired_hex = currency_to_hex20("RLUSD")
    for of in offers:
        g = _gets(of); p = _pays(of)
        is_pair = (
            (isinstance(g, dict) and is_xrp_amount(p) and g.get("currency","").upper() in {"RLUSD", desired_hex} and g.get("issuer","")==issuer) or
            (is_xrp_amount(g) and isinstance(p, dict) and p.get("currency","").upper() in {"RLUSD", desired_hex} and p.get("issuer","")==issuer)
        )
        if is_pair: out.append(of)
    return out

_last_book: Dict[str, Optional[D]] = {"ts": 0.0, "bid": None, "ask": None, "mid": None}

def fetch_orderbook_prices(client: JsonRpcClient, issuer: str, retries: int = 3) -> Dict[str, Optional[D]]:
    global _last_book
    now = time.time()
    if now - _last_book["ts"] <= 2:
        return {"best_bid": _last_book["bid"], "best_ask": _last_book["ask"], "mid": _last_book["mid"]}
    asks = request_with_backoff_on(client, BookOffers(
        taker_gets=XRP(),
        taker_pays=IssuedCurrencyAmount(currency=currency_to_hex20("RLUSD"), issuer=issuer, value="1"),
        limit=10,
    ), retries)
    bids = request_with_backoff_on(client, BookOffers(
        taker_gets=IssuedCurrencyAmount(currency=currency_to_hex20("RLUSD"), issuer=issuer, value="1"),
        taker_pays=XRP(),
        limit=10,
    ), retries)
    best_ask = best_bid = None
    if asks.result.get("offers"):
        ofa = asks.result["offers"][0]
        best_ask = D(ofa["TakerPays"]["value"]) / D(drops_to_xrp(ofa["TakerGets"]))
    if bids.result.get("offers"):
        ofb = bids.result["offers"][0]
        best_bid = D(ofb["TakerGets"]["value"]) / D(drops_to_xrp(ofb["TakerPays"]))
    mid = (best_bid + best_ask) / 2 if best_bid and best_ask else (best_bid or best_ask)
    _last_book = {"ts": now, "bid": best_bid, "ask": best_ask, "mid": mid}
    return {"best_bid": best_bid, "best_ask": best_ask, "mid": mid}

def submit_transaction(tx, client: JsonRpcClient, wallet: Wallet):
    return xrpl_sign_and_submit(tx, client, wallet, autofill=True)

def cancel_offers_by_seq(client: JsonRpcClient, wallet: Wallet, seqs: List[int], tag: str, log: Callable[[str], None]):
    classic = os.environ["CLASSIC_ADDRESS"]
    for seq in seqs:
        tx = OfferCancel(account=classic, offer_sequence=seq, memos=[Memo(memo_data=tag.encode().hex())])
        res = submit_transaction(tx, client, wallet)
        log(f"[Cancel] seq={seq} {'cancelled' if res.is_successful() else 'ERROR '+str(res.result)}")

def place_buy_xrp(client: JsonRpcClient, wallet: Wallet, rlusd_amount: D, price_rlusd: D, issuer: str, tag: str, log: Callable[[str], None], flags: int = 0) -> Optional[str]:
    classic = os.environ["CLASSIC_ADDRESS"]
    currency_format = currency_to_hex20("RLUSD")
    xrp_amt = rlusd_amount / price_rlusd
    tx = OfferCreate(
        account=classic,
        taker_gets=IssuedCurrencyAmount(currency=currency_format, issuer=issuer, value=str(rlusd_amount.quantize(PRICE_PREC))),
        taker_pays=xrp_to_drops(float(xrp_amt)),
        memos=[Memo(memo_data=tag.encode().hex())],
        flags=flags
    )
    res = submit_transaction(tx, client, wallet)
    log(f"[BUY] {xrp_amt:.6f} XRP @ {price_rlusd:.6f} RLUSD {'placed' if res.is_successful() else 'ERROR'}")
    return res.result.get("hash") if res.is_successful() else None

def place_sell_xrp(client: JsonRpcClient, wallet: Wallet, rlusd_amount: D, price_rlusd: D, issuer: str, tag: str, log: Callable[[str], None], flags: int = 0) -> Optional[str]:
    classic = os.environ["CLASSIC_ADDRESS"]
    currency_format = currency_to_hex20("RLUSD")
    xrp_amt = rlusd_amount / price_rlusd
    tx = OfferCreate(
        account=classic,
        taker_gets=xrp_to_drops(float(xrp_amt)),
        taker_pays=IssuedCurrencyAmount(currency=currency_format, issuer=issuer, value=str(rlusd_amount.quantize(PRICE_PREC))),
        memos=[Memo(memo_data=tag.encode().hex())],
        flags=flags
    )
    res = submit_transaction(tx, client, wallet)
    log(f"[SELL] {xrp_amt:.6f} XRP @ {price_rlusd:.6f} RLUSD {'placed' if res.is_successful() else 'ERROR'}")
    return res.result.get("hash") if res.is_successful() else None

def market_buy_rlusd(client: JsonRpcClient, wallet: Wallet, amount: D, slip: D, issuer: str, tag: str, log: Callable[[str], None]):
    px = fetch_orderbook_prices(client, issuer)
    mid = px["mid"]
    if not mid:
        raise ValueError("No mid price")
    min_price = mid * (D(1) - slip)
    _ = place_sell_xrp(client, wallet, amount, min_price, issuer, tag, log, flags=OfferCreateFlag.TF_IMMEDIATE_OR_CANCEL)

def market_buy_xrp(client: JsonRpcClient, wallet: Wallet, amount: D, slip: D, issuer: str, tag: str, log: Callable[[str], None]):
    px = fetch_orderbook_prices(client, issuer)
    mid = px["mid"]
    if not mid:
        raise ValueError("No mid price")
    max_price = mid * (D(1) + slip)
    max_rlusd = amount * max_price
    _ = place_buy_xrp(client, wallet, max_rlusd, D(1) / max_price, issuer, tag, log, flags=OfferCreateFlag.TF_IMMEDIATE_OR_CANCEL)

def calc_anchored_targets(best_bid: Optional[D], best_ask: Optional[D], mid: D,
                          levels: int, step_pct: D,
                          buy_offset_bps: D, sell_offset_bps: D) -> Dict[str, List[D]]:
    bid_anchor = best_bid or mid
    ask_anchor = best_ask or mid
    p0_buy = bid_anchor * (D(1) - buy_offset_bps / D(10000))
    p0_sell = ask_anchor * (D(1) + sell_offset_bps / D(10000))
    buys = [p0_buy * (D(1) - step_pct * D(i)) for i in range(levels)]
    sells = [p0_sell * (D(1) + step_pct * D(i)) for i in range(levels)]
    return {"buy": buys, "sell": sells}

def clean_pendings(client: JsonRpcClient, ttl: int, log: Callable[[str], None]):
    now = time.time()
    for side in ["buy", "sell"]:
        new_list = []
        for p in pendings[side]:
            if now - p["timestamp"] > ttl:
                log(f"[Pending] Expired {side} hash={p['hash'][:8]}")
                continue
            try:
                tx_res = client.request(Tx(transaction=p["hash"]))
                if tx_res.is_successful() and tx_res.result.get("validated"):
                    if tx_res.result["meta"].get("TransactionResult") == "tesSUCCESS":
                        log(f"[Pending] Confirmed {side} hash={p['hash'][:8]}")
                    else:
                        log(f"[Pending] Failed {side} hash={p['hash'][:8]}")
                    continue
            except Exception:
                # txnNotFound: keep as queued
                pass
            new_list.append(p)
        pendings[side] = new_list

def auto_cancel_offers(client: JsonRpcClient, wallet: Wallet, existing: List[dict], mid: D,
                      auto_cancel_buy_bps: D, auto_cancel_sell_bps: D,
                      max_per_cycle: int, strategy: str, tag: str, log: Callable[[str], None]) -> int:
    to_cancel = []
    for of in existing:
        price = price_vs_xrp(of)
        if price is None:
            continue
        side = offer_side_vs_xrp(of)
        if side == "buy":
            bps_diff = (mid - price) / mid * D(10000)
            if bps_diff >= auto_cancel_buy_bps:
                to_cancel.append((of["seq"], bps_diff, side))
        elif side == "sell":
            bps_diff = (price - mid) / mid * D(10000)
            if bps_diff >= auto_cancel_sell_bps:
                to_cancel.append((of["seq"], bps_diff, side))

    if not to_cancel:
        return 0

    # Sort by strategy
    to_cancel.sort(key=lambda x: x[1] if strategy == "farthest" else -x[0])
    to_cancel = to_cancel[:max_per_cycle]

    seqs = [seq for seq, _, _ in to_cancel]
    cancel_offers_by_seq(client, wallet, seqs, tag, log)
    return len(seqs)

def manage_grid_once(client: JsonRpcClient, wallet: Wallet, issuer: str, tag: str,
                     levels: int, step_pct: D,
                     buy_offset_bps: D, sell_offset_bps: D,
                     buy_tranche_rlusd: D, sell_tranche_rlusd: D,
                     min_notional: D, safety_buffer_xrp: D,
                     max_open_buys: int, max_open_sells: int,
                     global_sl_rlusd: D, sl_discount_bps: D,
                     auto_cancel_enabled: bool,
                     auto_cancel_buy_bps: D, auto_cancel_sell_bps: D,
                     auto_cancel_max_per_cycle: int, auto_cancel_strategy: str,
                     log: Callable[[str], None]):
    classic = os.environ["CLASSIC_ADDRESS"]
    ttl = int(os.environ.get("PENDING_TTL_SEC", "120"))
    buy_throttle = int(os.environ.get("BUY_THROTTLE_SEC", "10"))
    sell_throttle = int(os.environ.get("SELL_THROTTLE_SEC", "10"))
    price_retries = int(os.environ.get("PRICE_FETCH_RETRIES", "3"))
    reserve_relief_enabled = os.environ.get("RESERVE_RELIEF_ENABLED", "0") == "1"

    # ==== NFT license check (robust module) ====
    ok, reason = check_license(client, classic, log)
    if not ok:
        log(reason)
        raise RuntimeError(reason)
    else:
        log(f"[NFT] License OK: {reason}")

    if not has_trustline(client, classic, issuer):
        log("[Trustline] RLUSD missing. Creating...")
        t = TrustSet(
            account=classic,
            limit_amount=IssuedCurrencyAmount(currency=currency_to_hex20("RLUSD"), issuer=issuer, value="1000000"),
            memos=[Memo(memo_data=tag.encode().hex())],
        )
        res = submit_transaction(t, client, wallet)
        log("[Trustline] Submitted." if res.is_successful() else f"[Trustline] ERROR {res.result}")

    clean_pendings(client, ttl, log)

    px = fetch_orderbook_prices(client, issuer, price_retries)
    mid = px["mid"]
    if mid is None:
        log("[Price] No valid mid; retry later.")
        return None
    log(f"[Price] bid={px['best_bid']:.6f} ask={px['best_ask']:.6f} mid={mid:.6f}")

    # Global SL
    if global_sl_rlusd > 0 and mid <= global_sl_rlusd:
        log(f"[Risk] Global SL hit (mid {mid:.6f} ≤ {global_sl_rlusd:.6f}). Flattening...")
        pair_offers = list_pair_offers(client, classic, issuer)
        if pair_offers:
            cancel_offers_by_seq(client, wallet, [of["seq"] for of in pair_offers], tag, log)
        bal = get_balance_xrp(client, classic)
        base, owner = get_reserves_xrp(client)
        avail = bal - base - safety_buffer_xrp
        if avail > 0:
            px_sell = (px["best_bid"] * (D(1) - sl_discount_bps / D(10000))) if px["best_bid"] else mid
            log(f"[Risk] Flatten (SELL) {avail:.6f} XRP @ {px_sell:.6f} RLUSD")
            place_sell_xrp(client, wallet, avail * px_sell, px_sell, issuer, tag, log)
        return {"mid": mid, "sl_executed": True}

    rlusd_bal = get_iou_balance(client, classic, issuer)
    xrp_bal = get_balance_xrp(client, classic)
    base, owner = get_reserves_xrp(client)
    num_objs = get_account_objects_count(client, classic)
    reserved_xrp = base + owner * D(num_objs) + safety_buffer_xrp
    spendable_xrp = max(D(0), xrp_bal - reserved_xrp)

    targets = calc_anchored_targets(px["best_bid"], px["best_ask"], mid, levels, step_pct, buy_offset_bps, sell_offset_bps)

    existing = list_pair_offers(client, classic, issuer)
    existing_buy = sum(1 for of in existing if offer_side_vs_xrp(of) == "buy")
    existing_sell = sum(1 for of in existing if offer_side_vs_xrp(of) == "sell")

    cancelled = 0
    if auto_cancel_enabled:
        cancelled = auto_cancel_offers(client, wallet, existing, mid,
                                       auto_cancel_buy_bps, auto_cancel_sell_bps,
                                       auto_cancel_max_per_cycle, auto_cancel_strategy, tag, log)
        # Refresh existing after cancel
        existing = list_pair_offers(client, classic, issuer)
        existing_buy = sum(1 for of in existing if offer_side_vs_xrp(of) == "buy")
        existing_sell = sum(1 for of in existing if offer_side_vs_xrp(of) == "sell")

    if reserve_relief_enabled:
        from wizard_reserve_relief import prune_reserve
        relief_cancelled = prune_reserve(client, wallet, issuer, mid, existing, 
                                         {"buy": int(os.environ.get("RESERVE_RELIEF_BUY_CAP", "10")),
                                          "sell": int(os.environ.get("RESERVE_RELIEF_SELL_CAP", "2"))},
                                         D(os.environ.get("RESERVE_RELIEF_GRACE_BPS", "8")),
                                         int(os.environ.get("RESERVE_RELIEF_MAX_PER_CYCLE", "3")),
                                         os.environ.get("RESERVE_RELIEF_STRATEGY", "farthest"),
                                         tag, log)
        cancelled += relief_cancelled
        # Refresh existing
        existing = list_pair_offers(client, classic, issuer)
        existing_buy = sum(1 for of in existing if offer_side_vs_xrp(of) == "buy")
        existing_sell = sum(1 for of in existing if offer_side_vs_xrp(of) == "sell")

    # Log open orders
    buy_orders = []
    sell_orders = []
    for of in existing:
        side = offer_side_vs_xrp(of)
        price = price_vs_xrp(of)
        if price is None:
            continue
        if side == "buy":
            xrp_amt = D(drops_to_xrp(_pays(of)))
            buy_orders.append(f"seq={of['seq']}, {xrp_amt:.6f} XRP @ {price:.6f} RLUSD")
        elif side == "sell":
            xrp_amt = D(drops_to_xrp(_gets(of)))
            sell_orders.append(f"seq={of['seq']}, {xrp_amt:.6f} XRP @ {price:.6f} RLUSD")
    orders_str = f"[Orders] BUY: {' | '.join(buy_orders) or 'none'} | SELL: {' | '.join(sell_orders) or 'none'}"
    log(orders_str)

    pending_buy_len = len(pendings["buy"])
    pending_sell_len = len(pendings["sell"])
    now = time.time()
    buy_next_ok = max(0, buy_throttle - (now - last_place["buy"]))
    sell_next_ok = max(0, sell_throttle - (now - last_place["sell"]))
    log(f"[OpenCap] BUY: open={existing_buy}, pending={pending_buy_len}, next_ok_in={buy_next_ok:.0f} sec | SELL: open={existing_sell}, pending={pending_sell_len}, next_ok_in={sell_next_ok:.0f} sec")

    to_place_buy = max(0, max_open_buys - existing_buy - pending_buy_len)
    to_place_sell = max(0, max_open_sells - existing_sell - pending_sell_len)

    placed = 0
    skipped = 0
    throttle_skips = 0
    pending_skips = 0

    buy_tranche = buy_tranche_rlusd
    sell_tranche = sell_tranche_rlusd

    for p in targets["buy"][:to_place_buy]:
        if now - last_place["buy"] < buy_throttle:
            log(f"[Skip] BUY: throttle active, next in {buy_next_ok:.0f} sec")
            throttle_skips += 1
            skipped += 1
            continue
        if existing_buy + pending_buy_len >= max_open_buys:
            log(f"[Skip] BUY: pending cap reached")
            pending_skips += 1
            skipped += 1
            continue
        if rlusd_bal >= buy_tranche:
            if buy_tranche >= min_notional:
                hash_ = place_buy_xrp(client, wallet, buy_tranche, p, issuer, tag, log)
                if hash_:
                    pendings["buy"].append({"timestamp": now, "hash": hash_, "tranche": buy_tranche})
                    placed += 1
                    last_place["buy"] = now
                    rlusd_bal -= buy_tranche
            else:
                log(f"[Skip] BUY: tranche {buy_tranche:.6f} RLUSD < min_notional {min_notional:.6f}")
                skipped += 1
        else:
            log(f"[Skip] BUY: insufficient RLUSD {rlusd_bal:.6f} < {buy_tranche:.6f}")
            skipped += 1

    for p in targets["sell"][:to_place_sell]:
        if now - last_place["sell"] < sell_throttle:
            log(f"[Skip] SELL: throttle active, next in {sell_next_ok:.0f} sec")
            throttle_skips += 1
            skipped += 1
            continue
        if existing_sell + pending_sell_len >= max_open_sells:
            log(f"[Skip] SELL: pending cap reached")
            pending_skips += 1
            skipped += 1
            continue
        xrp_amt = sell_tranche / p
        if xrp_amt <= spendable_xrp:
            hash_ = place_sell_xrp(client, wallet, sell_tranche, p, issuer, tag, log)
            if hash_:
                pendings["sell"].append({"timestamp": now, "hash": hash_, "tranche": sell_tranche})
                placed += 1
                last_place["sell"] = now
                spendable_xrp -= xrp_amt
        else:
            log(f"[Skip] SELL: insufficient XRP {spendable_xrp:.6f} < {xrp_amt:.6f}")
            skipped += 1

    return {
        "mid": mid, "placed": placed, "skipped": skipped, "throttle_skips": throttle_skips,
        "pending_skips": pending_skips, "cancelled": cancelled,
        "pending_buy": len(pendings["buy"]), "pending_sell": len(pendings["sell"]),
        "existing_offers": existing
    }