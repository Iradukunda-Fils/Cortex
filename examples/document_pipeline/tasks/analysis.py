"""
Document Analysis Task.
"""

import cortex


@cortex.task(
    resources={"cpu": "2", "memory": "2GiB"},
    timeout=30.0,
)
def extract_entities(raw_doc: dict) -> dict:
    """Analyzes raw text content and extracts keywords/entities."""
    text = raw_doc.get("content", "")
    words = text.split()
    entities = [w for w in words if w.istitle() or len(w) > 6]

    return {
        "doc_id": raw_doc["doc_id"],
        "word_count": len(words),
        "entities": list(set(entities)),
    }
