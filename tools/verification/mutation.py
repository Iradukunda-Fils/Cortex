"""
Phase 3A.5 Fault Injection Engine for Pipeline Mutation Testing
"""

from typing import List
from tools.verification.schema import CanonicalState, CanonicalSTCR, CanonicalTrap

class FaultMutationEngine:
    def __init__(self, failure_vector: str):
        self.failure_vector = failure_vector

    def apply_mutation(self, rtl_trace: List[CanonicalState]) -> List[CanonicalState]:
        """
        Injects synthetic faults into engine traces to verify pipeline sensitivity.
        """
        if not rtl_trace:
            return rtl_trace

        mutated = []
        for step in rtl_trace:
            stcr_clone = [CanonicalSTCR(**s.to_dict()) for s in step.stcr]
            trap_clone = CanonicalTrap(**step.trap.to_dict())
            c_step = CanonicalState(
                step=step.step,
                pc=step.pc,
                instruction=step.instruction,
                privilege_mode=step.privilege_mode,
                reg_hec=step.reg_hec,
                registers=dict(step.registers),
                stcr=stcr_clone,
                trap=trap_clone
            )
            mutated.append(c_step)

        if self.failure_vector == "rtl.trap_suppress":
            # Suppress trap flag on step 3
            for step in mutated:
                if step.step == 3:
                    step.trap.triggered = False
                    step.trap.cause_code = 0
                    step.trap.cause_name = "None"
        elif self.failure_vector == "rtl.stcr0.epoch_mismatch":
            # Off-by-one epoch mismatch on step 2
            for step in mutated:
                if step.step == 2 and step.stcr:
                    step.stcr[0].epoch += 1

        return mutated
