# Contributing to Cortex Platform

Thank you for your interest in contributing to **Cortex Platform**!

Cortex is an open-source spatiotemporal authority and semantic verification framework designed for high-assurance execution integrity across software runtimes and AI agent architectures.

---

## 🚀 Quick Start for Contributors

1. **Fork & Clone the Repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Cortex.git
   cd Cortex
   ```

2. **Set Up the Development Environment (via Astral `uv`)**:
   ```bash
   uv venv && source .venv/bin/activate
   uv sync --all-extras
   ```

3. **Run the Local Canonical Verification Gate**:
   Before submitting any changes, ensure all quality and test gates pass:
   ```bash
   ./scripts/verify.sh
   ```

---

## 📖 Pull Request & Issue Guidelines

Please review our formal governance guides before opening a PR or Issue:

- **[Pull Request & Merge Governance Guide](docs/governance/contributor_pr_and_merge_guide.md)**: Conventional Commits, branch naming conventions, and automated merge gates.
- **[Documentation Portal](docs/README.md)**: System architecture specifications, security dossiers, and proof inventories.
- **[Issue Templates](.github/ISSUE_TEMPLATE/)**: Structured forms for feature proposals, bug reports, and Coq formal proof obligations.

---

## 📜 Code of Conduct & Licensing

By contributing to Cortex, you agree that your contributions will be licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.
