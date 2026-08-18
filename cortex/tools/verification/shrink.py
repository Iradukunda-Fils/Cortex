"""
Semantic Delta-Debugging Shrinker for Minimizing Failing Scenarios
"""

from typing import Any


class SemanticShrinker:
    def __init__(self, max_shrunk_steps: int = 50):
        self.max_shrunk_steps = max_shrunk_steps

    def shrink_scenario(self, scenario: dict[str, Any], failing_step: int) -> dict[str, Any]:
        """
        Reduces program instructions down to failing step minimum reproducer.
        """
        program = scenario.get("program", [])
        # Truncate instruction stream up to failing step
        shrunk_program = program[:failing_step]

        return {
            "seed": scenario.get("seed", "0x00000000"),
            "original_steps": len(program),
            "shrunk_steps": len(shrunk_program),
            "initial_state": scenario.get("initial_state", {}),
            "program": shrunk_program,
        }
