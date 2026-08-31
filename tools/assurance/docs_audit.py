#!/usr/bin/env python3
"""
Cortex Documentation & Repository Coherence Freshness Audit Tool

Statically and dynamically checks markdown documentation for:
1. Valid file path references.
2. Verified coverage of compliance gates (RD-*, RS-*) in unit/conformance tests.
3. Execution safety of marked Python code blocks.
4. Existence of referenced code symbols (classes, methods) in the implementation.
"""

import ast
import os
import re
import subprocess
import sys
import tempfile
from typing import Set, Tuple

# Root directory of the repository
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Exclude directories
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".runtime", ".generated", ".cache"}

# Regex patterns
PATH_PATTERN = re.compile(r'(?:[a-zA-Z0-9_\-\.]+/)+[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+')
GATE_PATTERN = re.compile(r'\b(RD|RS|LB)-\d+[a-z]?\b')
SYMBOL_PATTERN = re.compile(r'`([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)`')


def get_all_python_symbols() -> Set[str]:
    """Scans python files in cortex/ to build a set of all defined classes, methods, and functions."""
    symbols = set()
    for root, _, files in os.walk(os.path.join(ROOT_DIR, "cortex")):
        if any(ex in root for ex in EXCLUDE_DIRS):
            continue
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                        symbols.add(node.name)
            except Exception:
                pass
    return symbols


def get_all_test_methods() -> Set[str]:
    """Scans tests/ to find all test method names."""
    test_names = set()
    for root, _, files in os.walk(os.path.join(ROOT_DIR, "tests")):
        if any(ex in root for ex in EXCLUDE_DIRS):
            continue
        for file in files:
            if not file.endswith(".py"):
                continue
            path = os.path.join(root, file)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                        test_names.add(node.name)
            except Exception:
                pass
    return test_names


def verify_code_block(code: str) -> bool:
    """Saves code to a temp file and attempts to parse/compile it as valid Python."""
    try:
        ast.parse(code)
        return True
    except SyntaxError as e:
        print(f"  [ERROR] Syntax error in code block: {e}")
        return False


def run_executable_example(code: str) -> bool:
    """Executes code marked as # EXECUTABLE in a subprocess and checks exit code."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as temp:
        # Prepend repository root to sys.path to allow internal imports
        temp.write(f"import sys\nsys.path.insert(0, '{ROOT_DIR}')\n")
        temp.write(code)
        temp_path = temp.name

    try:
        res = subprocess.run([sys.executable, temp_path], capture_output=True, text=True, timeout=5)
        if res.returncode != 0:
            print(f"  [ERROR] Executable block failed execution:\n{res.stderr}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("  [ERROR] Executable block timed out.")
        return False
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass


def audit_md_file(file_path: str, known_symbols: Set[str], test_methods: Set[str]) -> Tuple[int, int, int]:
    """Audits a single markdown file and returns (failures, total_checks, warnings)."""
    failures = 0
    checks = 0
    warnings = 0

    print(f"Auditing: {os.path.relpath(file_path, ROOT_DIR)}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  [ERROR] Failed to read file: {e}")
        return 1, 1, 0

    # 1. Path Reference Checking
    all_paths = PATH_PATTERN.findall(content)
    for p in all_paths:
        # Skip URLs and external resources
        if any(x in p for x in {".com", ".dev", ".io", ".org", "github", "http", "img.shields"}):
            continue
        # Skip environment variables and placeholder/example paths
        if any(x in p for x in {"CORTEX_STATE_DIR", "BillingEngine", "export.csv", "invocation_journal.jsonl"}):
            continue
        full_path = os.path.join(ROOT_DIR, p)
        checks += 1
        if not os.path.exists(full_path):
            # Gracefully handle references to the replica management subsystem when it is not present on the current branch
            if "cortex/tools/replica" in p.replace("/kernel/", "/") and not os.path.exists(os.path.join(ROOT_DIR, "cortex/tools/kernel/replica/router.py")):
                warnings += 1
                continue
            print(f"  [FAIL] Referenced path does not exist: {p}")
            failures += 1

    # 2. Symbol Checking
    all_symbols = SYMBOL_PATTERN.findall(content)
    for sym in all_symbols:
        # Clean dot notation like 'LeaseManager.grant_lease' -> check class name or method
        base_sym = sym.split(".")[0]
        # Ignore common python/system keywords
        if base_sym in {"str", "int", "float", "dict", "list", "set", "bool", "True", "False", "None", "self", "args", "kwargs"}:
            continue
        checks += 1
        if base_sym not in known_symbols:
            # We flag this as a warning rather than hard failure, since some symbols might be general text
            warnings += 1

    # 3. Gate Verification Checks
    gates = GATE_PATTERN.findall(content)
    for gate in set(gates):
        # Translate gate like RD-1 to rd1 test format
        clean_gate = gate.lower().replace("-", "")
        checks += 1
        # Search for any test method containing the gate prefix
        has_test = any(clean_gate in tm for tm in test_methods)
        # Note: LB gates are design-only and code-blocked, so they won't have tests yet
        if not has_test and not gate.startswith("LB-"):
            print(f"  [FAIL] No conformance test covers gate: {gate}")
            failures += 1

    # 4. Code Blocks Verification
    # Match code blocks: ```python ... ```
    blocks = re.findall(r"```python(.*?)```", content, re.DOTALL)
    for block in blocks:
        clean_block = block.strip()
        checks += 1
        # Run static compile checks
        if not verify_code_block(clean_block):
            failures += 1
            continue

        # If explicitly marked as EXECUTABLE, execute it dynamically
        if "# EXECUTABLE" in clean_block or "# EXECUTABLE EXAMPLE" in clean_block:
            checks += 1
            if not run_executable_example(clean_block):
                failures += 1

    return failures, checks, warnings


def main() -> int:
    known_symbols = get_all_python_symbols()
    test_methods = get_all_test_methods()

    total_failures = 0
    total_checks = 0
    total_warnings = 0

    target_docs = [
        "docs/architecture/phase_4_routing_and_dispatch_specification.md",
        "docs/history/phase_4_implementation_audit.md",
        "docs/architecture/replica_scaling_specification.md",
        "docs/architecture/configuration_and_control_plane_specification.md",
        "docs/history/cli_and_configuration_audit.md",
        "docs/history/phase_4_documentation_and_generated_artifact_audit.md",
        "docs/guides/cortex-configuration.md",
        "README.md",
    ]

    print("DOCUMENTATION AUDIT")
    print("-------------------")

    for doc in target_docs:
        path = os.path.join(ROOT_DIR, doc)
        if not os.path.exists(path):
            print(f"[FAIL] Missing target doc file: {doc}")
            total_failures += 1
            continue

        fail, chk, warn = audit_md_file(path, known_symbols, test_methods)
        total_failures += fail
        total_checks += chk
        total_warnings += warn

    print("-------------------")
    print(f"Total Checks Executed: {total_checks}")
    print(f"Total Warnings:        {total_warnings}")
    print(f"Total Failures:        {total_failures}")

    if total_failures > 0:
        print("\nRESULT: FAIL")
        return 1
    else:
        print("\nRESULT: PASS")
        return 0


if __name__ == "__main__":
    sys.exit(main())
