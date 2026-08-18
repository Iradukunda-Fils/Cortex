"""
Cortex Verification Substrate Certification Pipeline
"""

import os
import sys
import traceback
import unittest

# Ensure workspace root is first in sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


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
        "EXECUTION-INTENT PARITY (GATE H)",
        "CRYPTOGRAPHIC CAUSAL WITNESS (GATE I)",
        "INDEPENDENT UNTRUSTED VERIFIER (GATE J)",
        "WORKER ISOLATION & MEDIATION (GATE G)",
        "BOUNDED RE-CERTIFICATION THROUGH PROFILE A (H/I/J)",
    ]

    def __init__(self):
        self.sections: dict[str, list[tuple[str, str]]] = {
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


def _run_suite(suite_module: str, reporter: CertificationReporter, category: str, name_mapping: dict[str, str]) -> None:
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
            method_name = str(test.id().split(".")[-1])
            if name_mapping and method_name in name_mapping:
                display_name: str = name_mapping[method_name]
            else:
                display_name = method_name.replace("_", " ").title()
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
    gate_h_canon_map = {
        "test_canonicalization_identical_semantic_objects": "Gate H Canonicalization (Identical Objects)",
        "test_canonicalization_path_modification_digest": "Gate H Canonicalization (Path Modification)",
        "test_canonicalization_payload_modification_digest": "Gate H Canonicalization (Payload Modification)",
    }
    gate_h_adv_map = {
        "test_h_001_valid_intent_valid_execution": "Gate H Adversarial H-TEST-001 (Valid Execution)",
        "test_h_002_modified_path_traps": "Gate H Adversarial H-TEST-002 (Path Modification Trap)",
        "test_h_008_replayed_token_traps": "Gate H Adversarial H-TEST-008 (Replay Protection Trap)",
        "test_h_013_concurrent_double_presentation": "Gate H Adversarial H-TEST-013 (Atomic CAS Concurrency)",
    }
    gate_h_act_map = {
        "test_h4_end_to_end_authorized_actuation": "Gate H Actuation Boundary End-to-End Actuation",
        "test_h4_single_byte_tampering_traps_before_actuation": "Gate H Actuation Boundary Single-Byte Trap",
    }
    gate_i_map = {
        "test_i_001_valid_witness_chain": "Gate I Causal Witness (Valid Sequential Chain)",
        "test_i_002_event_payload_tampering_traps": "Gate I Causal Witness (Event Digest Modification Trap)",
        "test_i_003_intent_payload_tampering_traps": "Gate I Causal Witness (Intent Digest Modification Trap)",
        "test_i_004_event_omission_traps": "Gate I Causal Witness (Event Omission Trap)",
        "test_i_005_event_reordering_traps": "Gate I Causal Witness (Event Re-ordering Trap)",
        "test_i_006_signature_tampering_traps": "Gate I Causal Witness (Signature Tampering Trap)",
        "test_i_007_genesis_state_tampering_traps": "Gate I Causal Witness (Genesis State Mismatch Trap)",
    }
    gate_j_map = {
        "test_j_adv_001_valid_evidence_bundle": "Gate J Independent Verifier (Valid Evidence Bundle)",
        "test_j_adv_002_event_payload_mutation": "Gate J Independent Verifier (Event Payload Mutation)",
        "test_j_adv_003_intent_parameter_substitution": "Gate J Independent Verifier (Intent Parameter Substitution)",
        "test_j_adv_004_event_omission_traps": "Gate J Independent Verifier (Event Omission Trap)",
        "test_j_adv_005_event_reordering_traps": "Gate J Independent Verifier (Event Re-ordering Trap)",
        "test_j_adv_006_forged_authority_signature": "Gate J Independent Verifier (Forged Signature Trap)",
        "test_j_adv_007_untrusted_genesis_anchor": "Gate J Independent Verifier (Untrusted Genesis Anchor)",
        "test_j_adv_008_forged_recomputed_witness_rewrite": "Gate J Independent Verifier (Forged Witness Rewrite)",
        "test_j_adv_009_truncated_log_stream": "Gate J Independent Verifier (Truncated Log Stream)",
        "test_j_adv_010_stream_length_mismatch": "Gate J Independent Verifier (Stream Length Mismatch)",
        "test_j_adv_011_missing_anchor_schema": "Gate J Independent Verifier (Missing Anchor Schema)",
        "test_j_adv_012_unbound_token_intent_mismatch": "Gate J Independent Verifier (Unbound Token Intent Mismatch)",
    }
    gate_g_map = {
        "test_g_000_legitimate_mediated_intent": "Gate G Mediated Path (Valid SignedIntent Path)",
        "test_g_000b_fail_closed_setup_invariant": "Gate G Invariant Safety (Fail-Closed Setup Trap)",
        "test_g_001_filesystem_mutation_escape_trapped": "Gate G Isolation (Filesystem Mutation Trap)",
        "test_g_002_network_access_escape_trapped": "Gate G Isolation (Network Connection Trap)",
        "test_g_003_subprocess_creation_trapped": "Gate G Isolation (Subprocess Exec Trap)",
        "test_g_004_writable_executable_memory_trapped": "Gate G Isolation (Writable+Exec Memory Trap)",
        "test_g_005_direct_device_access_trapped": "Gate G Isolation (Direct Device Access Trap)",
        "test_g_006_unwhitelisted_fd_leak_check": "Gate G Isolation (Unwhitelisted FD Sanitation)",
        "test_g_007_ipc_framing_flood_dropped": "Gate G Framing (IPC Buffer Flood Dropped)",
        "test_g_008_ipc_request_replay_rejected": "Gate G Protection (IPC Request Replay Rejected)",
        "test_g_009_worker_crash_pre_auth_isolated": "Gate G Recovery (Worker Crash Pre-Auth Isolated)",
        "test_g_010_crash_post_auth_pre_actuate_handled": "Gate G Recovery (Gateway Crash Pre-Actuate Handled)",
        "test_g_011_crash_post_actuate_indeterminate": "Gate G Recovery (Crash Post-Actuate INDETERMINATE)",
        "test_g_012_gateway_fail_closed_guarantee": "Gate G Invariant (Gateway Crash Fails Closed)",
        "test_g_pid1_namespace_containment": "Gate G Namespace (PID 1 Process Teardown Invariant)",
    }
    profile_a_recert_map = {
        "test_g_000_legitimate_mediated_intent": "Gate H Parity via Profile A (SignedIntent -> Gateway -> ExecutionToken)",
        "test_g_011_crash_post_actuate_indeterminate": "Gate I Witness via Profile A (State Chain & Crash UNKNOWN Marker)",
        "test_g_000_legitimate_mediated_intent": "Gate J Independent Verifier via Profile A (Evidence Bundle Verification)",
    }

    namespace_map = {
        "test_cortex_security_references_classification": "Reserved Namespace cortex.security Reference Audit",
        "test_manifests_use_local_schema_resolution": "Offline Local Relative Schema Resolution",
        "test_ci_workflows_have_zero_cortex_security_network_calls": "CI Workflow Zero Domain Network Call Guarantee",
    }

    f4c3_map = {
        "test_f4c3_001_valid_verdict_correspondence": "F4c.3 Coq Correspondence (VERDICT_VALID)",
        "test_f4c3_002_invalid_verdict_correspondence_digest_mismatch": "F4c.3 Coq Correspondence (VERDICT_INVALID - Event Digest)",
        "test_f4c3_003_invalid_verdict_correspondence_signature": "F4c.3 Coq Correspondence (VERDICT_INVALID - Signature)",
        "test_f4c3_004_malformed_verdict_correspondence_truncated_log": "F4c.3 Coq Correspondence (VERDICT_MALFORMED - Truncated)",
        "test_f4c3_005_malformed_verdict_correspondence_length_mismatch": "F4c.3 Coq Correspondence (VERDICT_MALFORMED - Stream Length)",
        "test_f4c3_006_sequence_continuity_trap": "F4c.3 Sequence Continuity Trap Alignment",
        "test_f4c3_007_parent_pointer_chaining_trap": "F4c.3 Parent Pointer Chaining Trap Alignment",
    }

    f4c4_map = {
        "test_class_1_full_verified_valid_trace": "F4c.4 Class 1 Differential Check (Valid Trace -> VALID)",
        "test_class_2_anchor_mismatch": "F4c.4 Class 2 Differential Check (Anchor Mismatch -> INVALID)",
        "test_class_3_signature_violation": "F4c.4 Class 3 Differential Check (Signature Violation -> INVALID)",
        "test_class_4_token_parity_mismatch": "F4c.4 Class 4 Differential Check (Token Parity -> INVALID)",
        "test_class_5_sequence_gap": "F4c.4 Class 5 Differential Check (Sequence Gap -> INVALID)",
        "test_class_6_chain_broken": "F4c.4 Class 6 Differential Check (Chain Broken -> INVALID)",
        "test_class_7_digest_mutation": "F4c.4 Class 7 Differential Check (Digest Mutation -> INVALID)",
        "test_class_8_empty_stream": "F4c.4 Class 8 Differential Check (Empty Stream -> INDETERMINATE)",
        "test_class_9_missing_required_section": "F4c.4 Class 9 Differential Check (Missing Section -> INDETERMINATE)",
        "test_class_10_stream_length_mismatch_and_flagged": "F4c.4 Class 10 Differential Check (Length Parity -> INDETERMINATE)",
    }

    # Execute Stages
    _run_suite("tests.conformance.test_conformance_coq", reporter, "SCHEMA VALIDATION", schema_map)
    _run_suite("tests.conformance.test_offline_namespace_hygiene", reporter, "SCHEMA VALIDATION", namespace_map)
    _run_suite("tests.conformance.test_golden_corpus", reporter, "GOLDEN CORPUS VECTORS", golden_map)
    _run_suite("tests.conformance.test_conformance_coq", reporter, "COQ ADAPTER CONFORMANCE", coq_map)
    _run_suite("tests.conformance.test_conformance_rust", reporter, "RUST ADAPTER CONFORMANCE", rust_map)
    _run_suite("tests.conformance.test_conformance_rtl", reporter, "RTL ADAPTER CONFORMANCE", rtl_map)
    _run_suite("tests.conformance.test_adapter_mutations", reporter, "MUTATION IMMUNITY", mutation_map)
    _run_suite("tests.conformance.test_invariant_safety", reporter, "INVARIANT SAFETY", invariant_map)
    _run_suite("tests.conformance.test_gate_h_canonicalization", reporter, "EXECUTION-INTENT PARITY (GATE H)", gate_h_canon_map)
    _run_suite("tests.conformance.test_gate_h_adversarial", reporter, "EXECUTION-INTENT PARITY (GATE H)", gate_h_adv_map)
    _run_suite("tests.conformance.test_gate_h_actuation_boundary", reporter, "EXECUTION-INTENT PARITY (GATE H)", gate_h_act_map)
    _run_suite("tests.conformance.test_gate_i_causal_witness", reporter, "CRYPTOGRAPHIC CAUSAL WITNESS (GATE I)", gate_i_map)
    _run_suite("tests.conformance.test_gate_j_independent_verifier", reporter, "INDEPENDENT UNTRUSTED VERIFIER (GATE J)", gate_j_map)
    _run_suite("tests.conformance.test_f4c3_verifier_formal_mapping", reporter, "INDEPENDENT UNTRUSTED VERIFIER (GATE J)", f4c3_map)
    _run_suite("tests.conformance.test_f4c4_domain_closure_audit", reporter, "INDEPENDENT UNTRUSTED VERIFIER (GATE J)", f4c4_map)
    _run_suite("tests.conformance.test_gate_g_adversarial", reporter, "WORKER ISOLATION & MEDIATION (GATE G)", gate_g_map)
    _run_suite("tests.conformance.test_gate_g_adversarial", reporter, "BOUNDED RE-CERTIFICATION THROUGH PROFILE A (H/I/J)", profile_a_recert_map)

    return reporter.render_report()


if __name__ == "__main__":
    success = run_certification_pipeline()
    sys.exit(0 if success else 1)
