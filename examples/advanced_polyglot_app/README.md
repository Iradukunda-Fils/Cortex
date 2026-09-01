# 05_advanced_polyglot_app: Advanced Native Substrate Integration

Demonstrates multi-language native integration (C, C++, Rust FFI) with Cortex tasks under low-resource constraints.

> [!IMPORTANT]
> **CLASSIFICATION**: ADVANCED SUBSTRATE INTEGRATION  
> This example demonstrates optional low-level native extension boundaries. It is **NOT** the standard Cortex application model. Standard Cortex applications and plugins do not require native compilation, C/C++/Rust code, or `binding.py` adapter layers.

## Core Concepts Illustrated

1. Native FFI integration using C (`c_fast_math`), C++ (`cpp_tensor_engine`), and Rust (`rust_secure_checksum`).
2. `CentralPluginLoader` pattern with automatic zero-overhead Python fallbacks on low-resource machines lacking native toolchains.
3. Multi-language task orchestration under Cortex resource governance.

## Directory Structure

```
05_advanced_polyglot_app/
├── cortex.yaml
├── main.py
├── tasks.py
├── workflows/
│   └── polyglot_workflow.py
├── plugins/
│   ├── plugin_loader.py
│   ├── c_fast_math/
│   ├── cpp_tensor_engine/
│   └── rust_secure_checksum/
├── tests/
│   └── test_polyglot_app.py
└── README.md
```

## How to Run

```bash
uv run python -m examples.05_advanced_polyglot_app.main
```

## How to Test

```bash
uv run python -m unittest discover -s examples/05_advanced_polyglot_app/tests
```
