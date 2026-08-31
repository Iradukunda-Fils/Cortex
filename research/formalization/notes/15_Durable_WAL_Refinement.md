# Issue #48 Formal Evidence Matrix: Durable WAL Safety & Refinement

## Executive Summary
This document provides the canonical evidence matrix for **Issue #48 (Durable WAL Assurance Gate)** of the Cortex Kernel System. It formalizes the binary record serialization, frame integrity verification, and replay engine of `cortex.tools.kernel.durable_state.DurableStateStore` inside the Coq verification system (`verification/Phase6WALSafety.v`).

The formal model guarantees that state recovery under crash, corruption, sequence gap, and trailing garbage fault models produces a sound prefix state consistent with Phase 5 authority safety invariants (`verification/Phase5Simulation.v`).

---

## 1. Safety & Verification Status Summary

$$\begin{array}{rcl}
\mathbf{\text{Phase 5 Abstract Scheduler Safety}} & = & \mathbf{PROVEN\ (0\ Axioms,\ 0\ Admits\ -\ Phase5LoadBalancerRefinement.v)} \\
\mathbf{\text{Phase 5 Concrete Refinement}} & = & \mathbf{PROVEN\ (0\ Axioms,\ 0\ Admits\ -\ Phase5Simulation.v)} \\
\mathbf{\text{Phase 6 Durable WAL Safety}} & = & \mathbf{PROVEN\ (0\ Axioms,\ 0\ Admits\ -\ Phase6WALSafety.v)} \\
\mathbf{\text{Python WAL Adversarial Suite}} & = & \mathbf{PASSING\ (9/9\ tests\ -\ test\_phase6\_durable\_state.py)} \\
\mathbf{\text{Phase 6 Distributed Authority Model}} & = & \mathbf{NEXT\ STEP\ (\#49\ -\ TLA+)} \\
\mathbf{\text{Performance Optimizations}} & = & \mathbf{FROZEN\ (\#50)}
\end{array}$$

---

## 2. Python $\leftrightarrow$ Coq 10-Theorem Verification Matrix

| Theorem # | Theorem Identifier | Mathematical / Formal Property | Python Mapping (`durable_state.py`) | Coq Machine Check |
|---|---|---|---|---|
| **1** | `replay_empty` | $Replay([]) = S_0$ | `replay_all_records()` on empty file returns initial state | `coqchk: PROVEN (0 Ax, 0 Ad)` |
| **2** | `replay_count_invariant` | $StepCount(Replay(L)) = \|L\|$ | Monotonic step counter tracks total processed frames | `coqchk: PROVEN (0 Ax, 0 Ad)` |
| **3** | `valid_prefix_replay_count` | $L' \sqsubseteq L \Rightarrow StepCount(Replay(L')) = \|L'\|$ | Prefix evaluation tracks valid record length | `coqchk: PROVEN (0 Ax, 0 Ad)` |
| **4** | `replay_deterministic` | $L_1 = L_2 \Rightarrow Replay(L_1) = Replay(L_2)$ | Replay is pure function of WAL frame sequence | `coqchk: PROVEN (0 Ax, 0 Ad)` |
| **5** | `replay_extend` | $Replay(L \mathbin{+\mkern-10mu+} [f]) = Apply(Replay(L), f)$ | Appending a frame updates state incrementally | `coqchk: PROVEN (0 Ax, 0 Ad)` |
| **6** | `seq_monotonic_prefix` | $Monotonic(L_1 \mathbin{+\mkern-10mu+} L_2) \Rightarrow Monotonic(L_1)$ | Prefix of sequence-valid log is sequence-valid | `coqchk: PROVEN (0 Ax, 0 Ad)` |
| **7** | `all_crc_valid_prefix` | $CRCValid(L_1 \mathbin{+\mkern-10mu+} L_2) \Rightarrow CRCValid(L_1)$ | Prefix of CRC-valid log is CRC-valid | `coqchk: PROVEN (0 Ax, 0 Ad)` |
| **8** | `valid_log_prefix_closed` | $Valid(L_1 \mathbin{+\mkern-10mu+} L_2) \Rightarrow Valid(L_1)$ | **Prefix Closure**: Replay-until-error yields safe prefix | `coqchk: PROVEN (0 Ax, 0 Ad)` |
| **9** | `corrupt_frame_rejected` | $\neg CRCValid(f) \Rightarrow \neg Valid(L \mathbin{+\mkern-10mu+} [f] \mathbin{+\mkern-10mu+} R)$ | `WALCorruptRecordError` halts replay prior to corrupt frame | `coqchk: PROVEN (0 Ax, 0 Ad)` |
| **10** | `seq_gap_rejected` | $Seq(f) \neq \|L\| + 1 \Rightarrow \neg Monotonic(L \mathbin{+\mkern-10mu+} [f] \mathbin{+\mkern-10mu+} R)$ | `seq_no != expected` halts replay prior to gap | `coqchk: PROVEN (0 Ax, 0 Ad)` |

---

## 3. Crash & Corruption Fault Model Coverage

1. **Truncated Write (Partial Frame)**:
   - *Formal*: Modeled by prefix length restriction $\|L'\| < \|L\|$.
   - *Python*: `_read_frame` returns `None` on short header or short payload, triggering replay termination at last flush.
2. **Bit-Flip / CRC Corruption**:
   - *Formal*: Theorem 9 (`corrupt_frame_rejected`).
   - *Python*: CRC calculation mismatch raises `WALCorruptRecordError`, halting replay.
3. **Out-of-Order / Missing Frame (Sequence Gap)**:
   - *Formal*: Theorem 10 (`seq_gap_rejected`).
   - *Python*: Monotonic check `record.seq_no != expected_seq_no` breaks replay loop.
4. **Trailing Garbage / Zero Padding**:
   - *Formal*: Theorem 8 (`valid_log_prefix_closed`).
   - *Python*: Non-matching magic bytes or invalid headers halt iteration safely.

---

## 4. Environment & Machine-Check Validation

- **Compiler**: Rocq 9.1.1 / Coq 8.18+
- **Build Command**: `make -C verification`
- **Checker**: `coqchk -R . Cortex Cortex.Phase6WALSafety`
- **Audit Outcome**: `Modules were successfully checked`
- **Total Axioms**: `0`
- **Total Admits**: `0`
- **Conformance Suite**: `215 / 215 tests passing` (`python3 -m unittest discover -s tests/conformance`)

---

## 5. Transition Authorization to Phase 49

With the machine-checked completion of `Phase6WALSafety.v` (0 Axioms, 0 Admits) and 100% Python test parity:
1. **Local Node Persistence**: Formalized and implementation-verified.
2. **Phase 49 Prerequisite**: Local `ReplayState` invariant is established as the node recovery axiom for the upcoming TLA+ distributed authority model.
3. **#50 Freeze**: Rust/Go/FFI optimization freeze remains strictly enforced until #49 consensus modeling completes.
