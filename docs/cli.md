# Cortex CLI Reference

The `cortex` Developer CLI provides project scaffolding, workflow lifecycle execution, execution graph inspection, and deterministic replay capabilities.

---

## Command Overview

```text
cortex [-h] {init,workflow} ...
```

---

## 1. `cortex init`

Scaffolds a new Cortex project structure.

### Usage
```bash
cortex init <project_name> [--type {app|plugin}]
```

### Arguments
- `project_name`: Name of the directory to create.
- `--type`: Type of scaffold (`app` or `plugin`, default: `app`).

---

## 2. `cortex workflow run`

Executes a workflow defined in a JSON specification file.

### Usage
```bash
cortex workflow run <workflow_file> [--output <file>]
```

### Arguments
- `workflow_file`: Path to workflow JSON specification file.
- `--output`, `-o`: (Optional) Path to write JSON execution trace journal.

---

## 3. `cortex workflow inspect`

Inspects the causal execution graph, event node lineage, and verification failure diagnostics.

### Usage
```bash
cortex workflow inspect <workflow_id_or_file>
```

### Arguments
- `workflow_id_or_file`: Direct path to a JSON trace file or a raw workflow ID.

---

## 4. `cortex workflow replay`

Replays an event trace through the `DeterministicReplayEngine` and asserts 100% causal sequence immutability.

### Usage
```bash
cortex workflow replay <workflow_id_or_file>
```

### Arguments
- `workflow_id_or_file`: Direct path to a JSON trace file or a raw workflow ID.
