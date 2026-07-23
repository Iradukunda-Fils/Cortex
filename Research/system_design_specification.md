# Cortex System Design Specification (SDS)
*Version: 1.0.0-draft*  
*Status: SYSTEM PROTO-DESIGN*

This document translates the verified spatiotemporal operational semantics ($\mathtt{step\_m}$) of the Cortex framework into a concrete Hardware/Software System Design Specification (SDS). This SDS serves as the blueprint for an architectural emulator or Register Transfer Level (RTL) hardware prototype.

---

## 1. STCR Instruction Set Architecture (ISA) Extension

We propose three assembly-level instructions to manipulate spatiotemporal capability registers and manage hardware epoch progression. 

### 1.1 Instruction: `invoke_cap $stcr, $arg`

*   **Format:** `invoke_cap $stcr_d, $arg_s`
*   **Behavior (Operational Semantics):**
    Checks the descriptor stored in register `$stcr_d` against active hardware constraints.
    ```
    if (REG_HEC <= $stcr_d.Max_Epoch) && 
       ($stcr_d.V == 1) && 
       ($stcr_d.Spatial_Mask & REQUIRED_PERM_INVOKE) != 0:
        // Execute operation under the authority of cap
        EXECUTE_INVOCATION($stcr_d.Base_Address, $arg_s)
    else:
        // Trapped operation: clear destination register and raise trap flag
        $stcr_d.V <- 0
        $stcr_d.Spatial_Mask <- 0
        $stcr_d.Base_Address <- 0
        $stcr_d.Max_Epoch <- 0
        SET_SYS_STATUS_FLAG(TRAP_BIT)
        RAISE_HARDWARE_TRAP()
    ```
*   **Pipeline Actions:**
    - Evaluated during the **Decode (ID)** and **Execute (EX)** stages.
    - Inhibits write-back and memory store operations until the guard evaluation completes.

### 1.2 Instruction: `restrict_cap $stcr_d, $mask_s`

