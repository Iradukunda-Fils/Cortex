"""
Minimal Application Tasks for Cortex Platform.
Demonstrates zero-configuration default task execution (Level 1 Developer API).
"""

import cortex


@cortex.task
def process_text(text: str) -> str:
    """Level 1 task: Zero-configuration default task."""
    return text.upper()


@cortex.task
def compute_summary(data: list) -> dict:
    """Level 1 task: Simple summary task."""
    return {
        "count": len(data),
        "total_chars": sum(len(str(x)) for x in data),
    }
