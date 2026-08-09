# Contributing to Cortex

Thank you for your interest in contributing to Cortex! This document provides guidelines and instructions for contributing to this project.

Cortex is licensed under the [Apache License, Version 2.0](LICENSE). By contributing to this project, you agree that your contributions will be licensed under the same terms (see [Apache-2.0 Section 5](https://www.apache.org/licenses/LICENSE-2.0#contributions)).

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Environment Setup](#development-environment-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)

---

## Prerequisites

- **Python 3.10+** (3.12+ recommended)
- **[uv](https://docs.astral.sh/uv/)** — fast Python package manager (primary)
- **Git** — version control
- **Rust toolchain** — required only for `cortex-emulator/` changes
- **Coq 8.18** — required only for `verification/` proof changes

## Development Environment Setup

### 1. Clone the repository

```bash
git clone https://github.com/Iradukunda-Fils/Cortex.git
cd Cortex
```

### 2. Create a virtual environment and install dependencies

Using `uv` (recommended):

```bash
uv sync --all-extras
```

Using `pip` (fallback):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Verify your setup

Run the full verification suite to confirm everything works:

```bash
# Lint & type checking
ruff check .
pyright

# Run all tests
python3 -m unittest discover -s tests -v
```

If all checks pass, your environment is correctly configured.

For detailed environment documentation, see [docs/development/setup.md](docs/development/setup.md).

---

## Development Workflow

### 1. Create a feature branch

```bash
git checkout -b <type>/<short-description>
```

Branch naming convention:

| Prefix | Purpose |
|:--|:--|
| `feat/` | New features or capabilities |
| `fix/` | Bug fixes |
| `docs/` | Documentation changes |
| `test/` | Test additions or improvements |
| `refactor/` | Code restructuring (no behavior change) |
| `ci/` | CI/CD pipeline changes |

### 2. Make your changes

- Write clean, type-annotated Python code
- Add or update tests for any behavioral changes
- Ensure all existing tests continue to pass

### 3. Run verification locally before pushing

```bash
# Format & lint
ruff check .

# Type safety
pyright

# Test suite
python3 -m unittest discover -s tests -v
```

### 4. Push and open a Pull Request

```bash
git push origin <your-branch>
```

Open a PR against `main` via the GitHub UI.

---

## Code Standards

### Python

- **Formatter/Linter**: [Ruff](https://docs.astral.sh/ruff/) — configured in `pyproject.toml`
- **Type Checker**: [Pyright](https://github.com/microsoft/pyright) — strict mode
- **Line Length**: 120 characters maximum
- **Target Version**: Python 3.10+
- **Import Order**: Enforced by Ruff (`isort` rules enabled)

### Rust (cortex-emulator)

- **Formatting**: `cargo fmt --check`
- **Linting**: `cargo clippy -- -D warnings`
- **Tests**: `cargo test --verbose`

### General

- All public functions and classes must have docstrings
- No `# type: ignore` comments without an accompanying explanation
- Tests must exercise **public API contracts**, not internal implementation details

---

## Commit Conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/). Every commit message must use the following format:

```
<type>(<optional scope>): <description>

[optional body]

[optional footer(s)]
```

### Allowed Types

| Type | Purpose |
|:--|:--|
| `feat` | A new feature or capability |
| `fix` | A bug fix |
| `docs` | Documentation-only changes |
| `test` | Adding or updating tests |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `ci` | CI/CD configuration changes |
| `chore` | Maintenance tasks (dependency updates, tooling) |
| `perf` | Performance improvements |

### Examples

```
feat(kernel): add event replay timeout configuration
fix(cli): correct exit code for CAPABILITY_VIOLATION errors
docs: add plugin authoring guide
test(conformance): add golden corpus replay regression test
refactor(kernel): extract event serialization into dedicated module
```

### Breaking Changes

Prefix the body or footer with `BREAKING CHANGE:` to indicate a breaking API change:

```
feat(schema)!: rename WorkflowPolicy.max_retries to retry_limit

BREAKING CHANGE: WorkflowPolicy.max_retries has been renamed to retry_limit.
Update all workflow configurations accordingly.
```

---

## Pull Request Process

1. **Ensure all CI checks pass.** The [Hierarchical Verification Substrate Gate](.github/workflows/verification_gate.yml) must pass before any PR can be merged. This includes:
   - Ruff lint + Pyright type checking
   - Golden hash integrity checks
   - Kernel conformance and regression tests
   - Rust emulator tests
   - Coq proof verification

2. **One approval required.** All PRs require at least one maintainer review.

3. **Keep PRs focused.** Each PR should address a single concern (one issue, one feature, one fix). Avoid mixing unrelated changes.

4. **Write a clear PR description.** Explain *what* changed and *why*. Reference the relevant issue number (e.g., `Closes #4`).

5. **Respond to review feedback.** Address all review comments before requesting re-review.

---

## Reporting Issues

- **Bugs**: Open an issue with steps to reproduce, expected behavior, and actual behavior.
- **Feature Requests**: Open an issue describing the use case and proposed solution.
- **Security Vulnerabilities**: See [SECURITY.md](SECURITY.md) for private disclosure instructions. **Do not open public issues for security vulnerabilities.**

---

## Questions?

If you have questions about contributing that are not covered here, open a [Discussion](https://github.com/Iradukunda-Fils/Cortex/discussions) or reach out via an issue.

Thank you for helping improve Cortex.
