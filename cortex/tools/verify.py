#!/usr/bin/env python3
"""
Cortex Contract-Driven Formal Verification CLI Entry Point
"""

import argparse
import sys

from cortex.tools.verification.contract import VerificationContract
from cortex.tools.verification.engine import VerificationEngine


def main():
    parser = argparse.ArgumentParser(description="Cortex Contract-Driven Formal Verification Tool")
    parser.add_argument("--contract", required=True, help="Path to verification contract YAML")
    parser.add_argument("--seed", default=None, help="Hex seed for random generation (e.g. 0x4A91C3F8)")
    parser.add_argument("--iterations", type=int, default=None, help="Override total fuzzing iterations")
    parser.add_argument("--inject-failure", default=None, help="Phase 3A.5 mutation fault vector to inject")

    args = parser.parse_args()

    contract = VerificationContract.load(args.contract)

    # Determine seed
    seed_str = args.seed or contract.fuzzing_parameters.get("default_seed", "0x4A91C3F8")
    seed_val = int(seed_str, 16) if seed_str.startswith("0x") else int(seed_str)

    iterations = args.iterations or contract.fuzzing_parameters.get("total_iterations", 100)

    print("================================================================================")
    print("                       Cortex Verification Platform Engine                      ")
    print("================================================================================")
    print(f" Contract ID:       {contract.contract_id}")
    print(f" Seed:              0x{seed_val:08X}")
    print(f" Target Iterations: {iterations}")
    print(f" Oracle Version:    {contract.oracle.get('version', 'v2.1.0')}")
    if args.inject_failure:
        print(f" Injecting Fault:   {args.inject_failure}")
    print("--------------------------------------------------------------------------------")

    engine = VerificationEngine(contract, seed_val)
    result = engine.run_verification(iterations=iterations, inject_failure=args.inject_failure)

    if result.get("status") == "FAIL":
        print("\n[!] VERIFICATION MISMATCH DETECTED!")
        print(f"    Iteration:            {result.get('iteration')}")
        print(f"    Seed:                 {result.get('seed')}")
        print(f"    Error Type:           {result['diagnostic'].get('error_type')}")
        print(f"    Failing Step:         {result['diagnostic'].get('failing_step')}")
        print(f"    Mismatched Field:     {result['diagnostic'].get('mismatched_field')}")
        print(f"    Counterexample Hash:  {result.get('counterexample_hash')}")
        print("================================================================================")
        sys.exit(1)
    else:
        print("\n[✓] SUCCESS: Contract-Driven Verification Passed Across All Targets!")
        print(f"    Steps Evaluated:       {result.get('total_steps_evaluated')}")
        print(f"    Opcode Coverage:       {result['metrics']['opcode_coverage']['coverage_percentage']}%")
        print(f"    Trap Path Coverage:    {result['metrics']['trap_coverage']['coverage_percentage']}%")
        print(f"    Unique States:         {result['metrics']['state_space_explored']['unique_states_explored']}")
        print("================================================================================")
        sys.exit(0)


if __name__ == "__main__":
    main()
