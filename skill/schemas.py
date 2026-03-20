"""Runtime contract schemas for the OpenClaw skill package."""

from dataclasses import dataclass


@dataclass
class SkillRequest:
    """Input contract for the skill runtime."""

    action: str
    payload: dict


@dataclass
class SkillResponse:
    """Output contract for the skill runtime."""

    status: str
    message: str
