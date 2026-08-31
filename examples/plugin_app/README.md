# 04_plugin_app: Canonical Plugin Architecture Application

Canonical example demonstrating standard pure-Python plugin architecture and manifest contract validation.

## Architectural Principle

$$\boxed{ \text{binding.py} = \text{adapter pattern for native code, NOT standard plugin requirement} }$$

A standard Cortex plugin is pure Python and declares its capabilities in `manifest.yml`. It does not require compiled C/C++/Rust code or custom FFI bindings unless performance constraints specifically demand native extensions.

## Directory Structure

```
04_plugin_app/
├── cortex.yaml
├── main.py
├── plugins/
│   ├── ingestion/
│   │   ├── manifest.yml
│   │   └── tasks.py
│   └── analysis/
│       ├── manifest.yml
│       └── tasks.py
├── tests/
│   └── test_plugin_app.py
└── README.md
```

## How to Run

```bash
uv run python -m examples.04_plugin_app.main
```

## How to Test

```bash
uv run python -m unittest discover -s examples/04_plugin_app/tests
```
