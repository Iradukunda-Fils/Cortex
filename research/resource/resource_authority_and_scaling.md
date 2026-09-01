# Research Note 22: Resource Authority Mathematics, Scaling Semantics & Recovery Invariants

**Author**: Cortex Core Architecture & Formal Verification Group  
**Refinement Certificate**: `RCA-7.3-v1`  
**Date**: August 27, 2026  
**Status**: APPROVED / NORMATIVE  

---

## 1. Vector Resource Algebra

Let $\mathbf{r} = \langle c, m, g, v, i, n, f, t, s \rangle$ represent the multidimensional resource demand vector:

$$\mathbf{r} \in \mathbb{N}^9 \quad (\text{CPU millicores, Memory bytes, GPU devices, VRAM bytes, I/O IOPS, Network Mbps, FDs, Threads, Storage bytes})$$

Capacity bound vector $\mathbf{K}$ and safety margin vector $\mathbf{M}$ enforce the total capacity safety inequality:

$$\boxed{ \sum_{r \in Active} \mathbf{d}_r + \mathbf{U}_{used} \le \mathbf{K} - \mathbf{M} - \mathbf{\Delta} }$$

---

## 2. Scale-Up / Scale-Down Transition Semantics

Scale-up and scale-down transitions are formalized as explicit atomic mutations on state $S_R$:

$$\text{ScaleUp}(w, g) : S_R \mapsto S_R \cup \{ (w, g, \text{ACTIVE}) \}$$
$$\text{ScaleDownDrain}(w) : S_R \mapsto S_R [ w \mapsto \text{DRAINING} ]$$
$$\text{ScaleDownRetire}(w, g) : S_R \mapsto S_R [ w \mapsto \text{RETIRED} ] \cup \text{Tombstones}(w, g)$$

---

## 3. Recovery Non-Resurrection Proof Theorem

During crash recovery replay $\text{Replay}(D)$:

$$\boxed{ \forall r, Status(r) \in \{RELEASED, EXPIRED, REVOKED\} \implies r \notin ActiveReservations(\text{Replay}(D)) }$$

Recovery reconstructs $S_R$ by replaying log records $D$, isolating terminal reservations in quarantine to prevent resurrecting active demand contributions.
