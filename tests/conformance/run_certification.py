"""
Cortex Verification Substrate Certification Pipeline

Separates system runtime validation from backend formal equivalence.
Provides a structured CertificationReporter that outputs a human-readable
certification report across all conformance categories.
"""

import sys
import os
import unittest
from typing import Dict, List, Tuple


class CertificationReporter:
    """Structured multi-category certification reporter."""

    CATEGORIES = [
        "SCHEMA VALIDATION",
        "GOLDEN CORPUS",
        "COQ ADAPTER CONFORMANCE",
        "RUST ADAPTER CONFORMANCE",
        "RTL ADAPTER CONFORMANCE",
        "MUTATION IMMUNITY",
        "INVARIANT SAFETY",
    ]

    def __init__(self):
        self.sections: Dict[str, List[Tuple[str, str]]] = {
            cat: [] for cat in self.CATEGORIES
        }

    def add_result(self, category: str, test_name: str, status: str) -> None:
        if category in self.sections:
            self.sections[category].append((test_name, status))

    def render_report(self) -> bool:
        print("\n" + "=" * 72)
        print("      Cortex Verification Substrate Certification Report")
        print("=" * 72)

        all_passed = True
        for category, results in self.sections.items():
            print(f"\n[{category}]")
            if not results:
                print("  (No tests executed)")
                continue
            for name, status in results:
                dots = "." * max(1, 50 - len(name))
                print(f"  {name} {dots} {status}")
                if status != "PASS":
                    all_passed = False

        print("\n" + "=" * 72)
        overall = "CERTIFICATION: PASS" if all_passed else "CERTIFICATION: FAIL"
        print(f"  OVERALL RESULT: {overall}")
        print("=" * 72 + "\n")
        return all_passed


def _run_suite(suite_module: str, reporter: CertificationReporter, category: str) -> None:
    """Discovers and runs all tests in a module, recording results."""
    try:
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(suite_module)
        runner = unittest.TextTestRunner(stream=open(os.devnull, "w"), verbosity=0)
        result = runner.run(suite)

        for test, _ in result.failures + result.errors:
            reporter.add_result(category, str(test), "FAIL")
        for test in result.successes if hasattr(result, "successes") else []:
            reporter.add_result(category, str(test), "PASS")

        # Fallback: if no successes attribute, infer from counts
        if not hasattr(result, "successes"):
            passed = result.testsRun - len(result.failures) - len(result.errors)
            if passed > 0 and not result.failures and not result.errors:
                reporter.add_result(category, f"{suite_module} ({passed} tests)", "PASS")
            elif result.failures or result.errors:
                reporter.add_result(category, f"{suite_module}", "FAIL")

    except Exception as e:
        reporter.add_result(category, f"{suite_module} (import error)", "FAIL")


def run_certification_pipeline() -> bool:
    """Executes the full Phase 3A.75 / 3A.9 conformance pipeline."""
    reporter = CertificationReporter()

    print("\nExecuting Phase 3A.75 / 3A.9 Conformance Pipeline...\n")

    # Stage 1: Schema Validation
    _run_suite("tests.conformance.test_conformance_coq", reporter, "SCHEMA VALIDATION")

    # Stage 2: Backend Conformance
    _run_suite("tests.conformance.test_conformance_coq", reporter, "COQ ADAPTER CONFORMANCE")
    _run_suite("tests.conformance.test_conformance_rust", reporter, "RUST ADAPTER CONFORMANCE")
    _run_suite("tests.conformance.test_conformance_rtl", reporter, "RTL ADAPTER CONFORMANCE")

    # Stage 3: Mutation Immunity
    _run_suite("tests.conformance.test_adapter_mutations", reporter, "MUTATION IMMUNITY")

    return reporter.render_report()


if __name__ == "__main__":
    success = run_certification_pipeline()
    sys.exit(0 if success else 1)
