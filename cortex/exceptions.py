"""
Custom Exceptions for Cortex Platform
"""


from cortex.compat import override


class CortexError(Exception):
    """Base exception class for all Cortex framework runtime errors."""

    message: str
    exit_code: int

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code

    @override
    def __str__(self) -> str:
        return self.message


class WorkflowExecutionError(CortexError):
    """Raised when a workflow fails during execution or policy evaluation."""

    workflow_id: str | None

    def __init__(self, message: str, workflow_id: str | None = None):
        super().__init__(message, exit_code=1)
        self.workflow_id = workflow_id


class CapabilityViolationError(CortexError):
    """Raised when a plugin attempts an unauthorized action exceeding its granted capabilities."""

    capability: str | None

    def __init__(self, message: str, capability: str | None = None):
        super().__init__(message, exit_code=2)
        self.capability = capability


class ManifestError(CortexError):
    """Raised when a plugin manifest schema or definition is invalid."""

    def __init__(self, message: str):
        super().__init__(message, exit_code=3)


__all__ = [
    "CapabilityViolationError",
    "CortexError",
    "ManifestError",
    "WorkflowExecutionError",
]
