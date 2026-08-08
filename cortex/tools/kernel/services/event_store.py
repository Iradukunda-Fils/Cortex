"""
Event Store & Audit Journal Kernel Service
"""

from cortex.tools.kernel.schema.contract import ServiceContract
from cortex.tools.kernel.transport import AnyEvent


class EventStoreService:
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
