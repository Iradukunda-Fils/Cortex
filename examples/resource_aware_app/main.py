"""
Entry Point for 02_resource_aware_app.
Demonstrates invoking tasks with explicit resource constraints.
"""

from .tasks import compute_heavy_aggregations, run_model_inference


def run_pipeline() -> dict:
    """Executes resource-aware tasks."""
    agg = compute_heavy_aggregations(["doc_a", "doc_b", "doc_c"])
    inf = run_model_inference("BATCH-001")

    return {
        "aggregations": agg,
        "inference": inf,
    }


def main():
    res = run_pipeline()
    print("=== CORTEX 02_RESOURCE_AWARE_APP OUTPUT ===")
    print(f"Aggregations: {res['aggregations']}")
    print(f"Inference:    {res['inference']}")


if __name__ == "__main__":
    main()
