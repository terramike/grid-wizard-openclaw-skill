"""Runtime handlers for Grid Wizard OpenClaw Skill actions."""

from __future__ import annotations

from typing import Any, Callable, Dict

from skill.schemas import ACTION_SCHEMAS

Handler = Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]


def _validate_type(value: Any, expected_type: str) -> bool:
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    return True


def _validate_payload(payload: Dict[str, Any], schema: Dict[str, Any], schema_name: str) -> None:
    required = schema.get("required", [])
    for key in required:
        if key not in payload:
            raise ValueError(f"{schema_name}: missing required field '{key}'")

    properties = schema.get("properties", {})
    additional_allowed = schema.get("additionalProperties", True)

    for key, value in payload.items():
        if key not in properties:
            if additional_allowed is False:
                raise ValueError(f"{schema_name}: unexpected field '{key}'")
            continue

        expected_type = properties[key].get("type")
        if expected_type and not _validate_type(value, expected_type):
            raise ValueError(
                f"{schema_name}: field '{key}' must be of type {expected_type}"
            )


def simulate_cycle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    schema = ACTION_SCHEMAS["simulate_cycle"]
    _validate_payload(params, schema["parameters"], "simulate_cycle.parameters")

    balances = dict(params["balances"])
    base = params["base_asset"]
    quote = params["quote_asset"]
    start_price = float(params["entry_price"])
    end_price = start_price * (1 + float(params["cycle_change_pct"]))
    trade_fraction = float(params["trade_fraction"])
    fee_rate = float(params.get("fee_bps", 0)) / 10_000.0

    base_balance = float(balances.get(base, 0.0))
    quote_balance = float(balances.get(quote, 0.0))

    if end_price >= start_price:
        trade_side = "sell_base"
        traded_base = max(base_balance * trade_fraction, 0.0)
        traded_quote = traded_base * end_price
        fee_paid_quote = traded_quote * fee_rate
        balances[base] = base_balance - traded_base
        balances[quote] = quote_balance + traded_quote - fee_paid_quote
    else:
        trade_side = "buy_base"
        quote_to_spend = max(quote_balance * trade_fraction, 0.0)
        traded_base = quote_to_spend / end_price if end_price > 0 else 0.0
        traded_quote = quote_to_spend
        fee_paid_quote = traded_quote * fee_rate
        balances[quote] = quote_balance - traded_quote - fee_paid_quote
        balances[base] = base_balance + traded_base

    response = {
        "starting_price": start_price,
        "ending_price": end_price,
        "trade_side": trade_side,
        "traded_base_amount": traded_base,
        "traded_quote_amount": traded_quote,
        "fee_paid_quote": fee_paid_quote,
        "balances_after": balances,
    }
    _validate_payload(response, schema["response"], "simulate_cycle.response")
    return response


def run_one_cycle(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    schema = ACTION_SCHEMAS["run_one_cycle"]
    _validate_payload(params, schema["parameters"], "run_one_cycle.parameters")

    pair = params["pair"]
    max_order_size = float(params["max_order_size"])
    spread_bps = float(params["target_spread_bps"])
    dry_run = bool(params.get("dry_run", True))

    side = "sell" if spread_bps >= 0 else "buy"
    status = "planned" if dry_run else "submitted"
    reason = "dry run requested" if dry_run else "cycle submitted"

    response = {
        "pair": pair,
        "dry_run": dry_run,
        "status": status,
        "side": side,
        "order_size": max_order_size,
        "target_spread_bps": abs(spread_bps),
        "reason": reason,
    }
    _validate_payload(response, schema["response"], "run_one_cycle.response")
    return response


def show_balances(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    schema = ACTION_SCHEMAS["show_balances"]
    _validate_payload(params, schema["parameters"], "show_balances.parameters")

    wallet_balances = dict(context.get("balances", {}))
    include_zero = bool(params.get("include_zero", False))
    requested_assets = params.get("assets")

    if requested_assets:
        filtered = {asset: float(wallet_balances.get(asset, 0.0)) for asset in requested_assets}
    else:
        filtered = {k: float(v) for k, v in wallet_balances.items()}

    if not include_zero:
        filtered = {k: v for k, v in filtered.items() if v != 0}

    response = {
        "balances": filtered,
        "asset_count": len(filtered),
    }
    _validate_payload(response, schema["response"], "show_balances.response")
    return response


ACTION_HANDLERS: Dict[str, Handler] = {
    "simulate_cycle": simulate_cycle,
    "run_one_cycle": run_one_cycle,
    "show_balances": show_balances,
}


def dispatch_action(action_name: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    if action_name not in ACTION_HANDLERS:
        raise ValueError(f"Unknown action '{action_name}'")
    return ACTION_HANDLERS[action_name](params, context)
