"""
Declarative Plugin Manifest Schema

Every plugin declares its event consumption/production contract and the
kernel capabilities it requires.  The Kernel enforces capability negotiation
at registration time — no raw access to internals is ever granted.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class PluginManifest:
    """Immutable declaration of a plugin's identity, event contract,
    and required kernel capabilities."""
    name: str
    version: str
    description: str
    consumes_events: List[str] = field(default_factory=list)
    produces_events: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)


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
