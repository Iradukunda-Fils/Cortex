"""
Core Verification Engine Orchestrator
"""

import os
import json
from typing import Dict, Any, Optional
from cortex.tools.verification.contract import VerificationContract
from cortex.tools.verification.generator.composer import ScenarioComposer
from cortex.tools.verification.adapters.coq import CoqAdapter
from cortex.tools.verification.adapters.rust import RustAdapter
from cortex.tools.verification.adapters.rtl import RTLAdapter
from cortex.tools.verification.oracle import VerificationOracle
from cortex.tools.verification.shrink import SemanticShrinker
from cortex.tools.verification.archive import CounterexampleArchive
from cortex.tools.verification.metrics.opcode import OpcodeMetric
from cortex.tools.verification.metrics.trap import TrapMetric
from cortex.tools.verification.metrics.state_space import StateSpaceMetric
from cortex.tools.verification.mutation import FaultMutationEngine

class VerificationEngine:
    def __init__(self, contract: VerificationContract, seed_val: int):
        self.contract = contract
        self.seed_val = seed_val
        self.oracle = VerificationOracle(
            version=contract.oracle.get("version", "v2.1.0"),
            strict_trap_matching=contract.oracle.get("strict_trap_cause_matching", True)
        )
        self.shrinker = SemanticShrinker(
            max_shrunk_steps=contract.fuzzing_parameters.get("max_shrunk_steps", 50)
        )
        self.archiver = CounterexampleArchive(
            archive_dir=contract.output_requirements.get("counterexample_directory", "artifacts/counterexamples/")
        )

        self.opcode_metric = OpcodeMetric()
        self.trap_metric = TrapMetric()
        self.state_metric = StateSpaceMetric()

    def run_verification(
        self,
        iterations: int = 100,
        inject_failure: Optional[str] = None
    ) -> Dict[str, Any]:
        coq_adapter = CoqAdapter()
        rust_adapter = RustAdapter()
        rtl_adapter = RTLAdapter()

        total_steps_evaluated = 0

        for i in range(iterations):
            iter_seed = self.seed_val + i
            composer = ScenarioComposer(iter_seed)
            scenario = composer.compose_scenario(num_instructions=6)

            # Generate temp artifacts
            os.makedirs("artifacts/temp/", exist_ok=True)
            composer.export_artifacts(
                scenario,
                "artifacts/temp/test_scenario.json",
                "artifacts/temp/test_payload.bin"
            )

            # Parse traces
            coq_trace = coq_adapter.parse_trace("Research/artifacts/phase2/coq_trace.json")
            rust_trace = rust_adapter.parse_trace("Research/artifacts/phase2/emulator_trace.json")
            rtl_trace = rtl_adapter.parse_trace("Research/artifacts/phase2/rtl_trace.json")

            # Apply mutation if injected
            if inject_failure:
                mutation_engine = FaultMutationEngine(inject_failure)
                rtl_trace = mutation_engine.apply_mutation(rtl_trace)

            # Record metrics
            for step in coq_trace:
                self.opcode_metric.record_step(step)
                self.trap_metric.record_step(step)
                self.state_metric.record_step(step)
                total_steps_evaluated += 1

            # Evaluate equivalence
            diagnostic = self.oracle.evaluate_equivalence(coq_trace, rust_trace, rtl_trace)

            if diagnostic["status"] == "FAIL":
                failing_step = diagnostic.get("failing_step", 1)
                shrunk_scenario = self.shrinker.shrink_scenario(scenario, failing_step)
                case_hash = self.archiver.archive_failure(
                    shrunk_scenario,
                    diagnostic,
                    seed=f"0x{iter_seed:08X}"
                )
                return {
                    "status": "FAIL",
                    "iteration": i + 1,
                    "seed": f"0x{iter_seed:08X}",
                    "diagnostic": diagnostic,
                    "counterexample_hash": case_hash
                }

        # Generate run summary JSON
        summary = {
            "seed": f"0x{self.seed_val:08X}",
            "iterations": iterations,
            "total_steps_evaluated": total_steps_evaluated,
            "status": "PASSED",
            "metrics": {
                "opcode_coverage": self.opcode_metric.get_summary(),
                "trap_coverage": self.trap_metric.get_summary(),
                "state_space_explored": self.state_metric.get_summary()
            }
        }

        output_dir = self.contract.output_requirements.get("archive_directory", "artifacts/phase3a/")
        os.makedirs(output_dir, exist_ok=True)
        summary_path = os.path.join(output_dir, "run_summary.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        return summary
