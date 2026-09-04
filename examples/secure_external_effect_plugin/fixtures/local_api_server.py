"""
Local Deterministic API Server Fixture.

Simulates a real-world external service over stdio JSON-RPC 2.0.
This server runs completely offline and requires no secrets.

Provided Tools:
  - lookup_record:  Returns a deterministic record (idempotent read)
  - store_record:   Stores a key-value record (idempotent write)
  - transfer_funds: Simulates a non-idempotent financial transfer
  - fail:           Always returns an explicit error
  - timeout:        Sleeps forever (tests timeout handling)

Malformed behavior: Returns invalid JSON if tool_name == "malformed".
"""

from __future__ import annotations

import json
import sys
import time


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

    if tool_name == "lookup_record":
        record_id = args.get("record_id", "unknown")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "record_id": record_id,
                                "status": "FOUND",
                                "data": {"name": "Test Record", "value": 42},
                            }
                        ),
                    }
                ]
            },
        }

    elif tool_name == "store_record":
        key = args.get("key", "default")
        value = args.get("value", "")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"key": key, "value": value, "stored": True}
                        ),
                    }
                ]
            },
        }

    elif tool_name == "transfer_funds":
        amount = args.get("amount", 0)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "transfer_id": f"txn_{req_id}",
                                "amount": amount,
                                "status": "COMMITTED",
                            }
                        ),
                    }
                ]
            },
        }

    elif tool_name == "fail":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32000, "message": "Downstream service unavailable"},
        }

    elif tool_name == "timeout":
        # Simulate an unresponsive service
        time.sleep(3600)
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    elif tool_name == "malformed":
        # Return invalid JSON to test malformed response handling
        sys.stdout.write("THIS IS NOT VALID JSON\n")
        sys.stdout.flush()
        sys.exit(0)

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
