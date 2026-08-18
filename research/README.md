# Cortex Research & Empirical Benchmarks Index

This directory contains theoretical formalization notes, Coq/RTL proof artifacts, empirical research synthesis documents, benchmark measurements, crash semantics reports, and experimental spike findings.

---

## Directory Navigation Taxonomy

```
research/
├── formalization/                     # Formal Proofs & Theoretical Research
│   ├── notes/                         # Coq, RTL, and mathematical foundation papers (01_Methodology .. FC_09)
│   └── artifacts/                     # Canonical binary test programs & phase trace logs (phase1_5, phase2)
├── synthesis/                         # Overall Architectural Research Syntheses
│   ├── v0.3_research_synthesis.md     # Synthesis of Issues #10-#13 Research Findings
│   └── architecture_gate_synthesis.json
├── recovery/                          # Crash Semantics & Recovery Evidence Research
│   ├── v0.3_process_and_recovery_synthesis.md
│   ├── recovery_and_side_effects.md
│   ├── crash_semantics_report.json
│   └── recovery_semantics_report.json
├── telemetry/                         # Runtime Performance & Telemetry Benchmark Data
│   └── telemetry_research_report.json
└── fault-tolerance/                  # Timeout, Cancellation & Sandbox Intercept Research
    └── timeout_cancellation_report.json
```

---

## Research Index Table

| Category | Document / Report | Format | Focus Area |
|---|---|---|---|
| **Formalization** | [`formalization/notes/`](formalization/notes/) | Markdown / TeX | Formal authority preorders, logical relations, conditional soundness & system design |
| **Formalization** | [`formalization/artifacts/`](formalization/artifacts/) | Binary / JSON | Coq, emulator & RTL pipeline execution trace logs (Phase 1.5 & Phase 2) |
| **Synthesis** | [`synthesis/v0.3_research_synthesis.md`](synthesis/v0.3_research_synthesis.md) | Markdown | Synthesis of telemetry, crash recovery, timeout & architecture gates |
| **Synthesis** | [`synthesis/architecture_gate_synthesis.json`](synthesis/architecture_gate_synthesis.json) | JSON | Machine-readable gate synthesis metrics |
| **Recovery** | [`recovery/v0.3_process_and_recovery_synthesis.md`](recovery/v0.3_process_and_recovery_synthesis.md) | Markdown | Process isolation, crash window classification & evidence model |
| **Recovery** | [`recovery/recovery_and_side_effects.md`](recovery/recovery_and_side_effects.md) | Markdown | Side-effect journal recovery and non-idempotent operation handling |
| **Recovery** | [`recovery/crash_semantics_report.json`](recovery/crash_semantics_report.json) | JSON | Empirical test data for plugin crash scenarios A–F |
| **Recovery** | [`recovery/recovery_semantics_report.json`](recovery/recovery_semantics_report.json) | JSON | Empirical test data for recovery scenarios A–E |
| **Telemetry** | [`telemetry/telemetry_research_report.json`](telemetry/telemetry_research_report.json) | JSON | Non-intrusive latency collector benchmarks & quantile measurements |
| **Fault Tolerance** | [`fault-tolerance/timeout_cancellation_report.json`](fault-tolerance/timeout_cancellation_report.json) | JSON | Cancellation cascade and timeout enforcement research data |
