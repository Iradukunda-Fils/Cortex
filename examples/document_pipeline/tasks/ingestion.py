"""
Document Ingestion Task.
"""

import cortex


@cortex.task(
    resources={"cpu": "1", "memory": "1GiB"},
    timeout=15.0,
    retries=2,
)
def fetch_document(doc_id: str) -> dict:
    """Simulates fetching raw document payload."""
    if not doc_id:
        raise ValueError("Document ID cannot be empty")

    return {
        "doc_id": doc_id,
        "content": f"Cortex distributed architecture documentation content for {doc_id}",
        "bytes": 512,
    }
