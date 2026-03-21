"""CLI-style skill runner for Grid Wizard orchestration."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any, Callable, Dict

from skill.safety import enforce_safety
from skill.schemas import ActionRequest, ActionResponse
from wizard_core.wizard_orchestrator_v2 import GridWizardEngine, available_actions


def dispatch(req: ActionRequest) -> ActionResponse:
    engine = GridWizardEngine()
    config = engine.show_config()

    if req.action not in available_actions():
        return ActionResponse(ok=False, action=req.action, result={"error": "Unknown action"})

    gate = enforce_safety(req.action, config)
    if not gate.get("allowed", False):
        return ActionResponse(ok=False, action=req.action, result=gate)

    handler: Callable[[], Dict[str, Any]] = getattr(engine, req.action)
    result = handler()
    ok = result.get("status") not in {"blocked"}
    return ActionResponse(ok=ok, action=req.action, result=result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Grid Wizard skill runner")
    parser.add_argument("action", help="Action name")
    parser.add_argument("--params", default="{}", help="JSON action params")
    args = parser.parse_args()

    req = ActionRequest(action=args.action, params=json.loads(args.params))
    res = dispatch(req)
    print(json.dumps(asdict(res), indent=2))


if __name__ == "__main__":
    main()
