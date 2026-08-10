"""
v0.2.0 Regression: Documentation Code Snippet Executability & SDK Surface Verification

Validates that all Python code snippets presented in developer documentation
(quickstart.md, plugin-authoring.md) execute cleanly using the public SDK surface
and do NOT import from internal kernel modules.
"""

import re
import unittest
from pathlib import Path

from cortex import (
    BaseEvent,
    BasePlugin,
    CommandIssuedEvent,
    CortexClient,
    DriverTelemetryEvent,
    IntentEvent,
    PlanGeneratedEvent,
    PluginManifest,
    VerificationResultEvent,
    WorkflowState,
)
from cortex.compat import override


class TestDocSnippetsPublicSDKImports(unittest.TestCase):
    """Assert that documentation markdown Python code blocks contain zero internal module leaks."""

    def test_doc_files_do_not_import_internal_modules(self) -> None:
        """Python code blocks in docs/ must not contain imports from cortex.tools.*."""
        docs_dir = Path(__file__).resolve().parent.parent.parent / "docs"
        md_files = list(docs_dir.glob("**/*.md"))
        self.assertTrue(len(md_files) > 0, "No markdown files found in docs/")

        # Match python code blocks in markdown
        code_block_pattern = re.compile(r"```python\s*(.*?)```", re.DOTALL)
        internal_import_pattern = re.compile(r"from\s+cortex\.tools")

        for md_path in md_files:
            with self.subTest(file=md_path.name):
                content = md_path.read_text(encoding="utf-8")
                blocks = code_block_pattern.findall(content)
                for i, block in enumerate(blocks):
                    matches = internal_import_pattern.findall(block)
                    self.assertEqual(
                        matches,
                        [],
                        f"Doc file '{md_path.relative_to(docs_dir)}' code block #{i+1} contains internal import 'from cortex.tools'",
                    )


class TestDocQuickstartSnippetExecution(unittest.TestCase):
    """Execute the canonical 5-minute quickstart workflow snippet."""

    def test_quickstart_workflow_executes_cleanly(self) -> None:
        """Quickstart 2-plugin workflow runs to completion with public SDK."""
        planner_manifest = PluginManifest(
            name="quickstart-planner",
            version="0.1.0",
            description="Decomposes intent into actionable steps",
            consumes_events=["IntentEvent"],
            produces_events=["PlanGeneratedEvent"],
            required_capabilities=["workflow.plan.create"],
        )

        executor_manifest = PluginManifest(
            name="quickstart-executor",
            version="0.1.0",
            description="Executes planned steps with capability guardrails",
            consumes_events=["PlanGeneratedEvent"],
            produces_events=["DriverTelemetryEvent", "VerificationResultEvent"],
            required_capabilities=["fs:read"],
        )

        class QuickstartPlanner(BasePlugin):
            def __init__(self) -> None:
                super().__init__(planner_manifest)

            @override
            def on_event(self, event: BaseEvent) -> None:
                match event:
                    case IntentEvent() if self.context and self.context.has_capability("workflow.plan.create"):
                        plan = PlanGeneratedEvent(
                            workflow_id=event.workflow_id,
                            intent_id=event.intent_id,
                            causation_id=event.event_id,
                            steps=[{"step": 1, "action": "check_workspace", "target": "."}],
                        )
                        self.context.publish(plan)
                    case _:
                        pass

        class QuickstartExecutor(BasePlugin):
            def __init__(self) -> None:
                super().__init__(executor_manifest)

            @override
            def on_event(self, event: BaseEvent) -> None:
                match event:
                    case PlanGeneratedEvent() if self.context and self.context.has_capability("fs:read"):
                        for step in event.steps:
                            telemetry = DriverTelemetryEvent(
                                workflow_id=event.workflow_id,
                                causation_id=event.event_id,
                                driver_id="quickstart_driver",
                                status="ok",
                                payload=step,
                            )
                            self.context.publish(telemetry)

                            verification = VerificationResultEvent(
                                workflow_id=event.workflow_id,
                                causation_id=event.event_id,
                                passed=True,
                                rule_id="QUICKSTART_PASS",
                                details={"target": step.get("target")},
                            )
                            self.context.publish(verification)
                    case _:
                        pass

        client = CortexClient()
        client.register_plugin(QuickstartPlanner())
        client.register_plugin(QuickstartExecutor())

        wf = client.create_workflow(name="QuickstartWorkflow", goal="Demonstrate Cortex SDK")
        intent = IntentEvent(workflow_id=wf.workflow_id, goal="Verify Workspace")
        executed_wf = client.run_workflow(wf, initial_intent=intent)

        self.assertEqual(executed_wf.state, WorkflowState.COMPLETED)

        log = client.event_store.get_log()
        self.assertEqual(len(log), 4)

        event_types = [type(e).__name__ for e in log]
        self.assertEqual(
            event_types,
            [
                "IntentEvent",
                "PlanGeneratedEvent",
                "DriverTelemetryEvent",
                "VerificationResultEvent",
            ],
        )


class TestPluginAuthoringGuideSnippetExecution(unittest.TestCase):
    """Execute the capability violation and handling snippets from plugin-authoring.md."""

    def test_capability_violation_handling_snippet(self) -> None:
        """Plugin attempting unauthorized capability produces failed verification."""
        manifest = PluginManifest(
            name="guarded-plugin",
            version="0.1.0",
            description="Guarded test plugin",
            consumes_events=["CommandIssuedEvent"],
            produces_events=["VerificationResultEvent"],
            required_capabilities=["fs:read"],  # Note: missing fs:write
        )

        class GuardedPlugin(BasePlugin):
            def __init__(self) -> None:
                super().__init__(manifest)

            @override
            def on_event(self, event: BaseEvent) -> None:
                match event:
                    case CommandIssuedEvent() if self.context:
                        if not self.context.has_capability("fs:write"):
                            failure = VerificationResultEvent(
                                workflow_id=event.workflow_id,
                                causation_id=event.event_id,
                                passed=False,
                                rule_id="CAPABILITY_VIOLATION",
                                details={"required": "fs:write", "status": "DENIED"},
                            )
                            self.context.publish(failure)

        client = CortexClient()
        client.register_plugin(GuardedPlugin())

        wf = client.create_workflow(name="ViolationTest", goal="Verify sandbox intercept")
        cmd = CommandIssuedEvent(
            workflow_id=wf.workflow_id,
            action="unauthorized_write",
            parameters={"target": "/etc/shadow"},
        )
        executed_wf = client.run_workflow(wf, initial_intent=cmd)  # type: ignore[arg-type]

        self.assertEqual(executed_wf.state, WorkflowState.FAILED)


if __name__ == "__main__":
    _ = unittest.main()
