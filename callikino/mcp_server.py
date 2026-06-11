"""
Callikino MCP Server — Model Context Protocol
===============================================
Exposes Callikino as an MCP-compatible tool server that any AI agent
environment (Antigravity, Cursor, Claude Desktop, etc.) can connect to.

Run:
    python -m callikino.mcp_server

Or via CLI:
    callikino-mcp

Protocol:
    Communicates over stdin/stdout using JSON-RPC 2.0 (MCP standard).
    Each tool maps 1:1 to a CallikinoEngine method.
"""

import json
import sys
from typing import Dict, Any, Optional

from callikino.core import CallikinoEngine
from callikino.agent_executor import AgentExecutor
from callikino.tool_schemas import TOOL_SCHEMAS


# ---------------------------------------------------------------------------
# MCP Protocol Constants
# ---------------------------------------------------------------------------

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "callikino"
SERVER_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

class CallikinoMCPServer:
    """
    A minimal MCP server that exposes Callikino tools over stdin/stdout.

    Implements the MCP lifecycle:
      1. initialize  -> returns server capabilities
      2. tools/list  -> returns available tools
      3. tools/call  -> executes a tool and returns the result
    """

    def __init__(self):
        self.engine = CallikinoEngine()
        self.executor = AgentExecutor(self.engine)
        self._initialized = False

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Route a JSON-RPC request to the appropriate handler."""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})

        if method == "initialize":
            return self._handle_initialize(req_id, params)
        elif method == "notifications/initialized":
            # Client acknowledgement — no response needed
            return None
        elif method == "tools/list":
            return self._handle_tools_list(req_id)
        elif method == "tools/call":
            return self._handle_tools_call(req_id, params)
        elif method == "ping":
            return self._make_response(req_id, {})
        else:
            return self._make_error(req_id, -32601, f"Method not found: {method}")

    def _handle_initialize(self, req_id: Any, params: Dict) -> Dict:
        """Handle the MCP initialize handshake."""
        self._initialized = True
        return self._make_response(req_id, {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION
            }
        })

    def _handle_tools_list(self, req_id: Any) -> Dict:
        """Return all available tools in MCP format."""
        tools = []
        for schema in TOOL_SCHEMAS:
            fn = schema["function"]
            tools.append({
                "name": fn["name"],
                "description": fn["description"],
                "inputSchema": fn["parameters"]
            })

        return self._make_response(req_id, {"tools": tools})

    def _handle_tools_call(self, req_id: Any, params: Dict) -> Dict:
        """Execute a tool call and return the result."""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        result = self.executor.dispatch({
            "name": tool_name,
            "arguments": arguments
        })

        if result["status"] == "success":
            # Format result as MCP content block
            content_text = json.dumps(result["result"]) if result["result"] is not None else "OK"
            return self._make_response(req_id, {
                "content": [
                    {"type": "text", "text": content_text}
                ]
            })
        else:
            return self._make_response(req_id, {
                "content": [
                    {"type": "text", "text": f"Error: {result['error']}"}
                ],
                "isError": True
            })

    @staticmethod
    def _make_response(req_id: Any, result: Any) -> Dict:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }

    @staticmethod
    def _make_error(req_id: Any, code: int, message: str) -> Dict:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message}
        }


# ---------------------------------------------------------------------------
# stdin/stdout transport
# ---------------------------------------------------------------------------

def run_server():
    """Run the MCP server on stdin/stdout."""
    server = CallikinoMCPServer()

    # Read line-delimited JSON from stdin
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            error_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
            sys.stdout.write(json.dumps(error_resp) + "\n")
            sys.stdout.flush()
            continue

        response = server.handle_request(request)

        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


def main():
    """Entry point for the MCP server."""
    print(f"[callikino-mcp] Starting MCP server v{SERVER_VERSION}...", file=sys.stderr)
    print(f"[callikino-mcp] Listening on stdin/stdout (JSON-RPC 2.0)", file=sys.stderr)
    run_server()


if __name__ == "__main__":
    main()
