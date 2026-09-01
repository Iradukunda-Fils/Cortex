"""
Minimal Application Entry Point for Cortex Platform.
Demonstrates: Project -> Install -> Configure -> Run -> Test.
"""

from .tasks import compute_summary, process_text


def run_pipeline() -> dict:
    """Executes minimal text processing and summary tasks."""
    header = process_text("hello cortex developer platform")
    summary = compute_summary(["item1", "item2", "item3"])

    return {
        "header": header,
        "summary": summary,
    }


def main():
    res = run_pipeline()
    print("=== CORTEX 01_MINIMAL_APP OUTPUT ===")
    print(f"Header:  {res['header']}")
    print(f"Summary: {res['summary']}")


if __name__ == "__main__":
    main()
