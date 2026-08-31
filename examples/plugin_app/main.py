"""
Main entry point for 04_plugin_app.
Demonstrates standard Python plugin discovery and capability-managed execution.
"""

from cortex import BaseEvent, BasePlugin, CortexClient, PluginManifest

from .plugins.analysis.tasks import analyze_payload
from .plugins.ingestion.tasks import read_payload


class StandardPythonPlugin(BasePlugin):
    """Standard pure Python plugin implementing Cortex BasePlugin contract."""

    def on_event(self, event: BaseEvent) -> None:
        pass


def run_plugin_pipeline() -> dict:
    """Demonstrates registering pure Python plugins with CortexClient."""
    client = CortexClient()

    # 1. Register Ingestion Plugin
    ingest_manifest = PluginManifest(
        name="ingestion",
        version="1.0.0",
        description="Standard Python Ingestion Plugin",
        required_capabilities=["fs.read"],
    )
    ingest_plugin = StandardPythonPlugin(ingest_manifest)
    _ = client.register_plugin(ingest_plugin)

    # 2. Register Analysis Plugin
    analysis_manifest = PluginManifest(
        name="analysis",
        version="1.0.0",
        description="Standard Python Analysis Plugin",
        required_capabilities=["workflow.plan.create"],
    )
    analysis_plugin = StandardPythonPlugin(analysis_manifest)
    _ = client.register_plugin(analysis_plugin)

    # 3. Execute Plugin Tasks
    payload = read_payload("SRC-9901")
    analysis = analyze_payload(payload)

    return {
        "source": payload["source_id"],
        "metrics": analysis["metrics"],
        "plugins_registered": ["ingestion", "analysis"],
    }


def main():
    print("=== CORTEX 04_PLUGIN_APP (STANDARD PYTHON PLUGINS) ===")
    res = run_plugin_pipeline()
    print(f"Source ID:          {res['source']}")
    print(f"Metrics:            {res['metrics']}")
    print(f"Registered Plugins: {res['plugins_registered']}")


if __name__ == "__main__":
    main()
