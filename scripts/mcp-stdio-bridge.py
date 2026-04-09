#!/usr/bin/env python3
"""HUBEX MCP stdio bridge — wraps the HTTP MCP server as a stdio MCP server
that Claude Code can connect to natively.

Usage: python mcp-stdio-bridge.py [--verbose] <email> <password>
"""

import argparse
import json
import sys
import time
import requests

BASE = "http://localhost:8000"
MCP = f"{BASE}/api/v1/mcp"

VERBOSE = False
TOKEN = None
TOKEN_ACQUIRED_AT = 0.0
TOKEN_LIFETIME = 3500  # refresh after ~58 min (tokens typically last 60 min)


def log(msg: str) -> None:
    """Always log to stderr so Claude Code can see issues."""
    print(f"[hubex-bridge] {msg}", file=sys.stderr, flush=True)


def debug(msg: str) -> None:
    """Log only in verbose mode."""
    if VERBOSE:
        print(f"[hubex-bridge:debug] {msg}", file=sys.stderr, flush=True)


def get_token(email: str, password: str, force: bool = False) -> str:
    global TOKEN, TOKEN_ACQUIRED_AT
    # Return cached token if still valid
    if TOKEN and not force and (time.monotonic() - TOKEN_ACQUIRED_AT) < TOKEN_LIFETIME:
        return TOKEN

    if force:
        debug("Token refresh forced (expired or failed request)")
    else:
        debug("Acquiring initial token")

    try:
        r = requests.post(
            f"{BASE}/api/v1/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        r.raise_for_status()
        TOKEN = r.json()["access_token"]
        TOKEN_ACQUIRED_AT = time.monotonic()
        debug("Token acquired successfully")
    except Exception as e:
        log(f"Login failed: {e}")
        TOKEN = ""
    return TOKEN


def headers(email: str, password: str) -> dict:
    return {"Authorization": f"Bearer {get_token(email, password)}", "Content-Type": "application/json"}


def handle_request(req: dict, email: str, password: str) -> dict | None:
    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params", {})

    debug(f"<-- {method} (id={req_id})")

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
            r = requests.post(f"{MCP}/tools/list", headers=headers(email, password), json={}, timeout=10)
            r.raise_for_status()
            tools = r.json().get("tools", [])
            debug(f"tools/list returned {len(tools)} tools")
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                log("Token expired during tools/list, refreshing...")
                get_token(email, password, force=True)
                try:
                    r = requests.post(f"{MCP}/tools/list", headers=headers(email, password), json={}, timeout=10)
                    r.raise_for_status()
                    tools = r.json().get("tools", [])
                except Exception as e2:
                    log(f"tools/list retry failed: {e2}")
                    tools = []
            else:
                log(f"tools/list error: {e}")
                tools = []
        except Exception as e:
            log(f"tools/list error: {e}")
            tools = []
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        debug(f"tools/call: {tool_name} args={json.dumps(arguments)[:200]}")

        def _do_call():
            r = requests.post(
                f"{MCP}/tools/call",
                headers=headers(email, password),
                json={"name": tool_name, "arguments": arguments},
                timeout=30,
            )
            r.raise_for_status()
            return r

        try:
            r = _do_call()
            result = r.json()
            # The /tools/call endpoint returns ToolCallResponse with content/isError
            debug(f"tools/call result: isError={result.get('isError', False)}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": result.get("content", [{"type": "text", "text": json.dumps(result)}]),
                    "isError": result.get("isError", False),
                },
            }
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                log(f"Token expired during tools/call ({tool_name}), refreshing...")
                get_token(email, password, force=True)
                try:
                    r = _do_call()
                    result = r.json()
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": result.get("content", [{"type": "text", "text": json.dumps(result)}]),
                            "isError": result.get("isError", False),
                        },
                    }
                except Exception as e2:
                    log(f"tools/call retry failed ({tool_name}): {e2}")
                    return {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"Error: {e2}"}],
                            "isError": True,
                        },
                    }
            log(f"tools/call error ({tool_name}): {e}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                },
            }
        except Exception as e:
            log(f"tools/call error ({tool_name}): {e}")
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                },
            }

    log(f"Unknown method: {method}")
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def main():
    global VERBOSE

    parser = argparse.ArgumentParser(description="HUBEX MCP stdio bridge")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("email", nargs="?", default="test@test.com", help="Login email")
    parser.add_argument("password", nargs="?", default="Test1234!", help="Login password")
    args = parser.parse_args()

    VERBOSE = args.verbose

    log(f"Starting HUBEX MCP bridge (user={args.email}, verbose={VERBOSE})")
    log(f"Backend: {BASE}")

    # Pre-authenticate
    token = get_token(args.email, args.password)
    if not token:
        log("FATAL: Could not authenticate. Check email/password and backend availability.")
        sys.exit(1)

    log("Authenticated successfully. Waiting for JSON-RPC requests on stdin...")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            log(f"Invalid JSON on stdin: {e}")
            continue

        response = handle_request(req, args.email, args.password)
        if response is not None:
            out = json.dumps(response)
            debug(f"--> {out[:200]}")
            sys.stdout.write(out + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
