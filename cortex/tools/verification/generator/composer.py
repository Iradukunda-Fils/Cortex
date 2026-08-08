"""
Scenario Composer: Merges Machine State and Instruction Stream into Reproducible Payloads
"""

import json
import struct
from typing import Dict, Any
from cortex.tools.verification.generator.state import StateGenerator
from cortex.tools.verification.generator.program import ProgramGenerator

class ScenarioComposer:
    def __init__(self, seed: int):
        self.seed = seed
        self.state_gen = StateGenerator(seed)
        self.prog_gen = ProgramGenerator(seed)

    def compose_scenario(self, num_instructions: int = 8) -> Dict[str, Any]:
        initial_state = self.state_gen.generate_initial_state()
        program = self.prog_gen.generate_program(num_instructions)

        return {
            "seed": f"0x{self.seed:08X}",
            "initial_state": initial_state,
            "program": program
        }

    def export_artifacts(self, scenario: Dict[str, Any], json_path: str, bin_path: str):
        with open(json_path, "w") as f:
            json.dump(scenario, f, indent=2)

        with open(bin_path, "wb") as f:
            for inst in scenario["program"]:
                # Big-endian 32-bit instruction word
                f.write(struct.pack(">I", inst["raw_uint32"]))
