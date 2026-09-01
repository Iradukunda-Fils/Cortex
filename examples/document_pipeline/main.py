"""
Main entry point for Document Pipeline Workflow Application.
"""

from .workflows.document_workflow import execute_document_pipeline


def main():
    print("=== CORTEX 03_WORKFLOW_APP (DOCUMENT PIPELINE) ===")
    res = execute_document_pipeline("DOC-8849")
    print(f"Workflow ID: {res['workflow_id']}")
    print(f"State:       {res['state']}")
    print(f"Export:      {res['export']}")


if __name__ == "__main__":
    main()
