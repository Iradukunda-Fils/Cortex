#!/usr/bin/env python3
import os
import struct


def encode_inst(opcode: int, stcr_id: int, arg_reg: int, imm: int) -> int:
    return ((opcode & 0x3F) << 26) | ((stcr_id & 0x1F) << 21) | ((arg_reg & 0x1F) << 16) | (imm & 0xFFFF)

def generate_canonical_test_bin(output_path: str):
    MAGIC = b"CORTEX"
    VERSION = 1

    # Sequence of instructions exercising all SDS v1.0 refinement properties:
    instructions = [
        encode_inst(0x01, 0, 1, 0),      # PC 0: invoke_cap STCR0, R1 -> Expected: COMMIT (Valid)
        encode_inst(0x03, 0, 0, 0x4000), # PC 1: restrict_cap STCR0, READ (Bit 62) -> Expected: COMMIT
        encode_inst(0x01, 0, 2, 0),      # PC 2: invoke_cap STCR0, R2 -> Expected: COMMIT
        encode_inst(0x05, 0, 0, 0),      # PC 3: hec.inc -> Expected: COMMIT (Epoch = 1)
        encode_inst(0x01, 0, 3, 0),      # PC 4: invoke_cap STCR0, R3 -> Expected: EFF_TRAP (Epoch Expired if Max_Epoch == 0)
        encode_inst(0x00, 0, 0, 0),      # PC 5: Opcode 0x00 -> Expected: EFF_TRAP (Illegal/Reserved Opcode)
    ]

    header = MAGIC + struct.pack(">H", VERSION) + struct.pack(">I", len(instructions))
    payload = b"".join(struct.pack(">I", inst) for inst in instructions)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(header + payload)

    print(f"[+] Canonical test binary successfully generated at {output_path} ({len(header + payload)} bytes)")

if __name__ == "__main__":
    import sys
    out_path = sys.argv[1] if len(sys.argv) > 1 else "tests/canonical_test_program.bin"
    generate_canonical_test_bin(out_path)
