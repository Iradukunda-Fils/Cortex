# System Design Specification (SDS) — Version 1.0

## Spatiotemporal Capability Register Architecture

**Project:** Cortex Spatiotemporal Authority Framework  
**Document:** System Design Specification (SDS)  
**Status:** Frozen Version 1.0 — Canonical Specification  
**Purpose:** Formal-to-systems implementation contract for software emulation, RTL prototyping, and formal refinement verification.

---

## 1. Architectural Status Boundary

> **IMPORTANT ARCHITECTURAL NOTICE:**  
> This SDS specifies the intended hardware/software architecture of the Cortex Spatiotemporal Authority Framework. It defines ISA semantics, register layouts, pipeline contracts, and refinement objectives. The document does not constitute a synthesized RTL implementation, FPGA prototype, timing report, or empirically validated hardware artifact. All performance, latency, area, power, and timing claims remain subject to future implementation and measurement.

---

## 2. Scope and Objectives

This specification refines the abstract operational semantics ($\mathtt{step\_m}$) and Kripke world model ($w = (\Lambda, \nu)$) into an implementable hardware/software interface contract.

Primary objectives:
1. Define a concrete 32-bit fixed STCR ISA with deterministic opcode space and reserved instruction handling.
2. Formally define the 64-bit STCR layout and 15-bit `Spatial_Mask` permission bits.
3. Establish an explicit, executable refinement function $encode(c)$ mapping capability descriptors to 64-bit integers.
4. Specify synchronous trap semantics (`eff_trap`) and global $\mathtt{REG\_HEC}$ coherence interfaces.
5. Provide a baseline specification for the Phase 1 software emulator.

---

## 3. Spatiotemporal Capability Register (STCR) Layout

The STCR is a 64-bit hardware register formatted as follows:

| Bits  | Field          | Size    | Description                                                  |
| :---- | :------------- | :------ | :----------------------------------------------------------- |
| 63    | `V`            | 1 bit   | Hardware validity bit (`1` = valid, `0` = invalid / revoked) |
| 62–48 | `Spatial_Mask` | 15 bits | Permitted spatial rights bitmask (Enumerated below)          |
| 47–16 | `Base_Address` | 32 bits | Target physical/virtual base pointer                         |
| 15–0  | `Max_Epoch`    | 16 bits | Temporal expiration epoch ($\nu_c$)                          |

### 3.1 Spatial_Mask Field Bit Enumeration

```text
  62     61     60     59     58    57                                        48
+------+------+------+------+------+--------------------------------------------+
| READ | WRITE| EXEC | DELEG| REVOK|          DOMAIN_TAGS (10 bits)             |
+------+------+------+------+------+--------------------------------------------+
```

* **Bit 62 (`READ`):** Authorizes memory read transactions targeting `Base_Address`.
* **Bit 61 (`WRITE`):** Authorizes memory write transactions targeting `Base_Address`.
* **Bit 60 (`EXEC`):** Authorizes instruction fetch and execution at `Base_Address`.
* **Bit 59 (`DELEG`):** Authorizes copying/granting this capability to another register.
* **Bit 58 (`REVOK`):** Authorizes executing `revoke_cap` against child descriptors.
* **Bits 57–48 (`DOMAIN_TAGS`):** Sub-world partition identifier used for spatial domain intersection checks.

---

## 4. STCR Instruction Set Architecture (ISA)

### 4.1 Fixed 32-Bit Encoding Format

```text
 31      26 25      21 20      16 15                               0
+----------+----------+----------+----------------------------------+
|  Opcode  | STCR_ID  | Arg_Reg  |        Immediate / Mask          |
+----------+----------+----------+----------------------------------+
```

### 4.2 Opcode Map & Reserved Handling

| Opcode | Mnemonic | Privilege Level | Action / Semantics |
| :--- | :--- | :--- | :--- |
| `0x01` | `invoke_cap` | Unprivileged | Atomically checks guard predicate; transfers PC or traps. |
| `0x02` | `grant_cap` | Privileged | Writes descriptor to STCR file entry. |
| `0x03` | `restrict_cap` | Unprivileged | Performs bitwise AND contraction on `Spatial_Mask`. |
| `0x04` | `revoke_cap` | Privileged | Clears V bit and broadcasts bus invalidation. |
| `0x05` | `hec.inc` | Privileged | Monotonically increments global $\mathtt{REG\_HEC}$ by 1. |
| *Others* | *RESERVED* | N/A | Any opcode $\notin \{0x01 \dots 0x05\}$ triggers `eff_trap`. |

