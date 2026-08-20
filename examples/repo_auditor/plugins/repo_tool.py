"""
Read-Only Repository Tool Plugin with Capability Security Sandbox Enforcement

This plugin executes read-only repository inspection actions (git status, linter,
tests) within the Cortex event pipeline. All actions are gated by capability
checks and produce DriverTelemetryEvent + VerificationResultEvent pairs.

The plugin is intentionally deterministic: it reports synthetic pass/fail results
based on capability authorization, not live subprocess output. This ensures
replay equivalence in the dogfood harness and test suite. For real tool execution,
use the CLI entrypoint (main.py) which orchestrates actual subprocess calls
outside the event pipeline.
"""

from cortex import (
    BaseEvent,
    BasePlugin,
    CommandIssuedEvent,
    DriverTelemetryEvent,
    PluginManifest,
    VerificationResultEvent,
)
from cortex.compat import override

REPO_TOOL_MANIFEST = PluginManifest(
    name="auditor-repo-tool",
    version="0.3.0",
    description="Executes read-only repository inspection tools (git status, linter, tests)",
    consumes_events=["CommandIssuedEvent"],
    produces_events=["DriverTelemetryEvent", "VerificationResultEvent"],
    required_capabilities=["fs:read", "exec:git", "exec:pytest", "hardware.telemetry.read"],
)


class ReadOnlyRepoToolPlugin(BasePlugin):
    """Read-only repository tool driver.

    Consumes ``CommandIssuedEvent`` and produces telemetry + verification
    result pairs. Sandbox violation simulation is opt-in via the
    ``simulate_sandbox_violation`` constructor flag.
    """

    simulate_sandbox_violation: bool

    def __init__(self, simulate_sandbox_violation: bool = False) -> None:
        super().__init__(REPO_TOOL_MANIFEST)
        self.simulate_sandbox_violation = simulate_sandbox_violation

    @override
    def on_event(self, event: BaseEvent) -> None:
        match event:
            case CommandIssuedEvent() if self.context:
                if self.simulate_sandbox_violation:
                    # Attempt unauthorized action requiring fs:write capability
                    if not self.context.has_capability("fs:write"):
                        violation_event = VerificationResultEvent(
                            workflow_id=event.workflow_id,
                            causation_id=event.command_id,
                            passed=False,
                            rule_id="CAPABILITY_VIOLATION",
                            details={
                                "attempted_capability": "fs:write",
                                "action": event.action,
                                "reason": "Unauthorized file system write operation rejected by CapabilitySandbox",
                            },
                        )
                        self.context.publish(violation_event)
                        return

                # Normal Authorized Read-Only Execution
                if self.context.has_capability("fs:read"):
                    result_payload: dict[str, object] = {
                        "action": event.action,
                        "result": "clean",
                    }

                    telemetry = DriverTelemetryEvent(
                        workflow_id=event.workflow_id,
                        causation_id=event.command_id,
                        driver_id="repo_tool_driver",
                        status="ok",
                        payload=result_payload,
                    )
                    self.context.publish(telemetry)

                    verification = VerificationResultEvent(
                        workflow_id=event.workflow_id,
                        causation_id=event.command_id,
                        passed=True,
                        rule_id="REPO_AUDIT_PASS",
                        details={"action": event.action, "status": "VERIFIED"},
                    )
                    self.context.publish(verification)

            case _:
                pass
