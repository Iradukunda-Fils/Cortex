# 01_minimal_app: Cortex Minimal Application

The smallest valid Cortex application, demonstrating the Level 1 Developer API.

## Core Concepts Illustrated

1. Zero-configuration `@cortex.task` functions.
2. Clean task execution with default resource bounds (1 CPU core, 512MiB RAM).
3. Minimal project structure requiring only Python, Cortex, and a standard `cortex.yaml`.

## Directory Structure

```
01_minimal_app/
├── cortex.yaml
├── main.py
├── tasks.py
├── tests/
│   └── test_minimal_app.py
└── README.md
```

## How to Run

```bash
uv run python -m examples.01_minimal_app.main
```

## How to Test

```bash
uv run python -m unittest discover -s examples/01_minimal_app/tests
```
