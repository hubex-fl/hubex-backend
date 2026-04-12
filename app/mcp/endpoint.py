"""MCP HTTP Endpoint (M22 Step 2).

Exposes HUBEX tools via both a JSON-RPC style endpoint and the standard
MCP SSE transport so that external clients (Claude Desktop, AI agents)
can connect using the Model Context Protocol.

Endpoints:
  POST /api/v1/mcp/tools/list    -- list available tools  (legacy JSON-RPC)
  POST /api/v1/mcp/tools/call    -- execute a tool         (legacy JSON-RPC)
  GET  /api/v1/mcp/sse           -- MCP SSE transport
  POST /api/v1/mcp/messages      -- MCP JSON-RPC via SSE session
  GET  /api/v1/mcp/status        -- server status + active connections
  GET  /api/v1/mcp/log           -- recent tool-call access log
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.user import User
from app.mcp.tools import get_tool_definitions
from app.mcp.handler import execute_tool
from app.mcp.system_prompt import SYSTEM_PROMPT
from app.mcp.prompts import PROMPT_TEMPLATES, get_prompt_messages

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/mcp", tags=["mcp"])


# ── In-memory session & log stores ─────────────────────────────────────────

_sessions: dict[str, dict[str, Any]] = {}  # session_id -> {user_id, queue, ...}
_access_log: list[dict[str, Any]] = []     # most-recent first, capped at 200
_MAX_LOG = 200


def _log_access(entry: dict[str, Any]) -> None:
    _access_log.insert(0, entry)
    while len(_access_log) > _MAX_LOG:
        _access_log.pop()


# ── Request/Response schemas ──────────────────────────────────────────────


class ToolCallRequest(BaseModel):
    name: str | None = None
    tool_name: str | None = None  # alias — accept both
    arguments: dict[str, Any] = {}

    @property
    def resolved_name(self) -> str:
        return self.name or self.tool_name or ""


class ToolCallResponse(BaseModel):
    content: list[dict[str, Any]]
    isError: bool = False


class ToolListResponse(BaseModel):
    tools: list[dict[str, Any]]


# ── Auth helper for SSE (accepts query-param key OR Bearer header) ────────


async def _resolve_user_for_sse(
    request: Request,
    key: str | None,
    db: AsyncSession,
) -> User:
    """Authenticate via API key query param *or* Bearer header."""
    from app.core.api_keys import is_api_key
    from app.core.security import hash_device_token, decode_access_token, AuthTokenError
    from app.db.models.api_key import ApiKey

    token: str | None = key

    # Fallback: try Authorization header
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()

    if not token:
        raise HTTPException(status_code=401, detail="missing authentication")

    # API key path
    if is_api_key(token):
        key_hash = hash_device_token(token)
        from sqlalchemy import select
        res = await db.execute(select(ApiKey).where(ApiKey.key_hash == key_hash))
        api_key = res.scalar_one_or_none()
        if not api_key or api_key.revoked:
            raise HTTPException(status_code=401, detail="invalid or revoked API key")
        if api_key.expires_at and api_key.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="API key expired")
        # Check MCP caps
        caps = set(api_key.caps or [])
        if "mcp.read" not in caps and "mcp.execute" not in caps:
            raise HTTPException(status_code=403, detail="API key lacks mcp capabilities")
        api_key.last_used_at = datetime.now(timezone.utc)
        from sqlalchemy import select as _sel
        user_res = await db.execute(_sel(User).where(User.id == api_key.user_id))
        user = user_res.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="user not found")
        return user

    # JWT path
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
    except (AuthTokenError, Exception):
        raise HTTPException(status_code=401, detail="invalid token")

    from sqlalchemy import select as _sel
    res = await db.execute(_sel(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="user not found")
    return user


# ── MCP JSON-RPC helpers ─────────────────────────────────────────────────


def _jsonrpc_response(id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _jsonrpc_error(id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


async def _handle_jsonrpc(
    body: dict[str, Any],
    db: AsyncSession,
    user: User,
) -> dict[str, Any]:
    """Process a single MCP JSON-RPC request and return the response."""
    req_id = body.get("id")
    method = body.get("method", "")
    params = body.get("params", {})
    user_id = user.id

    if method == "initialize":
        return _jsonrpc_response(req_id, {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "hubex-mcp", "version": "1.0.0"},
            "capabilities": {
                "tools": {"listChanged": False},
                # Sprint 9 Step 3: advertise resources + prompts so MCP
                # clients auto-discover the system-prompt and templates.
                "resources": {},
                "prompts": {},
            },
        })

    if method == "notifications/initialized":
        # Client acknowledges -- no response needed for notifications
        return _jsonrpc_response(req_id, {})

    if method == "tools/list":
        tools = get_tool_definitions()
        return _jsonrpc_response(req_id, {"tools": tools})

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        tool_names = {t["name"] for t in get_tool_definitions()}
        if tool_name not in tool_names:
            return _jsonrpc_error(req_id, -32602, f"Unknown tool: {tool_name}")

        t0 = time.monotonic()
        try:
            result = await execute_tool(
                tool_name=tool_name,
                arguments=arguments,
                db=db,
                user=user,
            )
            duration_ms = round((time.monotonic() - t0) * 1000)
            is_error = "error" in result
            _log_access({
                "ts": datetime.now(timezone.utc).isoformat(),
                "tool": tool_name,
                "status": "error" if is_error else "ok",
                "duration_ms": duration_ms,
                "user_id": user_id,
            })
            return _jsonrpc_response(req_id, {
                # ensure_ascii=False so unicode (German umlauts, emoji) passes
                # through as-is instead of \uNNNN escapes that confuse some
                # MCP clients. default=str handles datetime/Decimal/UUID safely.
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
                "isError": is_error,
            })
        except Exception as e:
            duration_ms = round((time.monotonic() - t0) * 1000)
            _log_access({
                "ts": datetime.now(timezone.utc).isoformat(),
                "tool": tool_name,
                "status": "exception",
                "duration_ms": duration_ms,
                "user_id": user_id,
                "error": str(e),
            })
            return _jsonrpc_error(req_id, -32603, str(e))

    # ── Sprint 9 Step 3: Resources + Prompts ────────────────────────────
    if method == "resources/list":
        return _jsonrpc_response(req_id, {
            "resources": [{
                "uri": "hubex://system-prompt",
                "name": "HubEx System Context",
                "description": "Background context about HubEx for AI assistants — concepts, workflows, and tool usage guide",
                "mimeType": "text/plain",
            }],
        })

    if method == "resources/read":
        uri = params.get("uri", "")
        if uri == "hubex://system-prompt":
            return _jsonrpc_response(req_id, {
                "contents": [{
                    "uri": "hubex://system-prompt",
                    "text": SYSTEM_PROMPT,
                    "mimeType": "text/plain",
                }],
            })
        return _jsonrpc_error(req_id, -32602, f"Unknown resource URI: {uri}")

    if method == "prompts/list":
        return _jsonrpc_response(req_id, {"prompts": PROMPT_TEMPLATES})

    if method == "prompts/get":
        prompt_name = params.get("name", "")
        prompt_args = params.get("arguments", {})
        known = {t["name"] for t in PROMPT_TEMPLATES}
        if prompt_name not in known:
            return _jsonrpc_error(req_id, -32602, f"Unknown prompt: {prompt_name}")
        messages = get_prompt_messages(prompt_name, prompt_args)
        return _jsonrpc_response(req_id, {"messages": messages})

    return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


# ── SSE Transport ────────────────────────────────────────────────────────


@router.get("/sse")
async def mcp_sse(
    request: Request,
    key: str | None = Query(None, description="API key for authentication"),
    db: AsyncSession = Depends(get_db),
):
    """MCP SSE transport endpoint.

    Clients connect here to establish a persistent SSE stream.  The server
    immediately sends an ``endpoint`` event containing the POST URL the
    client should use for JSON-RPC messages.  The connection is kept alive
    with periodic pings.  Tool-call results are streamed back as ``message``
    events.
    """
    user = await _resolve_user_for_sse(request, key, db)

    session_id = str(uuid.uuid4())
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    _sessions[session_id] = {
        "user_id": user.id,
        "user": user,
        "queue": queue,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("MCP SSE session started: %s (user %s)", session_id, user.id)

    async def event_stream():
        try:
            # Send the messages endpoint URL
            endpoint_url = f"/api/v1/mcp/messages?session_id={session_id}"
            yield f"event: endpoint\ndata: {endpoint_url}\n\n"

            while True:
                if await request.is_disconnected():
                    break

                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: message\ndata: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive ping
                    yield ": ping\n\n"
        finally:
            _sessions.pop(session_id, None)
            logger.info("MCP SSE session ended: %s", session_id)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/messages")
async def mcp_messages(
    request: Request,
    session_id: str = Query(..., description="SSE session ID"),
    db: AsyncSession = Depends(get_db),
):
    """Receive MCP JSON-RPC messages and push results to the SSE stream."""
    session = _sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Unknown session. Connect to /sse first.")

    body = await request.json()
    user: User = session["user"]

    response = await _handle_jsonrpc(body, db, user)

    # Push result to the SSE stream
    queue: asyncio.Queue = session["queue"]
    await queue.put(response)

    return response


# ── Status & Log endpoints ───────────────────────────────────────────────


@router.get("/status")
async def mcp_status(
    current_user: User = Depends(get_current_user),
):
    """Return MCP server status and active connection count."""
    return {
        "enabled": True,
        "active_connections": len(_sessions),
        "tools_count": len(get_tool_definitions()),
        "protocol_version": "2024-11-05",
    }


@router.get("/log")
async def mcp_access_log(
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
):
    """Return recent MCP tool-call access log entries."""
    return {"entries": _access_log[:limit], "total": len(_access_log)}


# ── Legacy JSON-RPC endpoints (unchanged) ────────────────────────────────


@router.post("/tools/list", response_model=ToolListResponse)
async def list_tools(
    current_user: User = Depends(get_current_user),
) -> ToolListResponse:
    """List all available MCP tools."""
    return ToolListResponse(tools=get_tool_definitions())


@router.post("/tools/call", response_model=ToolCallResponse)
async def call_tool(
    request: ToolCallRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ToolCallResponse:
    """Execute an MCP tool call."""
    tool_names = {t["name"] for t in get_tool_definitions()}
    if request.resolved_name not in tool_names:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{request.resolved_name}' not found. Available: {sorted(tool_names)}",
        )

    t0 = time.monotonic()
    try:
        result = await execute_tool(
            tool_name=request.resolved_name,
            arguments=request.arguments,
            db=db,
            user=current_user,
        )

        duration_ms = round((time.monotonic() - t0) * 1000)
        is_error = "error" in result
        _log_access({
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": request.resolved_name,
            "status": "error" if is_error else "ok",
            "duration_ms": duration_ms,
            "user_id": current_user.id,
        })
        # Sprint 3.4 bugfix: was using str(result) which produces Python
        # repr() output (single quotes, \xNN-escaped umlauts) instead of
        # valid JSON. MCP clients received "kryptische Zeichen" for alerts
        # with German text. Fixed to match the SSE transport which uses
        # json.dumps(result) with ensure_ascii=False so unicode passes
        # through as-is (ä not \u00e4).
        return ToolCallResponse(
            content=[{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
            isError=is_error,
        )
    except Exception as e:
        duration_ms = round((time.monotonic() - t0) * 1000)
        _log_access({
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": request.resolved_name,
            "status": "exception",
            "duration_ms": duration_ms,
            "user_id": current_user.id,
            "error": str(e),
        })
        return ToolCallResponse(
            content=[{"type": "text", "text": f"Error: {str(e)}"}],
            isError=True,
        )
