"""Schema definitions shared by manifest generation and runtime handlers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

JSONSchema = Dict[str, Any]

SIMULATE_CYCLE_PARAMS_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "balances": {
            "type": "object",
            "description": "Current balances by asset symbol (for example RLUSD and XRP).",
            "additionalProperties": {"type": "number"},
            "minProperties": 1,
        },
        "base_asset": {
            "type": "string",
            "description": "Asset symbol used as base in the trading pair.",
            "minLength": 1,
        },
        "quote_asset": {
            "type": "string",
            "description": "Asset symbol used as quote in the trading pair.",
            "minLength": 1,
        },
        "entry_price": {
            "type": "number",
            "description": "Starting market price for the simulated cycle (quote per base).",
            "exclusiveMinimum": 0,
        },
        "cycle_change_pct": {
            "type": "number",
            "description": "Percent move to apply for a single cycle; negative values simulate dips.",
            "minimum": -1,
        },
        "trade_fraction": {
            "type": "number",
            "description": "Fraction (0..1] of the relevant inventory to trade in this simulated cycle.",
            "exclusiveMinimum": 0,
            "maximum": 1,
        },
        "fee_bps": {
            "type": "number",
            "description": "Optional exchange fee in basis points applied to notional.",
            "minimum": 0,
            "default": 0,
        },
    },
    "required": [
        "balances",
        "base_asset",
        "quote_asset",
        "entry_price",
        "cycle_change_pct",
        "trade_fraction",
    ],
}

SIMULATE_CYCLE_RESPONSE_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "starting_price": {"type": "number"},
        "ending_price": {"type": "number"},
        "trade_side": {"type": "string", "enum": ["buy_base", "sell_base"]},
        "traded_base_amount": {"type": "number", "minimum": 0},
        "traded_quote_amount": {"type": "number", "minimum": 0},
        "fee_paid_quote": {"type": "number", "minimum": 0},
        "balances_after": {
            "type": "object",
            "additionalProperties": {"type": "number"},
        },
    },
    "required": [
        "starting_price",
        "ending_price",
        "trade_side",
        "traded_base_amount",
        "traded_quote_amount",
        "fee_paid_quote",
        "balances_after",
    ],
}

RUN_ONE_CYCLE_PARAMS_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "pair": {
            "type": "string",
            "description": "Pair symbol in BASE/QUOTE form, such as XRP/RLUSD.",
            "pattern": r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$",
        },
        "max_order_size": {
            "type": "number",
            "description": "Maximum base size to place for this cycle.",
            "exclusiveMinimum": 0,
        },
        "target_spread_bps": {
            "type": "number",
            "description": "Desired maker spread for the cycle in basis points.",
            "minimum": 0,
        },
        "allow_market_order": {
            "type": "boolean",
            "description": "If true, permit market order fallback when maker placement fails.",
            "default": False,
        },
        "dry_run": {
            "type": "boolean",
            "description": "If true, evaluate and return a plan without placing an order.",
            "default": True,
        },
    },
    "required": ["pair", "max_order_size", "target_spread_bps"],
}

RUN_ONE_CYCLE_RESPONSE_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "pair": {"type": "string"},
        "dry_run": {"type": "boolean"},
        "status": {"type": "string", "enum": ["planned", "submitted", "skipped"]},
        "side": {"type": "string", "enum": ["buy", "sell"]},
        "order_size": {"type": "number", "minimum": 0},
        "target_spread_bps": {"type": "number", "minimum": 0},
        "reason": {"type": "string"},
    },
    "required": [
        "pair",
        "dry_run",
        "status",
        "side",
        "order_size",
        "target_spread_bps",
        "reason",
    ],
}

SHOW_BALANCES_PARAMS_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "assets": {
            "type": "array",
            "description": "Optional explicit asset symbols to include. Omit to show all known balances.",
            "items": {"type": "string", "minLength": 1},
            "minItems": 1,
            "uniqueItems": True,
        },
        "include_zero": {
            "type": "boolean",
            "description": "Include zero balances in the response when true.",
            "default": False,
        },
    },
}

SHOW_BALANCES_RESPONSE_SCHEMA: JSONSchema = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "balances": {
            "type": "object",
            "additionalProperties": {"type": "number"},
        },
        "asset_count": {"type": "integer", "minimum": 0},
    },
    "required": ["balances", "asset_count"],
}

ACTION_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "simulate_cycle": {
        "description": (
            "Model one grid cycle using supplied balances and price move assumptions. "
            "Returns projected balances after fees and a single buy/sell decision."
        ),
        "parameters": SIMULATE_CYCLE_PARAMS_SCHEMA,
        "response": SIMULATE_CYCLE_RESPONSE_SCHEMA,
    },
    "run_one_cycle": {
        "description": (
            "Plan or execute one live trading cycle for a pair, including side selection "
            "and order sizing under provided risk limits."
        ),
        "parameters": RUN_ONE_CYCLE_PARAMS_SCHEMA,
        "response": RUN_ONE_CYCLE_RESPONSE_SCHEMA,
    },
    "show_balances": {
        "description": (
            "Return current wallet balances, optionally filtered to specific assets and "
            "including or excluding zero balances."
        ),
        "parameters": SHOW_BALANCES_PARAMS_SCHEMA,
        "response": SHOW_BALANCES_RESPONSE_SCHEMA,
    },
}


def build_manifest_actions() -> list[Dict[str, Any]]:
    """Return serializable action definitions for manifest.json."""
    actions: list[Dict[str, Any]] = []
    for name, spec in ACTION_SCHEMAS.items():
        actions.append(
            {
                "name": name,
                "description": spec["description"],
                "parameters": deepcopy(spec["parameters"]),
                "response": deepcopy(spec["response"]),
            }
        )
    return actions
