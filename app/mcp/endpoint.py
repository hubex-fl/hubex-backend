"""MCP HTTP Endpoint (M22 Step 2).

Exposes HUBEX tools via a JSON-RPC style MCP endpoint.
Supports tool listing and tool execution with JWT authentication.

Endpoints:
  POST /api/v1/mcp/tools/list    — list available tools
  POST /api/v1/mcp/tools/call    — execute a tool
"""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.db.models.user import User
from app.mcp.tools import get_tool_definitions
from app.mcp.handler import execute_tool

router = APIRouter(prefix="/mcp", tags=["mcp"])


# ── Request/Response schemas ──────────────────────────────────────────────


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = {}


class ToolCallResponse(BaseModel):
    content: list[dict[str, Any]]
    isError: bool = False


class ToolListResponse(BaseModel):
    tools: list[dict[str, Any]]


# ── Endpoints ─────────────────────────────────────────────────────────────


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
    # Validate tool exists
    tool_names = {t["name"] for t in get_tool_definitions()}
    if request.name not in tool_names:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{request.name}' not found. Available: {sorted(tool_names)}",
        )

    try:
        result = await execute_tool(
            tool_name=request.name,
            arguments=request.arguments,
            db=db,
            user_id=current_user.id,
        )

        is_error = "error" in result
        return ToolCallResponse(
            content=[{"type": "text", "text": str(result)}],
            isError=is_error,
        )
    except Exception as e:
        return ToolCallResponse(
            content=[{"type": "text", "text": f"Error: {str(e)}"}],
            isError=True,
        )
