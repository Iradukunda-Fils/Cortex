"""
Instruction Stream Fuzzing Generator for Cortex Capabilities
"""

import random
from typing import Any


class ProgramGenerator:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def generate_program(self, num_instructions: int = 8) -> list[dict[str, Any]]:
        instructions = []

        opcodes = [
            ("INVOKE_CAP", 0x01, 0x04000000),
            ("RESTRICT_CAP", 0x03, 0x0C000000),
            ("REVOKE_CAP", 0x05, 0x14000000),
            ("GRANT_CAP", 0x02, 0x08000000),
            ("ILLEGAL_OP", 0x0F, 0x00000000),
        ]

        for _ in range(num_instructions):
            op_name, op_code, raw_base = self.rng.choice(opcodes)
            src_reg = self.rng.randint(0, 3)
            dst_reg = self.rng.randint(0, 3)
            imm = self.rng.choice([0x0000, 0x1000, 0x2000, 0x4000, 0x7000, 0xFFFF])

            if op_name == "RESTRICT_CAP":
                raw = raw_base | (src_reg << 16) | imm
            elif op_name == "INVOKE_CAP" or op_name == "REVOKE_CAP":
                raw = raw_base | (src_reg << 16)
            elif op_name == "GRANT_CAP":
                raw = raw_base | (src_reg << 16) | (dst_reg << 20) | imm
            else:
                raw = 0x00000000

            instructions.append(
                {"opcode_name": op_name, "opcode_val": op_code, "raw_hex": f"0x{raw:08x}", "raw_uint32": raw}
            )

        return instructions
