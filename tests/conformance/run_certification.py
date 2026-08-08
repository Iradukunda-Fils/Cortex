"""
Cortex Verification Substrate Certification Pipeline
"""

import sys
import os
import unittest
import traceback
from typing import Dict, List, Tuple


class CertificationReporter:
    """Structured multi-category certification reporter."""

    CATEGORIES = [
        "SCHEMA VALIDATION",
        "GOLDEN CORPUS VECTORS",
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
        total_checks = 0
        passed_checks = 0

        for category, results in self.sections.items():
            print(f"\n[{category}]")
            if not results:
                print("  (No tests executed)")
                continue
            for name, status in results:
                total_checks += 1
                if status == "PASS":
                    passed_checks += 1
                else:
                    all_passed = False
                dots = "." * max(1, 58 - len(name))
                print(f"  {name} {dots} {status}")

        print("\n" + "=" * 72)
        overall = f"PASS ({passed_checks}/{total_checks} Checks Verified)" if all_passed else "FAIL"
        print(f"  OVERALL RESULT: CERTIFICATION: {overall}")
        print("=" * 72 + "\n")
        return all_passed


def _run_suite(suite_module: str, reporter: CertificationReporter, category: str, name_mapping: Dict[str, str]) -> None:
    """Discovers and runs all tests in a module, recording results."""
    try:
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(suite_module)

        # Build list of all run tests recursively using generic iteration BEFORE running
        run_tests = []
        def collect_tests(suite_item):
            if isinstance(suite_item, unittest.TestCase):
                run_tests.append(suite_item)
            else:
                try:
                    for sub_item in suite_item:
                        collect_tests(sub_item)
                except TypeError:
                    pass
        collect_tests(suite)

        # Now run the suite
        runner = unittest.TextTestRunner(stream=open(os.devnull, "w"), verbosity=0)
        result = runner.run(suite)

        failed_tests = {str(test.id().split('.')[-1]) for test, _ in result.failures + result.errors}

        for test in run_tests:
            method_name = test.id().split('.')[-1]
            if method_name in name_mapping:
                display_name: str = name_mapping[method_name]
                status = "FAIL" if method_name in failed_tests else "PASS"
                reporter.add_result(category, display_name, status)

    except Exception as e:
        print(f"DEBUG: exception in {suite_module}: {e}")
        traceback.print_exc()
        reporter.add_result(category, f"{suite_module} (import error)", "FAIL")


def run_certification_pipeline() -> bool:
    """Executes the full Phase 3A.75 / 3A.9 conformance pipeline."""
    reporter = CertificationReporter()

    print("\nExecuting Phase 3A.75 / 3A.9 Conformance Pipeline...\n")

    # Mapping method names to clean readable display outputs
    schema_map = {
        "test_coq_scenario_a0_basic_commit": "CommitContractV1 JSON Schema Validation",
    }
    golden_map = {
        "test_golden_scenario_a0_basic_commit": "Golden Scenario A0 (Basic Commit)",
        "test_golden_scenario_a1_register_writes": "Golden Scenario A1 (Register Writes)",
        "test_golden_scenario_a2_memory_writes": "Golden Scenario A2 (Memory Writes)",
        "test_golden_scenario_a3_control_flow_branch": "Golden Scenario A3 (Control Flow / Branch)",
        "test_golden_scenario_a4_exception_traps": "Golden Scenario A4 (Exception Traps)",
        "test_golden_scenario_a5_multi_cycle_burst": "Golden Scenario A5 (Multi-Cycle Burst)",
    }
    coq_map = {
        "test_coq_scenario_a0_basic_commit": "Coq Scenario A0 Conformance",
        "test_coq_scenario_a1_register_writes": "Coq Scenario A1 Conformance",
        "test_coq_scenario_a2_memory_writes": "Coq Scenario A2 Conformance",
        "test_coq_scenario_a3_control_flow_branch": "Coq Scenario A3 Conformance",
        "test_coq_scenario_a4_exception_traps": "Coq Scenario A4 Conformance",
        "test_coq_scenario_a5_multi_cycle_burst": "Coq Scenario A5 Conformance",
    }
    rust_map = {
        "test_rust_scenario_a0_basic_commit": "Rust Scenario A0 Conformance",
        "test_rust_scenario_a1_register_writes": "Rust Scenario A1 Conformance",
        "test_rust_scenario_a2_memory_writes": "Rust Scenario A2 Conformance",
        "test_rust_scenario_a3_control_flow_branch": "Rust Scenario A3 Conformance",
        "test_rust_scenario_a4_exception_traps": "Rust Scenario A4 Conformance",
        "test_rust_scenario_a5_multi_cycle_burst": "Rust Scenario A5 Conformance",
    }
    rtl_map = {
        "test_rtl_cycle_c0_fetch_decode": "RTL Cycle Assertion C0 (Fetch/Decode)",
        "test_rtl_cycle_c1_execute_stage": "RTL Cycle Assertion C1 (Execute Stage)",
        "test_rtl_cycle_c2_memory_access": "RTL Cycle Assertion C2 (Memory Access)",
        "test_rtl_cycle_c3_writeback": "RTL Cycle Assertion C3 (Writeback)",
        "test_rtl_cycle_c4_trap_vectoring": "RTL Cycle Assertion C4 (Trap Vectoring)",
    }
    mutation_map = {
        "test_coq_adapter_mutation_detection": "Adapter Schema Field Mutation Immunity",
        "test_rtl_adapter_decoding_immutability": "Adapter Binary Payload Mutation Immunity",
    }
    invariant_map = {
        "test_epoch_monotonicity_invariant": "Epoch Monotonicity Invariant",
        "test_neutral_trap_semantics_invariant": "Neutral Trap Semantics Invariant",
        "test_single_retirement_policy_invariant": "Single Retirement Policy Invariant",
    }

    # Execute Stages
    _run_suite("tests.conformance.test_conformance_coq", reporter, "SCHEMA VALIDATION", schema_map)
    _run_suite("tests.conformance.test_golden_corpus", reporter, "GOLDEN CORPUS VECTORS", golden_map)
    _run_suite("tests.conformance.test_conformance_coq", reporter, "COQ ADAPTER CONFORMANCE", coq_map)
    _run_suite("tests.conformance.test_conformance_rust", reporter, "RUST ADAPTER CONFORMANCE", rust_map)
    _run_suite("tests.conformance.test_conformance_rtl", reporter, "RTL ADAPTER CONFORMANCE", rtl_map)
    _run_suite("tests.conformance.test_adapter_mutations", reporter, "MUTATION IMMUNITY", mutation_map)
    _run_suite("tests.conformance.test_invariant_safety", reporter, "INVARIANT SAFETY", invariant_map)

    return reporter.render_report()


if __name__ == "__main__":
    success = run_certification_pipeline()
    sys.exit(0 if success else 1)