*   **Format:** `restrict_cap $stcr_d, $mask_s`
*   **Behavior (Operational Semantics):**
    Allows unprivileged code to contract spatial authority ($\Lambda' \subseteq \Lambda$) by performing a bitwise `AND` on the capability's spatial mask.
    ```
    if ($stcr_d.V == 1):
        // Atomically mask off unauthorized bits
        $stcr_d.Spatial_Mask <- $stcr_d.Spatial_Mask & $mask_s
    else:
        RAISE_FAULT(GP_FAULT)  // General Protection Fault on invalid register access
    ```
*   **Pipeline Actions:**
    - Commits in the **Writeback (WB)** stage.
    - Cannot enable bits that were not already active (enforcing hardware-level monotonicity).

### 1.3 Instruction: `hec.inc`

*   **Format:** `hec.inc` (Implicit destination `REG_HEC`)
*   **Behavior (Operational Semantics):**
    Increments the Hardware Epoch Counter ($\mathtt{REG\_HEC}$) to advance the temporal epoch ($\nu \to \nu'$).
    ```
    if (CURRENT_CPU_RING == PRIVILEGED_KERNEL_RING):
        if (REG_HEC < 0xFFFF):
            REG_HEC <- REG_HEC + 1
        else:
            RAISE_FAULT(HEC_OVERFLOW_FAULT)  // Handled by hypervisor / rekeying
    else:
        RAISE_FAULT(PRIVILEGE_VIOLATION_FAULT)
    ```
*   **Pipeline Actions:**
    - Must serialize the pipeline (flush instruction fetch queues) to guarantee that all subsequent instructions observe the advanced epoch.

---

## 2. Pipeline Refinement Relation

We formally bridge the abstract semantic state in Coq to physical hardware configurations using a refinement relation $R_{\text{refine}}$.

### 2.1 State Mappings

Let $\mathcal{S}_{\text{formal}} = \langle w, e \rangle$ be a formal state, where $w = (\Lambda, m, n, \nu)$ and $e$ is an expression.  
Let $\mathcal{S}_{\text{hardware}} = (\mathtt{REG\_HEC}, \mathtt{STCR\_File}, \mathtt{Pipeline\_State})$ be a physical hardware state.

We define $R_{\text{refine}}$ such that $\mathcal{S}_{\text{formal}} \propto \mathcal{S}_{\text{hardware}}$ if and only if the following properties hold:

1.  **Temporal Correspondence:**
    $$\mathtt{REG\_HEC} = w.\nu$$
2.  **Spatial Containment Correspondence:**
    For every capability token $c \in \text{Capability}$:
    $$c \in w.\Lambda \iff \exists i. \quad \left( \mathtt{STCR\_File}[i].V == 1 \land \mathtt{STCR\_File}[i].\text{Base\_Address} == \text{cap\_id}(c) \land (\mathtt{STCR\_File}[i].\text{Spatial\_Mask} \neq 0) \right)$$
3.  **Validity Monotonicity:**
    $$\mathtt{valid\_cap}(c, w) \iff \exists i. \quad \left( \mathtt{STCR\_File}[i].\text{Base\_Address} == \text{cap\_id}(c) \land \mathtt{REG\_HEC} \le \mathtt{STCR\_File}[i].\text{Max\_Epoch} \right)$$
4.  **Operational Reduction Mapping:**
    If the formal state reduces via $\mathtt{step\_m}$:
    $$\langle w, e \rangle \xrightarrow{\text{eff}} \langle w', e' \rangle$$
    Then the corresponding hardware pipeline state transitions as a refinement:
    $$(\mathtt{REG\_HEC}, \mathtt{STCR\_File}, \mathtt{Pipeline\_State}) \Longrightarrow (\mathtt{REG\_HEC}', \mathtt{STCR\_File}', \mathtt{Pipeline\_State}')$$
    Matching the effect:
    - If $\text{eff} = \mathtt{eff\_idle}$, the pipeline executes normal instruction retirement or zero-pattern writes ($\mathtt{e\_val}~0$) on trap.
    - If $\text{eff} = \mathtt{eff\_write}(c)$, the pipeline commits bus transactions tagged with target identifier $c$.

---

## 3. MMU and Bus Interface

To prevent Time-of-Check to Time-of-Use (TOCTOU) exploits and satisfy **Contract 1 (Atomic Guard Serialization)**, the Memory Management Unit (MMU) is integrated directly with the capability checks.

```
       CPU Core                       MMU                      System Bus
+--------------------+      +-----------------------+     +------------------+
|                    |      |                       |     |                  |
|  Loads STCR_i      |----> |  Check base/bounds    |     |                  |
|  & issues instruction|    |  Check STCR.V == 1    |     |                  |
|                    |      |  Check REG_HEC <= H   |     |                  |
|                    |      |                       |     |                  |
|  *Guard FAILS*     |      |  *Block Transaction*   |     |                  |
|  Pipeline Trapped  | <----|  - Send Bus Abort     |     |                  |
|  STCR_i <- 0       |      |  - Set Status IRR     |     |                  |
|                    |      +-----------------------+     |                  |
|                    |                                    |                  |
|  *Guard PASSES*    |                                    |  Issue Physical  |
|  Commit Execution  |----------------------------------->|  Read/Write Trans|
|                    |                                    |                  |
+--------------------+                                    +------------------+
```

### 3.1 Hardware Bus-Transaction Guard

When a capability-derived instruction issues a bus address $A$, the transaction is physically tagged with the active register's properties:
$$\text{TX\_Tag} = \langle \text{Base}, \text{Mask}, \text{Max\_Epoch} \rangle$$

The hardware bus controller evaluates the following gating condition atomically at the memory controller boundary:
$$\text{Gate\_Pass} = \left( A \ge \text{Base} \land A < \text{Base} + \text{Bounds} \right) \land \left( \mathtt{REG\_HEC} \le \text{Max\_Epoch} \right)$$

If $\text{Gate\_Pass}$ evaluates to false:
1.  The bus controller asserts an **Atomic Transaction Abort (ATA)**.
2.  The memory write-enable line is held low (deasserted) to block state changes.
3.  The pipeline executes neutral trap routing on the requesting destination register.

---

## 4. Microkernel IPC Contract (ABI)

Operating systems running on Cortex-compliant hardware must maintain spatiotemporal boundaries during context switching and Inter-Process Communication (IPC).

### 4.1 Process Context Switch ABI

During a thread switch, the microkernel is responsible for saving and restoring the entire spatiotemporal register set.

*   **Context Save Routine:**
    ```assembly
    // Save STCRs to Thread Control Block (struct TCB)
    svcap $stcr0, TCB_offsetof_stcr0($process_ptr)
    svcap $stcr1, TCB_offsetof_stcr1($process_ptr)
    ...
    // Save active epoch metadata
    rdhec $r1
    store $r1, TCB_offsetof_saved_epoch($process_ptr)
    ```
*   **Context Restore Routine:**
    When restoring, the microkernel reads the process's recorded epoch and compares it against the active hardware HEC:
    ```
    if (TCB.saved_epoch < REG_HEC):
        // Stale epoch observed during restoration.
        // Stale registers will safely trap at execution time.
    ```

### 4.2 IPC Authority Delegation Contract

When a sender process ($P_S$) delegates a spatiotemporal capability to a receiver process ($P_R$) through microkernel IPC:
1.  **Monotonic Spatial Check:** The microkernel validates that the delegated spatial mask $\Lambda_{\text{del}}$ is a subset of the sender's mask:  
    $$\Lambda_{\text{del}} \subseteq \Lambda_S$$
2.  **Monotonic Temporal Transitivity:** The microkernel enforces that the delegated capability epoch boundary $\nu_{\text{del}}$ is bounded by the sender's register limit:
    $$\nu_{\text{del}} \le \nu_S$$
3.  **Register Loading:** On IPC delivery, the microkernel populates the target register in $P_R$'s context file, verifying that $V=1$. If the current hardware counter value $\mathtt{REG\_HEC}$ already exceeds $\nu_{\text{del}}$, the kernel loads the capability as a pre-invalidated descriptor, forcing immediate containment traps on any invocation.

---

## 5. Verification & Emulation Blueprint

To validate hardware implementations against the Coq specification, prototype builds follow a formal co-simulation architecture.

### 5.1 RISC-V Spike / QEMU Emulator Extension

A software emulator (e.g., Spike or QEMU) is extended with STCR state registers and custom instruction decoders for `invoke_cap`, `restrict_cap`, and `hec.inc`.

*   **Co-Simulation Interface:** At every instruction retirement, the emulator logs a execution trace tuple:
    $$\tau = \langle \text{PC}, \mathtt{REG\_HEC}, \text{STCR\_State}, \text{Bus\_Effect} \rangle$$
*   **Trace Equivalence Testing:** An automated checker replay tool maps $\tau$ to the operational step relation $\mathtt{step\_m}$ in Coq via $R_{\text{refine}}$, asserting zero trace divergence.

### 5.2 Verilog / Chisel Hardware Prototype Strategy

For RTL implementations (e.g., in Chisel or SystemVerilog):
1.  **Decoder Unit:** Implements parallel comparison of `REG_HEC` and `STCR.Max_Epoch` alongside opcode decode.
2.  **Control Pipeline:** On validation failure during `invoke_cap`, the pipeline controller injects a `TRAP_CLEAR` micro-operation into the execution stage to zero out the register destination, emitting an interrupt signal (`eff_trap`).

---

## 6. Formal Traceability & Enforcement Summary

| Formal Semantic Concept (`Semantics.v` / `World.v`) | System Design Component | Hardware / Software Enforcement Contract |
| :--- | :--- | :--- |
| **Spatiotemporal World Tuple $w = (\Lambda, m, n, \nu)$** | Hardware Registers & Epoch Counter | `REG_HEC` ($\nu$), `STCR_File` ($\Lambda$), Pipeline Fuel ($n$) |
| **World Accessibility $w \sqsubseteq w'$** | `hec.inc` & `restrict_cap` | Monotonic increment of `REG_HEC`, Bitwise AND spatial masks |
| **Capability Validity $\mathtt{valid\_cap}(c, w)$** | Hardware Guard Check | `(REG_HEC <= STCR.Max_Epoch) && (STCR.V == 1)` |
| **Contravariant Capability Decay** | Automatic Expiration | Instantaneous non-monotone expiration across all STCRs as `REG_HEC` advances |
| **Operational Trapping ($\mathtt{step\_m\_invoke\_stale}$)** | Hardware Neutral Trap Pipeline | Zeroing destination register, emitting `eff_idle` / raising trap interrupt |
| **Complete Mediation** | MMU & Bus Interceptor | Atomic guard check gating physical bus transaction prior to writeback |

