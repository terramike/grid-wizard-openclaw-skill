"""Tool-facing runtime entrypoints for the OpenClaw skill package."""

from .schemas import SkillRequest, SkillResponse
from .safety import validate_request


def run_skill(request: SkillRequest) -> SkillResponse:
    """Validate and execute a skill request.

    This is a lightweight placeholder entrypoint for OpenClaw integration wiring.
    """
    validate_request(request)
    return SkillResponse(status="ok", message="Skill runtime scaffold is available.")
