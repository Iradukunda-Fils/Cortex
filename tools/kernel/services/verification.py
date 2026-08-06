"""
Verification Service Kernel Contract & Event Consumer
"""

from tools.kernel.schema.contract import ServiceContract
from tools.kernel.schema.event import RawRTLTraceEvent, CommitVerifiedEvent
from tools.kernel.context import RuntimeContext

class VerificationKernelService:
    contract = ServiceContract(
        service_name="VerificationKernelService",
        consumes=[RawRTLTraceEvent],
        produces=[CommitVerifiedEvent]
    )

    def __init__(self, context: RuntimeContext):
        self.context = context
        self.verified_count = 0

    def handle_raw_rtl_trace(self, event: RawRTLTraceEvent) -> None:
        self.verified_count += 1
        # Perform invariant checks (e.g. eff_trap -> trap_cause > 0)
        is_valid = True
        failing_field = None

        if event.eff_trap and event.trap_cause == 0:
            is_valid = False
            failing_field = "trap_cause"

        verified_event = CommitVerifiedEvent(
            parent_event_id=event.event_id,
            root_event_id=event.root_event_id or event.event_id,
            causation_id=event.event_id,
            correlation_id=event.correlation_id,
            session_id=event.session_id,
            step=event.sequence_number,
            verified=is_valid,
            failing_field=failing_field
        )
        self.context.publish(verified_event)
