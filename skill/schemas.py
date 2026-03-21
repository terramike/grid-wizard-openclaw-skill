"""Simple request/response schemas for skill actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ActionRequest:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResponse:
    ok: bool
    action: str
    result: Dict[str, Any]
