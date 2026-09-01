# 02_resource_aware_app: Cortex Resource-Aware Application

Demonstrates the Level 2 Developer API for expressing resource constraints (CPU, RAM, GPU, VRAM).

## Core Concepts Illustrated

1. Declarative resource requirements using standard string units (`"2"`, `"4GiB"`, `"8GiB"`).
2. Developer Intent model: $\boxed{\text{Declare Need} \rightarrow \text{Cortex Handles Reservation}}$.
3. Automatic unit parsing and normalization to millicores and bytes.

## Directory Structure

```
02_resource_aware_app/
├── cortex.yaml
├── main.py
├── tasks.py
├── tests/
│   └── test_resource_aware_app.py
└── README.md
```

## How to Run

```bash
uv run python -m examples.02_resource_aware_app.main
```

## How to Test

```bash
uv run python -m unittest discover -s examples/02_resource_aware_app/tests
```