---

## 5. Pipeline Trap Semantics & Multicore Memory Ordering

### 5.1 Synchronous Trap Behavior (`eff_trap`)

Guard evaluation occurs during the Decode/Guard stage prior to Execute commit:
$$\text{Guard\_Pass} \iff (\mathtt{STCR.V} == 1) \land ((\mathtt{STCR.Spatial\_Mask} \land \text{Req\_Perm}) \neq 0) \land (\mathtt{REG\_HEC} \le \mathtt{STCR.Max\_Epoch})$$

If $\text{Guard\_Pass}$ evaluates to FALSE (or an illegal opcode is decoded):
1. **Pipeline Flush:** In-flight instructions behind the faulting stage are cancelled.
2. **Neutral Destination:** Target destination register is zeroed ($\mathtt{e\_val}~0$).
3. **Trap Event:** Synchronous `eff_trap` exception signal is raised, causing immediate hardware control transfer to the microkernel exception vector.

### 5.2 Multicore Memory Ordering & Global Scope

* **Global Epoch Counter:** $\mathtt{REG\_HEC}$ is a globally synchronized hardware control register shared across all physical processing cores.
* **Coherence Invalidation:** Executing `revoke_cap` issues an atomic bus invalidation signal across the interconnect, forcing remote CPU L1 STCR caches to clear the corresponding V bit before instruction execution resumes.

---

## 6. Formal Refinement Mapping ($R_{\text{refine}}$, $encode$, & $decode$)

### 6.1 Executable Abstract-to-Concrete Functions

For an abstract capability descriptor $c = (a, \Lambda_c, \nu_c)$:
$$encode(c) \stackrel{\text{def}}{=} (1 \ll 63) \lor ((\text{mask\_bits}(\Lambda_c) \land \mathtt{0x7FFF}) \ll 48) \lor ((a \land \mathtt{0xFFFFFFFF}) \ll 16) \lor (\nu_c \land \mathtt{0xFFFF})$$

Conversely, decoding a 64-bit register value $R \in \mathbb{B}^{64}$ yields:
$$decode(R) \stackrel{\text{def}}{=} \begin{cases} 
\text{Some}\left(\text{address} = (R \gg 16) \land \mathtt{0xFFFFFFFF}, \, \Lambda = \text{parse\_mask}((R \gg 48) \land \mathtt{0x7FFF}), \, \nu_c = R \land \mathtt{0xFFFF}\right) & \text{if } (R \gg 63) == 1 \\
\text{None} & \text{if } (R \gg 63) == 0 
\end{cases}$$

---

## 7. Next Implementation Milestone: Software Emulator (Phase 1)

With Version 1.0 of the SDS frozen, all design development moves directly to Phase 1: Software Emulator Construction.

The software emulator specification:
* **Core Modules:**
  * `stcr_file`: 32x 64-bit register file with encode/decode primitives.
  * `hec`: 16-bit monotonic epoch counter unit.
  * `decoder`: 32-bit ISA instruction decoder with reserved opcode trapping.
  * `guard`: Atomic parallel guard evaluator emitting `eff_trap`.
  * `trace_logger`: JSON/Text state-trace exporter for verifying step-for-step equivalence against formal operational traces ($\mathtt{step\_m}$).

---

## Updated Project Execution Status

| Layer | Status | Artifact / Milestone |
| :--- | :--- | :--- |
| **Formal Semantics** | Verified | Operational Semantics & Kripke Model |
| **Threat Model** | Verified | `threat_model_section.tex` (Defensible evaluation) |
| **System Specs** | Frozen v1.0 | `Research/system_design_specification.md` |
| **Emulator** | NEXT MILESTONE | Software ISA emulator & `step_m` trace logger |
| **RTL / FPGA** | Pending | SystemVerilog/Chisel (Post-emulator) |
