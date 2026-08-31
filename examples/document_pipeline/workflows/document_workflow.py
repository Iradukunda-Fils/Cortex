"""
Document Processing Workflow Orchestration.
Integrates tasks into an end-to-end workflow managed via CortexClient.
"""

from cortex import CortexClient, WorkflowState

from ..tasks.analysis import extract_entities
from ..tasks.export import export_summary
from ..tasks.ingestion import fetch_document


def execute_document_pipeline(doc_id: str, client: CortexClient | None = None) -> dict:
    """Executes full document ingestion -> analysis -> export workflow.

    Demonstrates:
    - Intent declaration via CortexClient
    - Step-by-step task composition
    - Handling workflow execution state
    """
    if client is None:
        client = CortexClient()

    # 1. Register workflow intent with Cortex control plane
    workflow = client.create_workflow(
        name="DocumentPipeline",
        goal=f"Process document {doc_id}",
    )

    # 2. Step 1: Ingestion
    raw = fetch_document(doc_id)

    # 3. Step 2: Analysis
    analysis = extract_entities(raw)

    # 4. Step 3: Export
    final_export = export_summary(analysis)

    # 5. Mark workflow completed in Cortex control plane
    executed_wf = client.run_workflow(workflow)

    return {
        "workflow_id": executed_wf.workflow_id,
        "state": executed_wf.state.value if isinstance(executed_wf.state, WorkflowState) else executed_wf.state,
        "export": final_export,
    }
