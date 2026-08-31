"""
Document Export Task.
"""

import cortex


@cortex.task(
    resources={"cpu": "1", "memory": "512MiB"},
    timeout=10.0,
)
def export_summary(analysis_result: dict) -> dict:
    """Formats and exports final summary package."""
    return {
        "export_id": f"EXP-{analysis_result['doc_id']}",
        "status": "COMPLETED",
        "word_count": analysis_result["word_count"],
        "entity_count": len(analysis_result["entities"]),
    }
