# wizard_license.py
# SPDX-License-Identifier: BUSL-1.1
"""
Grid Wizard – simple NFT license gate (issuer-only)

Rule: If the connected account holds ANY NFT whose Issuer == LICENSE_ISSUER,
unlock Pro features. No .env override, no Taxon filtering.
"""

from typing import Tuple, Optional, List
import time
from xrpl.clients import JsonRpcClient
from xrpl.models.requests import AccountNFTs

# ==== HARD-CODED LICENSE PARAM ====
LICENSE_ISSUER = "rfYZ17wwhA4Be23fw8zthVmQQnrcdDRi52"  # Grid Wizard Labs issuer

# --- internal helpers ---------------------------------------------------------

def _req_with_backoff(client: JsonRpcClient, req, retries: int = 3, base: float = 0.5, cap: float = 5.0):
    for i in range(retries):
        try:
            resp = client.request(req)
            if hasattr(resp, "is_successful") and resp.is_successful():
                return resp
        except Exception:
            pass
        time.sleep(min(cap, base * (2 ** i)))
    return None

def _fetch_all_account_nfts(client: JsonRpcClient, classic: str, limit: int = 400) -> Optional[List[dict]]:
    """Paginate through account_nfts so we don't miss licenses on large wallets."""
    nfts: List[dict] = []
    marker = None
    for _ in range(10):  # safety cap: up to 10 pages
        req = AccountNFTs(account=classic, ledger_index="validated", limit=limit, marker=marker)
        resp = _req_with_backoff(client, req, retries=3)
        if resp is None:
            return None
        page = resp.result.get("account_nfts", [])
        nfts.extend(page)
        marker = resp.result.get("marker")
        if not marker:
            break
    return nfts

# --- public API ---------------------------------------------------------------

def check_license(client: JsonRpcClient, classic_address: str, log=None) -> Tuple[bool, str]:
    """
    Returns (ok, reason).
    ok=True if the account owns ANY NFT issued by LICENSE_ISSUER.
    """
    all_nfts = _fetch_all_account_nfts(client, classic_address, limit=400)
    if all_nfts is None:
        return (False, "[NFT] License check failed: RPC unavailable")

    if not all_nfts:
        return (False, "[NFT] No NFTs found on this account")

    for nft in all_nfts:
        if nft.get("Issuer") == LICENSE_ISSUER:
            return (True, f"issuer={LICENSE_ISSUER}")

    return (
        False,
        f"[NFT] License not found. Hold any NFT from issuer {LICENSE_ISSUER} to unlock Pro features."
    )

# --- optional: quick diagnostics ---------------------------------------------

def debug_list_issuers(client: JsonRpcClient, classic_address: str) -> List[str]:
    """Return a deduped list of issuers found on the account (for troubleshooting)."""
    nfts = _fetch_all_account_nfts(client, classic_address, limit=400) or []
    issuers = sorted({n.get("Issuer", "") for n in nfts if "Issuer" in n})
    return issuers