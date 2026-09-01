# 03_workflow_app: Canonical Document Pipeline Workflow

Canonical real-world workflow application demonstrating task orchestration, state tracking, and retry semantics.

## Core Concepts Illustrated

1. Workflow orchestration via `CortexClient.create_workflow()` and `CortexClient.run_workflow()`.
2. Multi-stage pipelines (Ingestion $\rightarrow$ Analysis $\rightarrow$ Export).
3. Task isolation with declarative resource bounds.

## Directory Structure

```
03_workflow_app/
├── cortex.yaml
├── main.py
├── tasks/
│   ├── ingestion.py
│   ├── analysis.py
│   └── export.py
├── workflows/
│   └── document_workflow.py
├── tests/
│   └── test_workflow_app.py
└── README.md
```

## How to Run

```bash
uv run python -m examples.03_workflow_app.main
```

## How to Test

```bash
uv run python -m unittest discover -s examples/03_workflow_app/tests
```
