"""
Cortex Project Scaffolding Engine

Scaffolds a new Cortex application or plugin project template with declarative
manifests, workflow definitions, and sample handlers adhering to public Cortex standards.
"""

import json
import os


def scaffold_project(project_name: str, project_type: str = "app", target_dir: str | None = None) -> str:
    """Scaffolds a standard Cortex application or plugin project directory structure."""
    if target_dir is None:
        target_dir = os.path.join(os.getcwd(), project_name)

    os.makedirs(target_dir, exist_ok=True)

    cortex_config: dict[str, str] = {
        "name": project_name,
        "type": project_type,
        "version": "0.1.0",
        "cortex_version": "0.2.0",
        "entrypoint": "main.py" if project_type == "app" else "plugin.py",
    }
    with open(os.path.join(target_dir, "cortex.json"), "w", encoding="utf-8") as f:
        json.dump(cortex_config, f, indent=2)

    plugin_manifest: dict[str, str | list[str]] = {
        "name": f"{project_name}-plugin",
        "version": "0.1.0",
        "description": f"Custom {project_type} plugin for {project_name}",
        "consumes_events": ["IntentEvent"],
        "produces_events": ["PlanGeneratedEvent", "CommandIssuedEvent"],
        "required_capabilities": ["workflow.plan.create", "workflow.command.issue"],
    }
    with open(os.path.join(target_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(plugin_manifest, f, indent=2)

    workflow_def: dict[str, object] = {
        "name": f"{project_name}_workflow",
        "goal": f"Execute default workflow for {project_name}",
        "policy": {
            "timeout_seconds": 300.0,
            "max_retries": 3,
            "abort_on_verification_failure": True,
        },
        "initial_intent": {
            "goal": f"Initialize {project_name} execution",
            "parameters": {"environment": "development"},
        },
    }
    with open(os.path.join(target_dir, "workflow.json"), "w", encoding="utf-8") as f:
        json.dump(workflow_def, f, indent=2)

    code_content = _generate_sample_code(project_name, project_type)
    code_filename = "main.py" if project_type == "app" else "plugin.py"
    with open(os.path.join(target_dir, code_filename), "w", encoding="utf-8") as f:
        _ = f.write(code_content)

    return target_dir


def _generate_sample_code(project_name: str, project_type: str) -> str:
    if project_type == "plugin":
        return f'''"""
Plugin Handler for {project_name}
"""

from cortex import BasePlugin, PluginManifest, IntentEvent, PlanGeneratedEvent

MANIFEST = PluginManifest(
    name="{project_name}-plugin",
    version="0.1.0",
    description="Custom plugin for {project_name}",
    consumes_events=["IntentEvent"],
    produces_events=["PlanGeneratedEvent"],
    required_capabilities=["workflow.plan.create"],
)

class CustomPlugin(BasePlugin):
    def __init__(self):
        super().__init__(MANIFEST)

    def on_event(self, event):
        if isinstance(event, IntentEvent) and self.context:
            plan = PlanGeneratedEvent(
                intent_id=event.intent_id,
                workflow_id=event.workflow_id,
                steps=[{{"step": 1, "action": "initialize"}}]
            )
            self.context.publish(plan)
'''
    return f'''"""
Application Handler for {project_name}
"""

from cortex import CortexClient, IntentEvent

def run_app():
    client = CortexClient()
    workflow = client.create_workflow(name="{project_name}_workflow", goal="Run autonomous task")
    intent = IntentEvent(workflow_id=workflow.workflow_id, goal=workflow.goal)
    executed = client.run_workflow(workflow, initial_intent=intent)
    print(f"Workflow {{executed.workflow_id}} status: {{executed.state.value}}")

if __name__ == "__main__":
    run_app()
'''
