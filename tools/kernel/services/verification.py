"""
Verification Service Kernel Contract

Consumes: RawRTLTraceEvent (verification domain), DriverTelemetryEvent (kernel domain)
Produces: CommitVerifiedEvent (verification domain), VerificationResultEvent (kernel domain)

This service bridges two event hierarchies:
  1. The verification substrate (event.py: RawRTLTraceEvent → CommitVerifiedEvent)
  2. The kernel runtime (message.py: DriverTelemetryEvent → VerificationResultEvent)

This is an intentional design decision — the verification service is the
only component that legitimately spans both domains.
"""

from typing import Callable, Any, Optional
from tools.kernel.schema.contract import ServiceContract
from tools.kernel.schema.event import RawRTLTraceEvent, CommitVerifiedEvent
from tools.kernel.schema.message import DriverTelemetryEvent, VerificationResultEvent
from tools.kernel.context import RuntimeContext


class VerificationKernelService:
    contract = ServiceContract(
        service_name="VerificationKernelService",
        consumes=[RawRTLTraceEvent, DriverTelemetryEvent],
        produces=[CommitVerifiedEvent, VerificationResultEvent],
    )

    def __init__(self, context: RuntimeContext, publish_cb: Optional[Callable[[Any], None]] = None):
        self.context = context
        self.publish_cb = publish_cb or context.publish
        self.verified_count = 0

    # -- Verification Domain (event.py hierarchy) --------------------------

    def handle_raw_rtl_trace(self, event: RawRTLTraceEvent) -> None:
        """Evaluates RTL trace frames against CommitContractV1 invariants."""
        self.verified_count += 1
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
            failing_field=failing_field,
        )
        self.publish_cb(verified_event)

    # -- Kernel Runtime Domain (message.py hierarchy) ----------------------

    def handle_telemetry(self, event: DriverTelemetryEvent) -> VerificationResultEvent:
        """Evaluates driver telemetry against runtime safety invariants."""
        self.verified_count += 1
        pos = event.payload.get("position", 0.0)
        passed = abs(pos) <= 100.0

        result = VerificationResultEvent(
            causation_id=event.event_id,
            correlation_id=event.correlation_id,
            root_id=event.root_id,
            passed=passed,
            rule_id="BOUNDS_CHECK_V1",
            metrics={"position": pos},
        )
        self.publish_cb(result)
        return result
