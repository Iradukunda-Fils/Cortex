# Cortex Long-Term Evolution Roadmap

> **North Star Principle**: Can Cortex become more capable and scalable without increasing developer complexity or weakening safety guarantees?  
> **Longevity Criterion**: Can internal implementations change while semantic contracts remain stable?  
> **Research Protocol**: $\text{Measure} \longrightarrow \text{Model} \longrightarrow \text{Prototype} \longrightarrow \text{Compare} \longrightarrow \text{Migrate}$  

---

## 1. Phased Evolution Roadmap

```
[ NOW: Baseline Hardening ] ──► [ NEXT: Research Gate & Mutation Profiling ]
  - 474 Passed Test Harness      - Independent Latency Profiling (T_lock, T_expiration, T_WAL)
  - Monotonic Lease Fencing      - Min-Heap Priority Queue for Reservation Expiration
  - Durable WAL Record/Replay    - Autonomous Metric-Feedback Autoscaling Loop
                                 - Concurrency Candidate Comparison (RCU, Disruptor, Sharding)

[ LATER: Authoritative Concurrency ] ──► [ RESEARCH: Multi-Node Consensus ]
  - Selected Mutation Concurrency Model  - Multi-Gateway Raft Consensus Across Nodes
  - WASM Sandboxed Worker Runtime        - Cross-Region Vector Resource Scheduling
  - Polyglot Gateway Core (If Proven)     - Zero-Copy Shared Memory Telemetry Buffer
```

---

## 2. Milestone Categorization

| Phase Horizon | Target Milestone | Architectural Focus | Primary Deliverables | Safety Invariant Impact |
| :--- | :--- | :--- | :--- | :--- |
| **NOW** | Single-Host Core Stability | Ground-truth verification, lock attribution profiling | Single-host control plane, 100% test pass rate | Invariants $I_1 \dots I_{12}$ enforced within host boundary |
| **NEXT** | Mutation Concurrency Research Gate | Profile $T_{\text{lock-wait}}$ vs $T_{\text{critical-section}}$ vs $T_{\text{expiration}}$ | Detailed latency profile across $N \in \{10^2 \dots 10^5\}$ and $C \in \{1 \dots 64\}$; min-heap $O(\log N)$ reservation expiration | Maintain single-source-of-truth semantics while scaling concurrency |
| **LATER** | Authoritative Concurrency Engine | Implement top-performing concurrency model | Selected model (RCU, Disruptor, Sharded, Single-Writer) | Capacity Safety ($I_1$) & Single Commit Owner ($I_{11}$) preserved |
| **RESEARCH** | Distributed Multi-Node Federation | Scale beyond single physical host | Multi-Gateway Raft consensus, distributed lease fencing | Monotonic Lease Epoch ($I_2$) expanded to cross-node consensus |
| **UNPROVEN** | Polyglot Gateway Core / Hardware CBE | Rust/Go gateway migration & FPGA decoders | Evaluated ONLY after bottleneck isolation | Semantics & SDK contracts remain identical |

---

## 3. Multi-Decade Architecture Replaceability Protocol

To ensure Cortex can evolve over decades without breaking developer code:

1. **Public API Contract Freeze**: `cortex.CortexClient`, `@task`, and `CortexPlugin` contracts MUST maintain strict backward compatibility. Internal kernel rewrites expose identical Python bindings.
2. **Schema Versioning & Migration**: Declarative manifests enforce explicit `$schema` URIs with automatic migrators in `ConfigResolver`.
3. **Transport Protocol Stability**: CBE binary wire format features immutable magic bytes (`0x434F5254`) and explicit field tagging.
