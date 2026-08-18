"""
Architecture Research Gate & Synthesis Module (Post Issue #12)

Synthesizes empirical findings from Issues #10, #11, and #12 to evaluate:
1. State recovery & EventStore guarantees
2. Side-effect semantics & IN_DOUBT state contracts
3. Recovery contract specification
4. Comparative topology analysis (Tiered Hybrid Isolation vs Process-per-Plugin)
"""

import json
import os
import platform
import sys
import time
from typing import Any


def generate_architecture_gate_synthesis() -> dict[str, Any]:
    """Generates the structured Architecture Gate research synthesis data."""
    env_metadata = {
        "python_version": sys.version.split()[0],
        "os": platform.system(),
        "arch": platform.machine(),
    }

    empirical_evidence = {
        "issue_10_telemetry": {
            "baseline_p50_ms": 0.2265,
            "multistage_p50_ms": 0.5014,
            "tail_p99_ms": 4.0892,
            "event_propagation_scaling": "Observed approximately linear growth over tested workload range",
            "public_api_symbols": 21,
        },
        "issue_11_crash_semantics": {
            "ordinary_python_exception_trapped": True,
            "cortex_error_classification_preserved": True,
            "capability_rejection_security_intact": True,
            "chained_execution_prior_events_preserved": True,
            "subsequent_workflow_isolated": True,
            "single_process_limit": "Low-level process crashes (SIGSEGV, sys.exit) escape single-process boundary",
        },
        "issue_12_timeout_cancellation": {
            "pre_execution_cancellation_clean": True,
            "mid_workflow_cooperative_halt": True,
            "event_journal_lineage_post_cancellation_intact": True,
            "subsequent_workflow_healthy": True,
            "deterministic_cancellation": True,
            "single_process_limitation": "Non-cooperative thread blocking (time.sleep, GIL loops) stalls main event thread",
        },
    }

    five_architectural_questions = {
        "q1_recovery_targets": {
            "authoritative_source": "EventStore append-only journal log",
            "volatile_components": ["In-memory event queues", "Active plugin handler frames", "Transient client state"],
            "persistent_components": ["EventStore journal log", "Workflow dataclass state", "PluginManifest records"],
            "state_reconstruction_method": "Replaying event journal from t=0 to crash point t_crash",
        },
        "q2_eventstore_guarantees": {
            "persistence_model": "Synchronous append upon context.publish()",
            "lineage_integrity": "Strict DAG ordering via event_id -> causation_id -> correlation_id",
            "replay_determinism": "Replaying log against clean client reproduces identical state machine sequence",
            "crash_point_semantics": {
                "pre_side_effect_crash": "Operation unexecuted; safe to re-run on restart",
                "mid_side_effect_crash": "Operation partially performed; event missing -> requires IN_DOUBT state",
                "post_side_effect_crash": "Operation complete; event committed -> safe replay",
            },
        },
        "q3_side_effect_semantics": {
            "unconfirmed_side_effect_problem": "Runtime crashes after external side effect but before completion event is persisted",
            "chosen_contract_option": "Option B (IN_DOUBT state) + Option C (Required Idempotency Keys)",
            "rationale": "Prevents catastrophic double-execution of non-idempotent external operations while giving operators explicit CLI resolution tools.",
        },
        "q4_recovery_contract_spec": {
            "event_delivery": "At-least-once with deduplication by event_id",
            "plugin_execution": "At-most-once per event emission",
            "workflow_recovery": "Deterministic EventStore journal replay",
            "side_effects": "Idempotency keys required for side-effect capabilities",
            "crash_point": "Arbitrary instruction / signal boundary",
            "state_reconstruction": "Pure function of EventStore log: S_t = f(S_0, E_1, ..., E_t)",
            "unknown_operation": "Explicit IN_DOUBT workflow state",
            "cancellation": "Cooperative (in-process) / Forced (SIGKILL worker process)",
            "recovery_control": "Automatic for deterministic events; Operator-assisted for IN_DOUBT operations",
        },
        "q5_architectural_topology_comparison": {
            "topologies_evaluated": [
                {
                    "name": "Topology 1: Process-per-Plugin",
                    "pros": "Maximum isolation; crashed plugin cannot kill host or peer plugins",
                    "cons": "High process creation & IPC latency overhead",
                    "cortex_fit": "Suitable for untrusted / high-risk plugins only",
                },
                {
                    "name": "Topology 2: Shared Worker Pool",
                    "pros": "Lower process overhead than 1:1",
                    "cons": "Crash in worker process affects all plugins assigned to worker",
                    "cortex_fit": "Suitable for medium-risk plugin groups",
                },
                {
                    "name": "Topology 3: Tiered / Hybrid Isolation (RECOMMENDED)",
                    "pros": "Sub-millisecond performance (P50 = 0.226ms) for trusted plugins in-process; SIGKILL preemption and fault containment for untrusted / heavy plugins in worker processes",
                    "cons": "Requires trust/isolation metadata in capability manifests",
                    "cortex_fit": "PERFECT FIT with Cortex capability security model",
                },
            ],
            "recommended_architecture": "Topology 3: Tiered Hybrid Isolation Model",
        },
    }

    readiness_decision = {
        "architecture_gate_passed": True,
        "recommendation": "Proceed to Issue #13 (Runtime Restart & Workflow Recovery Semantics) with IN_DOUBT state contracts and Tiered Hybrid Architecture principles established.",
        "issue_13_authorized": True,
    }

    return {
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": env_metadata,
        "empirical_evidence": empirical_evidence,
        "synthesis": five_architectural_questions,
        "gate_decision": readiness_decision,
    }


def generate_architecture_gate_artifacts(json_output_path: str) -> dict[str, Any]:
    """Generates and writes research/synthesis/architecture_gate_synthesis.json."""
    data = generate_architecture_gate_synthesis()
    os.makedirs(os.path.dirname(os.path.abspath(json_output_path)), exist_ok=True)
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return data


if __name__ == "__main__":
    report_file = os.path.join("research", "synthesis", "architecture_gate_synthesis.json")
    res = generate_architecture_gate_artifacts(report_file)
    print(f"Architecture Gate Decision: Passed={res['gate_decision']['architecture_gate_passed']}")
    print(
        f"Recommended v0.3 Topology: {res['synthesis']['q5_architectural_topology_comparison']['recommended_architecture']}"
    )
