name: 📜 Formal Proof Obligation
description: Track or report a Coq formal verification gap, theorem requirement, or proof maintenance issue
title: "proof: "
labels: ["formal-verification", "coq", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Use this template for tracking Coq formal proofs, refinement theorems, or proof maintenance.

  - type: textarea
    id: theorem-scope
    attributes:
      label: 📜 Theorem & Formal Scope
      description: Specify the target Coq module and theorem statement.
      placeholder: e.g. verification/Phase8ResourceAuthorityConcrete.v -> Theorem simulation_relation_preserved
    validations:
      required: true

  - type: textarea
    id: obligation-details
    attributes:
      label: 🔍 Obligation Details
      description: Describe the proof gap, admit, or refinement mapping to be verified.
      placeholder: Outline the Coq proof goals...
    validations:
      required: true
