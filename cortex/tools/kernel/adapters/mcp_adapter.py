"""
Cortex Local Process MCP Adapter (Gate B — Stdio Transport)

Executes MCP tool calls via JSON-RPC over stdio on an isolated subprocess boundary.
Implements ResourceContract. Receives ONLY pre-authorized AdapterExecutionContext.

Security Constraints:
    1. Adapter NEVER evaluates authorization policy.
    2. Adapter NEVER derives idempotency keys.
    3. Adapter NEVER returns raw credentials or internal state to callers.
    4. Adapter NEVER decides retry semantics (reconciliation engine decides).
    5. Subprocess crash → UNKNOWN_EFFECT (cannot determine if side-effect committed).
    6. Malformed response → EFFECT_NOT_APPLIED (deterministic rejection, no ambiguity).
    7. Evidence exceeding MAX_INLINE_EVIDENCE_BYTES → is_reference=True (hash pointer).
"""

from __future__ import annotations

import hashlib
import json
import subprocess

from cortex.tools.kernel.adapter_contract import (
    MAX_INLINE_EVIDENCE_BYTES,
    AdapterExecutionContext,
    AdapterOutcome,
    EffectClassification,
    EffectPayload,
    EvidencePayload,
    ExecutionStatus,
    ResourceContract,
)

# Explicit Named Constants
DEFAULT_MCP_TIMEOUT_SECONDS: float = 5.0
MAX_STDERR_CAPTURE_BYTES: int = 256


class LocalProcessMCPAdapter(ResourceContract):
    """
    Executes MCP tool calls via stdio on an isolated subprocess boundary.

    Governing Principle: Adapter Executes; Authority Decides.

    The adapter receives a pre-authorized AdapterExecutionContext from the
    GatewayAuthorizationGate and executes the tool call against a local MCP
    server subprocess. It handles:
        - Timeout → UNKNOWN_EFFECT
        - Process crash → UNKNOWN_EFFECT
        - Malformed JSON-RPC → EFFECT_NOT_APPLIED
        - Explicit tool error → EFFECT_NOT_APPLIED
        - Evidence > 4KiB → is_reference=True (hash pointer)
    """

    def __init__(
        self,
        server_command: list[str],
        timeout_seconds: float = DEFAULT_MCP_TIMEOUT_SECONDS,
    ) -> None:
        self._server_command = server_command
        self._timeout_seconds = timeout_seconds

    @property
    def resource_type(self) -> str:
        return "adapter.mcp.stdio.v1"

    @property
    def effect_classification(self) -> EffectClassification:
        # Conservative default: Gateway resolves authoritative classification per-operation
        return EffectClassification.UNKNOWN_EFFECT

    def execute_effect(
        self,
        ctx: AdapterExecutionContext,
        payload: EffectPayload,
    ) -> AdapterOutcome:
        """
        Executes a pre-authorized MCP tool call across the stdio subprocess boundary.

        Args:
            ctx: Pre-authorized execution context from GatewayAuthorizationGate.
            payload: EffectPayload containing serialized tool call specification.

        Returns:
            AdapterOutcome with deterministic execution status and bounded evidence.
        """
        # Parse tool call specification from payload
        try:
            call_spec = json.loads(payload.data.decode("utf-8"))
        except Exception as e:
            return AdapterOutcome(
                status=ExecutionStatus.EFFECT_NOT_APPLIED,
                error_message=f"Payload deserialization failed: {e}",
            )

        tool_name = call_spec.get("tool_name", "")
        tool_arguments = call_spec.get("arguments", {})

        if not tool_name:
            return AdapterOutcome(
                status=ExecutionStatus.EFFECT_NOT_APPLIED,
                error_message="Missing 'tool_name' in payload specification.",
            )

        # Construct JSON-RPC 2.0 request
        rpc_request = {
            "jsonrpc": "2.0",
            "id": ctx.adapter_request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": tool_arguments,
            },
        }

        # Execute via subprocess stdio boundary
        # Step A: Spawn subprocess (OSError domain)
        try:
            proc = subprocess.Popen(
                self._server_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as e:
            return AdapterOutcome(
                status=ExecutionStatus.EFFECT_NOT_APPLIED,
                error_message=f"Failed to spawn MCP subprocess: {e}",
            )

        # Step B: Communicate with subprocess (TimeoutExpired domain)
        # proc is guaranteed to be initialized at this point.
        try:
            stdout_data, stderr_data = proc.communicate(
                input=json.dumps(rpc_request) + "\n",
                timeout=self._timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            # Kill → Drain → Reap: communicate() after kill() drains remaining
            # pipe data and reaps the child, preventing zombies and pipe deadlocks.
            proc.kill()
            proc.communicate()  # Drain pipes and wait for process exit
            return AdapterOutcome(
                status=ExecutionStatus.UNKNOWN_EFFECT,
                error_message=f"MCP stdio process timed out after {self._timeout_seconds}s",
            )
        except Exception as e:
            # Unexpected I/O error during communication — same drain discipline
            proc.kill()
            proc.communicate()
            return AdapterOutcome(
                status=ExecutionStatus.UNKNOWN_EFFECT,
                error_message=f"Subprocess communication error: {e}",
            )

        # Process crash → UNKNOWN_EFFECT (cannot determine if side-effect committed)
        if proc.returncode != 0:
            truncated_stderr = (stderr_data or "").strip()[:MAX_STDERR_CAPTURE_BYTES]
            return AdapterOutcome(
                status=ExecutionStatus.UNKNOWN_EFFECT,
                error_message=(
                    f"MCP process exited with code {proc.returncode}. "
                    f"stderr: {truncated_stderr}"
                ),
            )

        # Parse JSON-RPC response — malformed output → EFFECT_NOT_APPLIED
        stdout_stripped = (stdout_data or "").strip()
        if not stdout_stripped:
            return AdapterOutcome(
                status=ExecutionStatus.EFFECT_NOT_APPLIED,
                error_message="Empty response from MCP server.",
            )

        try:
            rpc_response = json.loads(stdout_stripped)
        except (json.JSONDecodeError, ValueError) as e:
            return AdapterOutcome(
                status=ExecutionStatus.EFFECT_NOT_APPLIED,
                error_message=f"Malformed JSON-RPC response from MCP server: {e}",
            )

        # JSON-RPC error object → EFFECT_NOT_APPLIED (server explicitly rejected)
        if "error" in rpc_response:
            error_msg = rpc_response["error"].get(
                "message", "MCP tool execution failed"
            )
            return AdapterOutcome(
                status=ExecutionStatus.EFFECT_NOT_APPLIED,
                error_message=error_msg,
            )

        # Successful execution: extract and bound evidence payload
        result_data = rpc_response.get("result", {})
        result_bytes = json.dumps(result_data, sort_keys=True).encode("utf-8")

        if len(result_bytes) > MAX_INLINE_EVIDENCE_BYTES:
            # Evidence exceeds 4KiB → spool to reference pointer
            content_hash = hashlib.sha256(result_bytes).hexdigest()
            ref_pointer = f"sha256:{content_hash}:{len(result_bytes)}".encode("utf-8")
            evidence = EvidencePayload(data=ref_pointer, is_reference=True)
        else:
            evidence = EvidencePayload(data=result_bytes)

        return AdapterOutcome(
            status=ExecutionStatus.EFFECT_CONFIRMED,
            evidence=evidence,
        )
