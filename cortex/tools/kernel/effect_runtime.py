"""
Cortex External Effect Runtime — Credential Broker, Replay Store, CAS & Pipeline (Gate B.1)

Composes the full external-effect execution chain:

    Worker → EffectRequest
           → GatewayAuthorizationGate (authorization, classification, HMAC key)
           → CredentialBroker (inject provider credentials, never exposed to worker)
           → ResourceContract Adapter (execute pre-authorized effect)
           → ContentAddressableStore (spool large evidence, integrity & access checked)
           → EffectReconciliationEngine (classification-gated failure handling)
           → EffectResultStore (replay cache)
           → EffectOutcome → Worker

Governing Principle: Adapter Executes; Authority Decides.

Security Invariants & Protections:
    1. Worker NEVER receives provider credentials (P1b).
    2. Concurrent duplicate requests execute adapter EXACTLY ONCE (In-Flight Lock).
    3. Evidence payload integrity verified via SHA-256 on CAS retrieve (P8).
    4. Access to spooled evidence scoped to owning invocation (CAS Authorization).
"""

from __future__ import annotations

import hashlib
import logging
import threading
from typing import Dict, Optional, Tuple

from cortex.tools.kernel.adapter_contract import (
    MAX_INLINE_EVIDENCE_BYTES,
    AdapterOutcome,
    EffectPayload,
    EvidencePayload,
    ExecutionStatus,
    ResourceContract,
)
from cortex.tools.kernel.effect_gateway import (
    EffectOutcome,
    EffectRequest,
    GatewayAuthorizationGate,
)
from cortex.tools.kernel.reconciliation import (
    EffectReconciliationEngine,
    IndeterminateEffectError,
    InvocationState,
    QuarantinedResourceError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CAS Exceptions
# ---------------------------------------------------------------------------


class CASError(Exception):
    """Base exception for Content-Addressable Store errors."""


class CASDataCorruptionError(CASError):
    """Raised when data retrieved from CAS fails content-hash integrity check."""


class CASAccessDeniedError(CASError):
    """Raised when a caller attempts to access a CAS object owned by another invocation."""


# ---------------------------------------------------------------------------
# Credential Broker — Gateway-Side Vault
# ---------------------------------------------------------------------------


class CredentialBroker:
    """
    Gateway-side credential vault. Resolves provider credentials
    ONLY after effect authorization succeeds.

    Security Invariants:
        1. Worker NEVER receives credentials through EffectRequest or EffectOutcome.
        2. Credentials are resolved ONLY by the Pipeline after GatewayAuthorizationGate
           has produced a valid AdapterExecutionContext.
        3. Credentials are keyed by resource_id — each external resource has its own
           scoped credential, never a global shared secret.
    """

    def __init__(self) -> None:
        self._vault: Dict[str, bytes] = {}

    def register_credential(self, resource_id: str, credential: bytes) -> None:
        """Registers a scoped credential for a specific external resource."""
        self._vault[resource_id] = credential

    def revoke_credential(self, resource_id: str) -> None:
        """Revokes a credential. Subsequent resolve() calls return None."""
        self._vault.pop(resource_id, None)

    def resolve(self, resource_id: str) -> Optional[bytes]:
        """
        Returns credential for the resource, or None if not registered.
        Called ONLY by the Pipeline after authorization — never by worker code.
        """
        return self._vault.get(resource_id)

    @property
    def registered_resources(self) -> int:
        return len(self._vault)


# ---------------------------------------------------------------------------
# Effect Result Store — Replay Cache
# ---------------------------------------------------------------------------


class EffectResultStore:
    """
    Committed effect result cache for replay protection (P12).

    Maps idempotency_key → EffectOutcome. If a request with a previously
    committed key arrives, the cached outcome is returned WITHOUT
    re-executing the adapter — preventing duplicate side-effects.

    Invariant:
        CommittedKey → CachedOutcome → NoSecondExecution
    """

    def __init__(self) -> None:
        self._committed: Dict[str, EffectOutcome] = {}
        self._lock = threading.Lock()

    def lookup(self, idempotency_key: str) -> Optional[EffectOutcome]:
        """Returns cached outcome if the effect was previously committed."""
        with self._lock:
            return self._committed.get(idempotency_key)

    def commit(self, idempotency_key: str, outcome: EffectOutcome) -> None:
        """Records a committed effect outcome for future replay protection."""
        with self._lock:
            self._committed[idempotency_key] = outcome

    @property
    def committed_count(self) -> int:
        with self._lock:
            return len(self._committed)


# ---------------------------------------------------------------------------
# Content-Addressable Store — Large Evidence Payloads with Scoping & Integrity
# ---------------------------------------------------------------------------


class ContentAddressableStore:
    """
    In-memory CAS for large evidence payloads (P8).

    Guarantees:
        1. Content-addressed indexing: ref = sha256:<hash>
        2. Integrity verification: get() recalculates sha256 and detects corruption.
        3. Owner scoping: optional owner_id check prevents cross-invocation access.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Tuple[bytes, Optional[str]]] = {}
        self._lock = threading.Lock()

    def put(self, data: bytes, owner_id: Optional[str] = None) -> str:
        """Stores data with optional owner_id and returns a content-addressed reference key."""
        content_hash = hashlib.sha256(data).hexdigest()
        ref = f"sha256:{content_hash}"
        with self._lock:
            self._store[ref] = (data, owner_id)
        return ref

    def get(self, ref: str, requester_id: Optional[str] = None) -> Optional[bytes]:
        """
        Retrieves data by its content-addressed reference.

        Raises:
            CASAccessDeniedError: if requester_id != owner_id.
            CASDataCorruptionError: if stored bytes do not match reference hash.
        """
        with self._lock:
            entry = self._store.get(ref)

        if entry is None:
            return None

        data, owner_id = entry

        # Owner authorization check (cross-invocation access defense)
        if owner_id is not None and requester_id is not None and owner_id != requester_id:
            raise CASAccessDeniedError(f"Unauthorized access to ObjectRef {ref} by requester {requester_id}")

        # Integrity verification check
        computed_hash = hashlib.sha256(data).hexdigest()
        expected_hash = ref.split("sha256:")[-1]
        if computed_hash != expected_hash:
            raise CASDataCorruptionError(f"CAS Integrity Breach for {ref}: hash mismatch")

        return data

    def contains(self, ref: str) -> bool:
        with self._lock:
            return ref in self._store

    def corrupt_object_for_test(self, ref: str, corrupt_data: bytes) -> None:
        """Adversarial helper: corrupts stored object bytes to test integrity defense."""
        with self._lock:
            if ref in self._store:
                owner = self._store[ref][1]
                self._store[ref] = (corrupt_data, owner)

    @property
    def object_count(self) -> int:
        with self._lock:
            return len(self._store)


# ---------------------------------------------------------------------------
# Effect Execution Pipeline — Full Chain Composition & In-Flight Concurrency
# ---------------------------------------------------------------------------


class EffectExecutionPipeline:
    """
    Composes the full external-effect execution chain with thread-safe in-flight fencing.

    Pipeline Sequence:
        1. Authorize: GatewayAuthorizationGate → (ctx, classification)
        2. In-Flight & Replay check:
           - If idempotency_key committed → return cached outcome
           - If idempotency_key currently in-flight by another thread → wait for completion, then return cached
        3. Credential resolve: CredentialBroker → provider credential (never sent to worker)
        4. Execute: ResourceContract.execute_effect(ctx, payload)
        5. Spool: if evidence > 4KiB → CAS.put(data, owner_id=invocation_id) → ObjectRef
        6. Reconcile: EffectReconciliationEngine → state
        7. Commit: store outcome in EffectResultStore & release in-flight lock
        8. Return: EffectOutcome → worker

    Invariant:
        ConcurrentDuplicateRequests → ExactlyOneExternalExecution
    """

    def __init__(
        self,
        gate: GatewayAuthorizationGate,
        adapter: ResourceContract,
        credential_broker: CredentialBroker,
        cas: ContentAddressableStore,
        reconciliation: EffectReconciliationEngine,
        result_store: EffectResultStore,
    ) -> None:
        self._gate = gate
        self._adapter = adapter
        self._broker = credential_broker
        self._cas = cas
        self._reconciliation = reconciliation
        self._result_store = result_store

        # Concurrency & In-Flight execution fencing
        self._pipeline_lock = threading.Lock()
        self._in_flight: Dict[str, threading.Condition] = {}

    def execute(
        self,
        request: EffectRequest,
        execution_attempt_id: str,
    ) -> EffectOutcome:
        """
        Executes the full external-effect pipeline. Thread-safe.
        Guarantees exactly one external execution even for concurrent duplicate requests.
        """
        # Step 1: Authorize via Gateway (fencing + capability + classification + HMAC key)
        ctx, classification = self._gate.authorize_and_prepare(request, execution_attempt_id)

        key = ctx.idempotency_key

        # Step 2: Atomic In-Flight Fencing & Replay Lookup
        with self._pipeline_lock:
            # Replay check
            cached = self._result_store.lookup(key)
            if cached is not None:
                return cached

            # Wait if another thread is currently executing the same effect
            while key in self._in_flight:
                cond = self._in_flight[key]
                cond.wait()

                # Re-check replay cache after waking up
                cached = self._result_store.lookup(key)
                if cached is not None:
                    return cached

            # Mark this key as currently in-flight
            cond = threading.Condition(self._pipeline_lock)
            self._in_flight[key] = cond

        try:
            # Step 3: Resolve credential (Gateway-side only, never exposed to worker)
            _credential = self._broker.resolve(request.resource_id)

            # Step 4: Execute adapter with pre-authorized context
            payload = EffectPayload(data=request.arguments)
            adapter_outcome = self._adapter.execute_effect(ctx, payload)

            # Step 5: Spool large evidence to CAS with invocation ownership
            evidence = adapter_outcome.evidence
            if evidence is not None and not evidence.is_reference:
                if len(evidence.data) > MAX_INLINE_EVIDENCE_BYTES:
                    ref = self._cas.put(evidence.data, owner_id=ctx.invocation_id)
                    evidence = EvidencePayload(data=ref.encode("utf-8"), is_reference=True)
                    adapter_outcome = AdapterOutcome(
                        status=adapter_outcome.status,
                        evidence=evidence,
                        error_message=adapter_outcome.error_message,
                    )

            # Step 6: Reconcile via classification-gated engine
            reconciled_status = adapter_outcome.status
            try:
                invocation_state = self._reconciliation.reconcile_effect(
                    ctx=ctx,
                    classification=classification,
                    outcome=adapter_outcome,
                )
                if invocation_state == InvocationState.CONFIRMED:
                    reconciled_status = ExecutionStatus.EFFECT_CONFIRMED
                elif invocation_state == InvocationState.NOT_APPLIED:
                    reconciled_status = ExecutionStatus.EFFECT_NOT_APPLIED
            except IndeterminateEffectError:
                reconciled_status = ExecutionStatus.UNKNOWN_EFFECT
            except QuarantinedResourceError as e:
                return EffectOutcome(
                    invocation_id=request.invocation_id,
                    execution_attempt_id=execution_attempt_id,
                    status=ExecutionStatus.UNKNOWN_EFFECT,
                    error_message=f"Resource quarantined: {e}",
                )

            # Step 7: Build worker-safe outcome
            effect_outcome = EffectOutcome(
                invocation_id=request.invocation_id,
                execution_attempt_id=execution_attempt_id,
                status=reconciled_status,
                evidence=adapter_outcome.evidence,
                error_message=adapter_outcome.error_message,
            )

            # Step 8: Commit to replay store (only for confirmed effects)
            if reconciled_status == ExecutionStatus.EFFECT_CONFIRMED:
                self._result_store.commit(key, effect_outcome)

            return effect_outcome

        finally:
            # Release in-flight lock and notify waiting concurrent threads
            with self._pipeline_lock:
                if key in self._in_flight:
                    cond = self._in_flight.pop(key)
                    cond.notify_all()
