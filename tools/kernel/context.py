"""
Runtime Context Provided to Kernel Actors
"""

from tools.kernel.mailbox import Mailbox
from tools.kernel.schema.event import Event
from tools.kernel.transport import InMemoryTransport

class RuntimeContext:
    def __init__(self, actor_id: str, session_id: str, transport: InMemoryTransport):
        self.actor_id = actor_id
        self.session_id = session_id
        self.mailbox = Mailbox()
        self._transport = transport

    def publish(self, event: Event) -> None:
        self._transport.publish(event)
