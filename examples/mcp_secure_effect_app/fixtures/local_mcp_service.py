"""
Local Stdio MCP Service Fixture.

Simulates a real-world external MCP service over stdio JSON-RPC 2.0.
Provides tools:
  - echo: Echoes input parameters (idempotent write)
  - generate_report: Generates a large data report payload (>4KiB)
  - fail: Returns explicit execution error
"""

from __future__ import annotations

import json
import sys


def handle_rpc_request(request: dict) -> dict:
    req_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})
    tool_name = params.get("name", "")
    args = params.get("arguments", {})

    if method != "tools/call":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method unsupported: {method}"},
        }

    if tool_name == "echo":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(args)}]},
        }

    elif tool_name == "generate_report":
        size_bytes = int(args.get("size_bytes", 8192))
        report_data = {
            "status": "COMPLETED",
            "records_processed": 500,
            "data_payload": "R" * size_bytes,
        }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(report_data)}]},
        }

    elif tool_name == "audit_log":
        audit_payload = {
            "audit_id": "aud_9901",
            "lineage_verified": True,
            "security_invariants_met": True,
        }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(audit_payload)}]},
        }

    elif tool_name == "rebalance_resources":
        mitigation_payload = {
            "action": "REBALANCE",
            "status": "SUCCESS",
            "allocated_units": 64,
        }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(mitigation_payload)}]},
        }

    elif tool_name == "send_alert":
        notification_payload = {
            "channel": "OPS_TELEMETRY_ALERTS",
            "delivery_status": "DELIVERED",
        }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(notification_payload)}]},
        }

    elif tool_name == "fail":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32000, "message": "Downstream external service error"},
        }

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
        }


def main() -> None:
    for line in sys.stdin:
        line_str = line.strip()
        if not line_str:
            continue
        try:
            req = json.loads(line_str)
            res = handle_rpc_request(req)
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as err:
            res_err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(err)}"},
            }
            sys.stdout.write(json.dumps(res_err) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
