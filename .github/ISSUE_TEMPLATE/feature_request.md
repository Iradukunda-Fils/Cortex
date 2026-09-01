name: 🚀 Feature Request
description: Propose a new feature, API symbol, or runtime enhancement for Cortex
title: "feat: "
labels: ["enhancement", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thank you for suggesting a feature! Please provide clear context, requirements, and invariant considerations.

  - type: textarea
    id: problem
    attributes:
      label: 🎯 Problem Statement / Motivation
      description: Is your feature request related to a problem or limitation?
      placeholder: Describe the problem or use case...
    validations:
      required: true

  - type: textarea
    id: solution
    attributes:
      label: 💡 Proposed Solution & Architecture
      description: Describe the technical design or API changes you are proposing.
      placeholder: Outline the proposed implementation...
    validations:
      required: true

  - type: checkboxes
    id: invariant-impact
    attributes:
      label: 🛡️ Invariant & Security Impact
      options:
        - label: This proposal preserves authority attenuation ($P1$).
        - label: This proposal preserves execution parity ($P2$).
        - label: This proposal preserves causal witness non-repudiation ($P3$).
        - label: This proposal preserves zero-dependency untrusted verification ($P4$).
