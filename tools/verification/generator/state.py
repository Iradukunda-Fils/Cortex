"""
Initial STCR & Machine Register State Fuzzing Generator
"""

import random
from typing import Dict, List, Any

class StateGenerator:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def generate_initial_state(self) -> Dict[str, Any]:
        stcr_file = []

        # STCR0 always starts as root execution capability by default or random
        root_v = True
        root_mask = 0x7000 # READ | WRITE | EXEC (0x4000 | 0x2000 | 0x1000)
        root_base = 0x2000
        root_epoch = 0

        stcr_file.append({
            "index": 0,
            "valid": root_v,
            "permissions": root_mask,
            "base_address": root_base,
            "epoch": root_epoch
        })

        for reg_id in range(1, 32):
            is_valid = self.rng.choice([True, False, False, False]) # 25% chance of valid STCR slot
            if is_valid:
                mask = self.rng.choice([0x4000, 0x2000, 0x1000, 0x7000, 0x0000])
                base = self.rng.choice([0x0, 0x1000, 0x2000, 0x8000, 0xFFFF0000])
                epoch = self.rng.choice([0, 1, 100, 65534, 65535]) # include boundary epoch limits
            else:
                mask = 0
                base = 0
                epoch = 0

            stcr_file.append({
                "index": reg_id,
                "valid": is_valid,
                "permissions": mask,
                "base_address": base,
                "epoch": epoch
            })

        return {
            "pc": 0x1000,
            "privilege_mode": "Machine",
            "reg_hec": self.rng.choice([0, 1, 65535]),
            "stcr_registers": stcr_file
        }