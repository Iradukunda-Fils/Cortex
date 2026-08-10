"""
Event Store & Audit Journal Kernel Service
"""

from cortex.tools.kernel.schema.contract import ServiceContract
from cortex.tools.kernel.transport import AnyEvent


class EventStoreService:
    """Append-only event journal that records all domain events for a workflow.

    Provides ordered event retrieval for trace persistence, inspection,
    and deterministic replay. This is the public EventStore interface
    re-exported as ``cortex.EventStore``.
    """
    _log: list[AnyEvent]

    contract: ServiceContract = ServiceContract(
        service_name="EventStoreService",
        consumes=[],
        produces=[],
    )

    def __init__(self) -> None:
        self._log = []

    def record_event(self, event: AnyEvent) -> None:
        self._log.append(event)

    def get_log(self) -> list[AnyEvent]:
        return list(self._log)
