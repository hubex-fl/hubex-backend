"""Custom API Builder — CRUD for user-defined REST endpoints."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.api.deps_org import get_current_org_id
from app.core.system_events import emit_system_event
from app.db.models.custom_endpoint import CustomEndpoint
from app.db.models.user import User

logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/custom-endpoints", tags=["Custom API"])


class EndpointCreateIn(BaseModel):
    name: str
    route_path: str
    method: str = "GET"
    description: str | None = None
    response_mapping: dict = {}
    params_schema: dict | None = None
    rate_limit_per_minute: int = 60
    required_scope: str | None = None


class EndpointUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    response_mapping: dict | None = None
    params_schema: dict | None = None
    rate_limit_per_minute: int | None = None
    required_scope: str | None = None
    enabled: bool | None = None


class EndpointOut(BaseModel):
    id: int
    name: str
    route_path: str
    method: str
    description: str | None
    response_mapping: dict
    params_schema: dict | None
    rate_limit_per_minute: int
    required_scope: str | None
    enabled: bool
    request_count: int
    last_called_at: str | None
    created_at: str


class EndpointTrafficOut(BaseModel):
    id: int
    name: str
    route_path: str
    request_count: int
    last_called_at: str | None
    rate_limit_per_minute: int


@router.get("", response_model=list[EndpointOut])
async def list_custom_endpoints(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CustomEndpoint).order_by(CustomEndpoint.created_at.desc())
    )
    endpoints = list(result.scalars().all())
    return [_to_out(ep) for ep in endpoints]


@router.post("", response_model=EndpointOut, status_code=201)
async def create_custom_endpoint(
    data: EndpointCreateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    org_id: int | None = Depends(get_current_org_id),
):
    if not data.name.strip():
        raise HTTPException(status_code=422, detail="name is required")
    if not data.route_path.strip().startswith("/"):
        raise HTTPException(status_code=422, detail="route_path must start with /")
    if data.method.upper() not in ("GET", "POST"):
        raise HTTPException(status_code=422, detail="method must be GET or POST")

    # Check uniqueness
    existing = await db.execute(
        select(CustomEndpoint).where(CustomEndpoint.route_path == data.route_path.strip())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"route {data.route_path} already exists")

    ep = CustomEndpoint(
        org_id=org_id,
        created_by=user.id,
        name=data.name.strip(),
        route_path=data.route_path.strip(),
        method=data.method.upper(),
        description=data.description,
        response_mapping=data.response_mapping,
        params_schema=data.params_schema,
        rate_limit_per_minute=data.rate_limit_per_minute,
        required_scope=data.required_scope,
    )
    db.add(ep)
    await emit_system_event(db, "custom_endpoint.created", {
        "user_id": user.id, "name": data.name, "route": data.route_path,
    })
    await db.commit()
    await db.refresh(ep)
    return _to_out(ep)


@router.get("/traffic", response_model=list[EndpointTrafficOut])
async def get_traffic(db: AsyncSession = Depends(get_db)):
    """API Traffic Dashboard — requests per endpoint."""
    result = await db.execute(
        select(CustomEndpoint)
        .where(CustomEndpoint.enabled == True)
        .order_by(CustomEndpoint.request_count.desc())
    )
    return [
        EndpointTrafficOut(
            id=ep.id, name=ep.name, route_path=ep.route_path,
            request_count=ep.request_count,
            last_called_at=ep.last_called_at.isoformat() if ep.last_called_at else None,
            rate_limit_per_minute=ep.rate_limit_per_minute,
        )
        for ep in result.scalars().all()
    ]


@router.patch("/{endpoint_id}", response_model=EndpointOut)
async def update_custom_endpoint(
    endpoint_id: int,
    data: EndpointUpdateIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ep = await db.get(CustomEndpoint, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="endpoint not found")

    if data.name is not None:
        ep.name = data.name
    if data.description is not None:
        ep.description = data.description
    if data.response_mapping is not None:
        ep.response_mapping = data.response_mapping
    if data.params_schema is not None:
        ep.params_schema = data.params_schema
    if data.rate_limit_per_minute is not None:
        ep.rate_limit_per_minute = data.rate_limit_per_minute
    if data.required_scope is not None:
        ep.required_scope = data.required_scope
    if data.enabled is not None:
        ep.enabled = data.enabled

    await db.commit()
    await db.refresh(ep)
    return _to_out(ep)


@router.delete("/{endpoint_id}", status_code=204)
async def delete_custom_endpoint(
    endpoint_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    ep = await db.get(CustomEndpoint, endpoint_id)
    if not ep:
        raise HTTPException(status_code=404, detail="endpoint not found")
    await db.delete(ep)
    await emit_system_event(db, "custom_endpoint.deleted", {
        "user_id": user.id, "name": ep.name, "route": ep.route_path,
    })
    await db.commit()


def _to_out(ep: CustomEndpoint) -> EndpointOut:
    return EndpointOut(
        id=ep.id, name=ep.name, route_path=ep.route_path,
        method=ep.method, description=ep.description,
        response_mapping=ep.response_mapping, params_schema=ep.params_schema,
        rate_limit_per_minute=ep.rate_limit_per_minute,
        required_scope=ep.required_scope, enabled=ep.enabled,
        request_count=ep.request_count,
        last_called_at=ep.last_called_at.isoformat() if ep.last_called_at else None,
        created_at=ep.created_at.isoformat(),
    )
