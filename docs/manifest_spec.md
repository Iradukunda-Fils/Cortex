# PluginManifest & Capability Negotiation Specification

The `PluginManifest` defines plugin identities, consumed and produced events, and required security capabilities.

---

## Schema Overview

```json
{
  "name": "my-plugin",
  "version": "0.1.0",
  "description": "Sample plugin",
  "consumes_events": ["IntentEvent"],
  "produces_events": ["PlanGeneratedEvent"],
  "required_capabilities": [
    "workflow.plan.create"
  ]
}
```

---

## Standard Capability Namespaces

| Namespace | Example Capability | Description |
| :--- | :--- | :--- |
| `workflow.*` | `workflow.plan.create` | Generating plan events |
| `workflow.*` | `workflow.command.issue` | Issuing executable command events |
| `fs:*` | `fs:read` | Read-only file system operations |
| `exec:*` | `exec:git`, `exec:pytest` | Subprocess execution capabilities |
| `hardware.*` | `hardware.telemetry.read` | Hardware sensor and telemetry monitoring |

---

## Sandboxing Behavior

When a plugin is registered with `CortexClient.register_plugin(plugin)`:
1. `CapabilityNegotiator` matches required capabilities against `platform_capabilities`.
2. Granted capabilities are attached to the plugin's `PluginContext`.
3. Any unauthorized capability requests reject the plugin and log a `CAPABILITY_VIOLATION` event during workflow execution.
