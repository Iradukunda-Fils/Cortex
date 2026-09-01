name: 🐛 Bug Report
description: Report a defect, crash, or unexpected behavior in Cortex
title: "fix: "
labels: ["bug", "triage"]
body:
  - type: markdown
    attributes:
      value: |
        Thank you for reporting a bug! Help us reproduce and fix it by providing exact steps and environment details.

  - type: textarea
    id: description
    attributes:
      label: 🐛 Bug Description
      description: Clear and concise description of what the bug is.
      placeholder: Describe what happened...
    validations:
      required: true

  - type: textarea
    id: reproduction
    attributes:
      label: 🔄 Steps to Reproduce
      description: Provide minimal steps or code snippet to reproduce the issue.
      placeholder: |
        1. Run command '...'
        2. Execute task '...'
        3. See error '...'
    validations:
      required: true

  - type: textarea
    id: expected
    attributes:
      label: Expected Behavior
      description: What did you expect to happen instead?
      placeholder: Expected behavior...

  - type: textarea
    id: environment
    attributes:
      label: 🖥️ Environment & System Details
      description: OS version, Python version, uv version, etc.
      placeholder: e.g. Linux x86_64, Python 3.10.12, uv 0.4.0
