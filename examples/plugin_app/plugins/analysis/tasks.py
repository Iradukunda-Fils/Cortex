"""
Analysis Plugin Tasks (Pure Python Plugin).
No binding.py or C FFI required!
"""

import cortex


@cortex.task(resources={"cpu": "2", "memory": "1GiB"})
def analyze_payload(payload: dict) -> dict:
    """Standard Python analysis plugin task."""
    content = payload.get("content", "")
    return {
        "source_id": payload.get("source_id"),
        "metrics": {
            "char_count": len(content),
            "word_count": len(content.split()),
        },
    }
