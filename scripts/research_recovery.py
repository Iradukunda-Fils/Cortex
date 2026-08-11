#!/usr/bin/env python3
"""
Issue #13 Restart, Recovery & Side-Effect Research Script

Executes Experiments A through E and generates docs/operations/recovery_semantics_report.json.
"""

import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cortex._research.recovery import generate_recovery_semantics_artifacts


def main() -> None:
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "operations", "recovery_semantics_report.json")
    print("🔬 Running Cortex Issue #13 Restart, Recovery & Side-Effect Research Suite...")
    results = generate_recovery_semantics_artifacts(output_path)

    print("\n=================================================================")
    print("      ISSUE #13 RESTART, RECOVERY & SIDE-EFFECT RESEARCH REPORT   ")
    print("=================================================================")
    print(f"Environment: Python {results['environment']['python_version']} on {results['environment']['os']} ({results['environment']['arch']})")
    print("-----------------------------------------------------------------")
    exp_a = results["experiments"]["experiment_a"]
    print(f"[{exp_a['title']}]")
    print(f"  - In-Memory State Survived Process Death: {exp_a['in_memory_state_survived']}")
    print(f"  - Finding: {exp_a['empirical_finding']}")

    exp_b = results["experiments"]["experiment_b"]
    print(f"\n[{exp_b['title']}]")
    print(f"  - B1 (Pre-Execution): Mutations={exp_b['b1_pre_execution']['side_effect_mutations']} | Ambiguity={exp_b['b1_pre_execution']['ambiguity']}")
    print(f"  - B2 (Mid-Execution): Mutations={exp_b['b2_mid_execution']['side_effect_mutations']} | Ambiguity={exp_b['b2_mid_execution']['ambiguity']}")
    print(f"  - B3 (Post-Execution): Mutations={exp_b['b3_post_execution']['side_effect_mutations']} | Ambiguity={exp_b['b3_post_execution']['ambiguity']}")

    exp_c = results["experiments"]["experiment_c"]
    print(f"\n[{exp_c['title']}]")
    print(f"  - Replay Without Idempotency Key: {exp_c['replay_without_idempotency_mutations']} mutations (DUPLICATED!)")
    print(f"  - Replay With Idempotency Key:    {exp_c['replay_with_idempotency_mutations']} mutation (DEDUPLICATED!)")
    print(f"  - Idempotency Deduplication Proof: {exp_c['idempotency_eliminates_duplication']}")

    print("\n-----------------------------------------------------------------")
    print("THE 5 CORE EMPIRICAL QUESTIONS ANSWERED:")
    for q_key, val in results["five_core_empirical_questions"].items():
        print(f"  [{q_key}] {val}")
    print("=================================================================")
    print(f"[✓] Artifact generated cleanly: {output_path}\n")


if __name__ == "__main__":
    main()
