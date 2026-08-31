"""
Ingestion Plugin Tasks (Pure Python Plugin).
No binding.py or C FFI required!
"""

import cortex


@cortex.task(resources={"cpu": "1", "memory": "512MiB"})
def read_payload(source_id: str) -> dict:
    """Standard Python plugin task."""
    return {
        "source_id": source_id,
        "content": f"Ingested text payload from {source_id}",
    }
