#!/usr/bin/env python3
"""HUBEX MCP stdio bridge — wraps the HTTP MCP server as a stdio MCP server
that Claude Code can connect to natively.

Usage: python mcp-stdio-bridge.py <email> <password>
"""

import json
import sys
import requests

BASE = "http://localhost:8000"
MCP = f"{BASE}/api/v1/mcp"

# Auth: login with email/password to get JWT
EMAIL = sys.argv[1] if len(sys.argv) > 1 else "test@test.com"
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else "Test1234!"

TOKEN = None


def get_token():
    global TOKEN
    if TOKEN:
        return TOKEN
    try:
        r = requests.post(
            f"{BASE}/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD},
            timeout=5,
        )
        r.raise_for_status()
        TOKEN = r.json()["access_token"]
    except Exception as e:
        print(json.dumps({"error": f"Login failed: {e}"}), file=sys.stderr)
        TOKEN = ""
    return TOKEN


def headers():
    return {"Authorization": f"Bearer {get_token()}", "Content-Type": "application/json"}


def handle_request(req: dict) -> dict | None:
    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "hubex", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
        }

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        try:
            r = requests.post(f"{MCP}/tools/list", headers=headers(), json={}, timeout=10)
            r.raise_for_status()
            tools = r.json().get("tools", [])
        except Exception as e:
            print(f"tools/list error: {e}", file=sys.stderr)
            tools = []
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            r = requests.post(
                f"{MCP}/tools/call",
                headers=headers(),
                json={"tool_name": tool_name, "arguments": arguments},
                timeout=30,
            )
            r.raise_for_status()
            result = r.json().get("result", r.json())
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                },
            }
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        response = handle_request(req)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
