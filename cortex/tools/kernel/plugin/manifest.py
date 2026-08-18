"""
Declarative Plugin Manifest Schema

Every plugin declares its event consumption/production contract and the
kernel capabilities it requires.  The Kernel enforces capability negotiation
at registration time — no raw access to internals is ever granted.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PluginManifest:
    """Immutable declaration of a plugin's identity, event contract,
    and required kernel capabilities."""

    name: str
    version: str
    description: str
    consumes_events: list[str] = field(default_factory=list)
    produces_events: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)


def validate_manifest(manifest: PluginManifest) -> None:
    """Validates the structural integrity of a PluginManifest.

    Raises:
        ManifestError: If any manifest field violates structural constraints.
    """
    from cortex.exceptions import ManifestError

    if not isinstance(manifest, PluginManifest):
        raise ManifestError(f"Expected PluginManifest instance, got {type(manifest).__name__}")

    if not isinstance(manifest.name, str) or not manifest.name.strip():
        raise ManifestError("Plugin manifest 'name' must be a non-empty string")

    if not isinstance(manifest.version, str) or not manifest.version.strip():
        raise ManifestError("Plugin manifest 'version' must be a non-empty string")

    if not isinstance(manifest.description, str):
        raise ManifestError("Plugin manifest 'description' must be a string")

    if not isinstance(manifest.consumes_events, (list, tuple)):
        raise ManifestError("Plugin manifest 'consumes_events' must be a sequence of strings")
    for item in manifest.consumes_events:
        if not isinstance(item, str) or not item.strip():
            raise ManifestError("Plugin manifest 'consumes_events' elements must be non-empty strings")

    if not isinstance(manifest.produces_events, (list, tuple)):
        raise ManifestError("Plugin manifest 'produces_events' must be a sequence of strings")
    for item in manifest.produces_events:
        if not isinstance(item, str) or not item.strip():
            raise ManifestError("Plugin manifest 'produces_events' elements must be non-empty strings")

    if not isinstance(manifest.required_capabilities, (list, tuple)):
        raise ManifestError("Plugin manifest 'required_capabilities' must be a sequence of strings")
    for item in manifest.required_capabilities:
        if not isinstance(item, str) or not item.strip():
            raise ManifestError("Plugin manifest 'required_capabilities' elements must be non-empty strings")


# -----------------------------------------------------------------------
# Reference Manifests — canonical examples of domain plugin declarations
# -----------------------------------------------------------------------

ROBOT_ARM_MANIFEST = PluginManifest(
    name="robot-arm-driver",
    version="0.1.0",
    description="Interface for 6-DOF industrial robot arm",
    consumes_events=["CommandIssuedEvent"],
    produces_events=["DriverTelemetryEvent"],
    required_capabilities=["hardware.actuators.execute", "hardware.telemetry.read"],
)

AGENT_PLANNER_MANIFEST = PluginManifest(
    name="llm-task-planner",
    version="0.1.0",
    description="Decomposes goal intents into step-wise plans",
    consumes_events=["IntentEvent"],
    produces_events=["PlanGeneratedEvent"],
    required_capabilities=["workflow.plan.create"],
)

VERIFICATION_SERVICE_MANIFEST = PluginManifest(
    name="verification-service",
    version="0.1.0",
    description="Formal verification oracle for CommitContractV1",
    consumes_events=["DriverTelemetryEvent", "CommitEventV1"],
    produces_events=["VerificationResultEvent"],
    required_capabilities=["verification.oracle.execute", "verification.invariant.check"],
)
