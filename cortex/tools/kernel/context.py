"""
Runtime Context Provided to Kernel Actors
"""

from cortex.tools.kernel.mailbox import Mailbox
from cortex.tools.kernel.transport import AnyEvent, InMemoryTransport


class RuntimeContext:
    actor_id: str
    session_id: str
    mailbox: Mailbox
    _transport: InMemoryTransport

    def __init__(self, actor_id: str, session_id: str, transport: InMemoryTransport):
        self.actor_id = actor_id
        self.session_id = session_id
        self.mailbox = Mailbox()
        self._transport = transport

    def publish(self, event: AnyEvent) -> None:
        self._transport.publish(event)
