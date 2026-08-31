"""
Resource-Aware Application Tasks for Cortex Platform.
Demonstrates Level 2 Developer API: Declarative Resource Requirements.

Mental Model:
Declare Need -> Cortex Handles Reservation
No manual calls to reserve(), lease(), generation(), or release().
"""

import cortex


@cortex.task(
    resources={
        "cpu": "2",
        "memory": "4GiB",
    },
    timeout=30.0,
    retries=2,
)
def compute_heavy_aggregations(dataset: list) -> dict:
    """CPU and Memory-aware batch processing task."""
    total_val = sum(len(str(item)) for item in dataset)
    return {
        "status": "PROCESSED",
        "item_count": len(dataset),
        "total_value": total_val,
    }


@cortex.task(
    resources={
        "cpu": "4",
        "memory": "8GiB",
        "gpu": 1,
        "vram": "8GiB",
    },
    timeout=60.0,
)
def run_model_inference(batch_id: str) -> dict:
    """GPU and VRAM-aware model inference task."""
    return {
        "batch_id": batch_id,
        "status": "COMPLETED",
        "predictions": [0.95, 0.88, 0.99],
    }
