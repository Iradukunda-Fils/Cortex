# Cortex Release Process, Governance & Deployment Protocol

> **Document Version**: `1.0.0` | **Target Release**: `v0.7.0rc1` & `v1.0.0` Baseline  
> **Status**: Normative Release Protocol | **Security Standard**: Fail-Closed Release Invariant

---

## 1. Governing Release Principle

Cortex enforces the **Immutable Release-Identity Invariant**:

$$ \boxed{ \text{Audited Source} = \text{Tested Source} = \text{Built Artifact} = \text{Tagged Release} } $$

No binary package, wheel, or release tag may be published to PyPI or distributed to production unless the source commit has passed the **Hierarchical Verification Substrate Gate** and its SHA256 build checksums are recorded in the release manifest.

---

## 2. Step-by-Step Release Protocol

```
[ Step 1: Feature Freeze & Verification ]
       │
       ▼
[ Step 2: Quality & Conformance Gate Execution ]
       │
       ▼
[ Step 3: Package Build & SHA256 Checksum Calculation ]
       │
       ▼
[ Step 4: Version Bump & Release Tag Assignment ]
       │
       ▼
[ Step 5: Automated PyPI OIDC Trusted Publishing ]
       │
       ▼
[ Step 6: Release Manifest Audit & Verification Gate ]
```

### Step 1: Pre-Release Verification & Code Freeze
1. Ensure `git status --porcelain` is clean with zero uncommitted changes or untracked files.
2. Confirm architectural freeze: $\Delta \text{Architecture} = 0$.

### Step 2: Run Full Conformance & Verification Battery
Execute the canonical release integrity battery:
```bash
# 1. Code quality and type safety
uv run ruff check .

# 2. Conformance and integration suites
uv run python -m unittest discover -s tests/conformance
uv run python -m unittest discover -s examples/secure_external_effect_plugin/tests
uv run python -m unittest discover -s examples/mcp_secure_effect_app/tests

# 3. Rust emulator and Go codecs
cargo test --manifest-path cortex-emulator/Cargo.toml
cd cortex-go && go test -v ./...
```

### Step 3: Package Build & Checksum Recording
Construct distribution artifacts using `uv`:
```bash
uv build
sha256sum dist/*
```
Record the resulting SHA256 checksums in the release manifest (`docs/release/v0.7.0rc1_release_manifest.md`).

### Step 4: Tag Assignment & Verification
Create an annotated or lightweight release tag:
```bash
git tag -a v0.7.0rc1 -m "Release Candidate v0.7.0rc1: External Effects & Containment Kernel"
git push origin v0.7.0rc1
```

### Step 5: PyPI OIDC Trusted Publishing (CI/CD)
When tag `v*` is pushed to GitHub:
1. `.github/workflows/pypi.yml` triggers automatically.
2. The `test` job runs `./scripts/verify.sh`.
3. Upon 100% pass, the `publish` job authenticates with PyPI via **OIDC Keyless Trusted Publishing** (`permissions: id-token: write`).
4. Artifacts are built clean and uploaded directly to PyPI.

---

## 3. Mandatory Security & Release Gates

| Gate Name | Execution Scope | Enforcement Level | Fail Action |
| :--- | :--- | :--- | :--- |
| **Lint & Type Gate** | `ruff check` | Blocking | Reject Build |
| **Python Conformance** | `tests/conformance` | Blocking | Reject Build |
| **Rust Containment Gate** | `cortex-emulator cargo test` | Blocking | Reject Build |
| **Coq Proof Gate** | `verification/*.v` (0 Admits) | Blocking | Reject Build |
| **PyPI OIDC Gate** | PyPI Keyless OIDC Token | Blocking | Abort Upload |

---

## 4. Post-Release Audit Verification

After release publication, verify PyPI index availability and installability:
```bash
uv pip install cortex-runtime==0.7.0rc1
python -c "import cortex; print(cortex.__version__)"
```
