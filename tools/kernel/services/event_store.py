"""
Event Store & Audit Journal Kernel Service
"""

from typing import List
from tools.kernel.schema.contract import ServiceContract
from tools.kernel.schema.event import Event

class EventStoreService:
    contract = ServiceContract(
        service_name="EventStoreService",
        consumes=[Event],
        produces=[]
    )

    def __init__(self):
        self._log: List[Event] = []

    def record_event(self, event: Event) -> None:
        self._log.append(event)

    def get_log(self) -> List[Event]:
        return list(self._log)
