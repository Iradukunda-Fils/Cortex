"""
Cortex Local Stdio MCP Test Server

A controlled local MCP server implementing JSON-RPC 2.0 over stdio for
adversarial testing of the External Effect Adapter pipeline.

Tools:
    echo            - Returns arguments as-is (deterministic, idempotent)
    fail            - Returns explicit JSON-RPC error (deterministic failure)
    slow            - Sleeps for configurable duration (timeout testing)
    large_response  - Returns payload exceeding evidence size bounds
    ambiguous_effect - Crashes mid-execution (UNKNOWN_EFFECT testing)

Usage:
    python tests/fixtures/local_mcp_server.py
    (Reads JSON-RPC requests from stdin, writes responses to stdout)
"""

import json
import sys
import time


def handle_request(req: dict) -> dict:
    """Routes JSON-RPC tool/call requests to the appropriate handler."""
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params", {})
    tool_name = params.get("name", "")
    args = params.get("arguments", {})

    if method != "tools/call":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    # --- Tool Implementations ---

    if tool_name == "echo":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(args)}]
            },
        }

    elif tool_name == "fail":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32000,
                "message": "Explicit tool execution failure",
            },
        }

    elif tool_name == "slow":
        delay = float(args.get("delay_seconds", 2.0))
        time.sleep(delay)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": "Completed slow task"}]
            },
        }

    elif tool_name == "large_response":
        size_bytes = int(args.get("size_bytes", 8192))
        large_text = "A" * size_bytes
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": large_text}]
            },
        }

    elif tool_name == "ambiguous_effect":
        # Simulates crash after partial execution — status is genuinely unknown
        sys.stderr.write(
            "CRITICAL: Internal state ambiguous, crashing process\n"
        )
        sys.stderr.flush()
        sys.exit(137)

    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32602,
                "message": f"Unknown tool: {tool_name}",
            },
        }


def main() -> None:
    """Main loop: reads JSON-RPC from stdin, writes responses to stdout."""
    for line in sys.stdin:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            req = json.loads(stripped)
            res = handle_request(req)
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}",
                },
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
