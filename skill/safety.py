"""Safety checks for runtime skill execution."""

from .schemas import SkillRequest


class SafetyValidationError(ValueError):
    """Raised when a request fails safety validation."""


def validate_request(request: SkillRequest) -> None:
    """Ensure required request fields are present."""
    if not request.action or not isinstance(request.action, str):
        raise SafetyValidationError("request.action must be a non-empty string")
    if not isinstance(request.payload, dict):
        raise SafetyValidationError("request.payload must be a dictionary")
