# Certification Vector: Commit Store

## Purpose
Validates that target commit adapters normalize basic STCR register access and program counter state into canonical `CommitEventV1` instances.

## Expected Commit Events
- Exactly 1 architectural retirement per instruction step.
- STCR0 initial capability descriptor ($V=1$, $\text{mask}=0x7000$, $\text{base}=0x2000$, $\text{epoch}=0$).
