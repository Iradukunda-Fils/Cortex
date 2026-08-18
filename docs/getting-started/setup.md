# Cortex Development Environment Setup

This guide provides step-by-step instructions for setting up a reproducible Cortex development environment on macOS or Linux.

---

## System Prerequisites

| Tool | Version | Required For |
|:--|:--|:--|
| Python | 3.10+ (3.12+ recommended) | Core runtime, tests, CLI |
| [uv](https://docs.astral.sh/uv/) | Latest | Package management (primary) |
| Git | 2.x+ | Version control |
| Rust toolchain | Stable | `cortex-emulator/` only |
| Coq | 8.18 | `verification/` proofs only |
| Verilator | 5.x+ | RTL simulation only |

> **Note:** Rust, Coq, and Verilator are only required if you are modifying the emulator, formal proofs, or RTL targets respectively. Most contributors only need Python + uv.

---

## Quick Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Iradukunda-Fils/Cortex.git
cd Cortex
```

### 2. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install All Dependencies

```bash
uv sync --all-extras
```

This creates a `.venv/` virtual environment and installs all runtime and development dependencies, including:
- `ruff` — linting and formatting
- `pyright` — strict type checking
- `pre-commit` — git commit hook management
- `build` — package building

### 4. Enable Pre-Commit Hooks (Recommended)

```bash
uv run pre-commit install
```

This installs lightweight git commit hooks that run formatting and linting automatically before each commit.

### 5. Verify Your Setup

Run the canonical one-command verification gate:

```bash
./scripts/verify.sh
```

Or execute individual steps:

```bash
# Lockfile validation
uv lock --check

# Spec freeze check
./scripts/check_contract_freeze.sh

# Lint check
uv run ruff check .

# Type safety analysis
uv run pyright

# Run all tests
uv run python -m unittest discover -s tests -v
```

All commands should complete without errors.

---

## Reproducible Dependency Policy (`uv.lock`)

Cortex uses `uv.lock` to guarantee 100% deterministic dependencies across local development and CI pipelines:
- **Lockfile Enforcement**: `uv.lock` is committed to git and validated in CI via `uv lock --check`.
- **Synchronization**: Always use `uv sync --all-extras` to update your local `.venv/` to match `uv.lock`.
- **Modifying Dependencies**: Edit `pyproject.toml` and run `uv lock` to update the lockfile. Commit both `pyproject.toml` and `uv.lock` together.

---

## Alternative: pip Setup

If you prefer standard `pip` over `uv`:

```bash
python3 -m venv .venv
source .venv/bin/activate  # On macOS/Linux
pip install -e ".[dev]"
```

---

## Rust Emulator Setup (Optional)

Only needed for changes in `cortex-emulator/`:

```bash
# Install Rust (if not installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Build and test the emulator
cd cortex-emulator
cargo fmt --check
cargo clippy -- -D warnings
cargo test --verbose
```

---

## Coq Proof Environment (Optional)

Only needed for changes in `verification/`:

```bash
# Using Docker (recommended — matches CI exactly)
docker run --rm --user root \
  -v $(pwd):/workspace \
  -w /workspace/verification \
  -e OPAMROOT=/home/coq/.opam \
  coqorg/coq:8.18-ocaml-4.14-flambda \
  sh -c 'eval $(opam env --switch=default --set-root) && coq_makefile -f _CoqProject -o Makefile.coq && make -f Makefile.coq'
```

Or install Coq 8.18 natively via [opam](https://opam.ocaml.org/).

---

## RTL Simulation Setup (Optional)

Only needed for SystemVerilog RTL targets:

```bash
# Install Verilator (Ubuntu/Debian)
sudo apt-get install verilator

# Build and run RTL simulation
make verilate
make run-rtl
```

---

## Project Structure Overview

```
Cortex/
├── cortex/                  # Public Python API package
│   ├── schema/              # Event and workflow schemas
│   ├── tools/
│   │   ├── cli/             # CLI entry point
│   │   ├── kernel/          # Internal kernel engine
│   │   └── verification/    # Verification tooling
│   ├── client.py            # CortexClient public interface
│   ├── plugin.py            # BasePlugin, PluginContext, Capability
│   └── exceptions.py        # Public exception hierarchy
├── contracts/               # Internal state protocol contracts
├── tests/
│   ├── kernel/              # Kernel runtime & public API tests
│   ├── conformance/         # Cross-platform conformance tests
│   ├── golden/              # Golden hash corpus
│   └── certification/       # Certification test vectors
├── cortex-emulator/         # Rust hardware state machine emulator
├── verification/            # Coq formal proof scripts
├── rtl/                     # SystemVerilog RTL sources
├── docs/                    # Documentation
├── examples/                # Example applications
│   └── repo_auditor/        # Repo Auditor dogfood application
└── scripts/                 # Build and verification scripts
```

---

## Troubleshooting

### `pyright` reports import errors

Ensure you installed with `--all-extras`:

```bash
uv sync --all-extras
```

### Tests fail with `ModuleNotFoundError`

Ensure the package is installed in editable mode:

```bash
uv pip install -e ".[dev]"
```

### Coq proofs fail locally

Use the Docker-based verification method described above to match the CI environment exactly.

---

## What's Next?

Once your environment is set up:

1. Read the [Contributing Guide](../../CONTRIBUTING.md) for workflow and PR conventions.
2. Review the [Architecture Documentation](../architecture.md) for codebase context.
3. Check the [CLI Reference](../cli.md) for available commands.
4. Explore the [Plugin Manifest Specification](../manifest_spec.md) if building plugins.
