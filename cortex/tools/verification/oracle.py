"""
Structured Verification Oracle for 3-Way Trace Equivalence
"""

from typing import List, Dict, Any, Optional
from cortex.tools.verification.schema import CanonicalState

class VerificationOracle:
    def __init__(self, version: str = "v2.1.0", strict_trap_matching: bool = True):
        self.version = version
        self.strict_trap_matching = strict_trap_matching

    def evaluate_equivalence(
        self,
        coq_trace: List[CanonicalState],
        rust_trace: List[CanonicalState],
        rtl_trace: Optional[List[CanonicalState]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates step-by-step equivalence across CanonicalState objects.
        Returns structured diagnostic object.
        """
        # 1. Length check
        if len(coq_trace) != len(rust_trace):
            return {
                "status": "FAIL",
                "error_type": "LengthMismatch",
                "message": f"Coq emitted {len(coq_trace)} steps, Rust emitted {len(rust_trace)} steps",
                "observed_divergence": {"coq_len": len(coq_trace), "rust_len": len(rust_trace)}
            }

        if rtl_trace and len(rust_trace) != len(rtl_trace):
            return {
                "status": "FAIL",
                "error_type": "LengthMismatch",
                "message": f"Rust emitted {len(rust_trace)} steps, RTL emitted {len(rtl_trace)} steps",
                "observed_divergence": {"rust_len": len(rust_trace), "rtl_len": len(rtl_trace)}
            }

        # 2. Frame-by-frame field evaluation
        num_steps = len(coq_trace)
        for idx in range(num_steps):
            c_step = coq_trace[idx]
            e_step = rust_trace[idx]
            step_num = idx + 1

            # HEC match
            if c_step.reg_hec != e_step.reg_hec:
                return {
                    "status": "FAIL",
                    "error_type": "StateDivergence",
                    "failing_step": step_num,
                    "mismatched_field": "reg_hec",
                    "canonical_expected": {"coq": c_step.reg_hec},
                    "observed_divergence": {"rust": e_step.reg_hec}
                }

            # Trap status match
            if c_step.trap.triggered != e_step.trap.triggered:
                return {
                    "status": "FAIL",
                    "error_type": "TrapStatusMismatch",
                    "failing_step": step_num,
                    "mismatched_field": "trap.triggered",
                    "canonical_expected": {"coq": c_step.trap.triggered},
                    "observed_divergence": {"rust": e_step.trap.triggered}
                }

            # STCR file match
            for r in range(32):
                c_stcr = c_step.stcr[r]
                e_stcr = e_step.stcr[r]

                if c_stcr.valid != e_stcr.valid:
                    return {
                        "status": "FAIL",
                        "error_type": "StateDivergence",
                        "failing_step": step_num,
                        "mismatched_field": f"stcr[{r}].valid",
                        "canonical_expected": {"coq": c_stcr.valid},
                        "observed_divergence": {"rust": e_stcr.valid}
                    }
                if c_stcr.valid:
                    if c_stcr.permissions != e_stcr.permissions:
                        return {
                            "status": "FAIL",
                            "error_type": "StateDivergence",
                            "failing_step": step_num,
                            "mismatched_field": f"stcr[{r}].permissions",
                            "canonical_expected": {"coq": c_stcr.permissions},
                            "observed_divergence": {"rust": e_stcr.permissions}
                        }
                    if c_stcr.epoch != e_stcr.epoch:
                        return {
                            "status": "FAIL",
                            "error_type": "StateDivergence",
                            "failing_step": step_num,
                            "mismatched_field": f"stcr[{r}].epoch",
                            "canonical_expected": {"coq": c_stcr.epoch},
                            "observed_divergence": {"rust": e_stcr.epoch}
                        }

            # RTL 3-way check if RTL trace present
            if rtl_trace:
                r_step = rtl_trace[idx]
                if e_step.reg_hec != r_step.reg_hec:
                    return {
                        "status": "FAIL",
                        "error_type": "StateDivergence",
                        "failing_step": step_num,
                        "mismatched_field": "reg_hec",
                        "canonical_expected": {"rust": e_step.reg_hec},
                        "observed_divergence": {"rtl": r_step.reg_hec}
                    }
                if e_step.trap.triggered != r_step.trap.triggered:
                    return {
                        "status": "FAIL",
                        "error_type": "TrapStatusMismatch",
                        "failing_step": step_num,
                        "mismatched_field": "trap.triggered",
                        "canonical_expected": {"rust": e_step.trap.triggered},
                        "observed_divergence": {"rtl": r_step.trap.triggered}
                    }

                for r in range(32):
                    e_stcr = e_step.stcr[r]
                    r_stcr = r_step.stcr[r]
                    if e_stcr.valid != r_stcr.valid:
                        return {
                            "status": "FAIL",
                            "error_type": "StateDivergence",
                            "failing_step": step_num,
                            "mismatched_field": f"stcr[{r}].valid",
                            "canonical_expected": {"rust": e_stcr.valid},
                            "observed_divergence": {"rtl": r_stcr.valid}
                        }
                    if e_stcr.valid:
                        if e_stcr.permissions != r_stcr.permissions:
                            return {
                                "status": "FAIL",
                                "error_type": "StateDivergence",
                                "failing_step": step_num,
                                "mismatched_field": f"stcr[{r}].permissions",
                                "canonical_expected": {"rust": e_stcr.permissions},
                                "observed_divergence": {"rtl": r_stcr.permissions}
                            }
                        if e_stcr.epoch != r_stcr.epoch:
                            return {
                                "status": "FAIL",
                                "error_type": "StateDivergence",
                                "failing_step": step_num,
                                "mismatched_field": f"stcr[{r}].epoch",
                                "canonical_expected": {"rust": e_stcr.epoch},
                                "observed_divergence": {"rtl": r_stcr.epoch}
                            }

        return {
            "status": "PASS",
            "evaluated_steps": num_steps,
            "targets_checked": 3 if rtl_trace else 2,
            "message": "1:1 State Equivalence Confirmed Across Evaluated Targets"
        }
