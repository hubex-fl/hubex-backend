"""Organization management & members API."""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.deps_org import get_jwt_user_id
from app.core.system_events import emit_system_event
from app.db.models.device import Device
from app.db.models.orgs import Organization, OrganizationUser, VALID_PLANS, VALID_ROLES
from app.db.models.user import User

router = APIRouter(prefix="/orgs", tags=["orgs"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,62}$")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class OrgOut(BaseModel):
    id: int
    name: str
    slug: str
    plan: str
    max_devices: int
    max_users: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrgCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    slug: str = Field(min_length=1, max_length=64)
    plan: str = "free"

    model_config = ConfigDict(extra="ignore")


class OrgUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    plan: str | None = None

    model_config = ConfigDict(extra="ignore")


class OrgMemberOut(BaseModel):
    user_id: int
    email: str
    role: str
    invited_at: datetime
    joined_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class MemberInviteIn(BaseModel):
    email: str
    role: str = "member"

    model_config = ConfigDict(extra="ignore")


class MemberRoleUpdateIn(BaseModel):
    role: str

    model_config = ConfigDict(extra="ignore")


# ---------------------------------------------------------------------------
# Plan-limit helpers
# ---------------------------------------------------------------------------

async def check_user_limit(db: AsyncSession, org: Organization) -> None:
    """Raise 403 if org user limit is reached. 0 = unlimited."""
    if org.max_users == 0:
        return
    count = (
        await db.execute(
            select(func.count())
            .select_from(OrganizationUser)
            .where(OrganizationUser.org_id == org.id)
        )
    ).scalar_one()
    if count >= org.max_users:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PLAN_LIMIT_USERS",
                "message": f"Organization user limit ({org.max_users}) reached",
            },
        )


async def check_device_limit(db: AsyncSession, org: Organization) -> None:
    """Raise 403 if org device limit is reached. 0 = unlimited."""
    if org.max_devices == 0:
        return
    count = (
        await db.execute(
            select(func.count())
            .select_from(Device)
            .where(Device.org_id == org.id)
        )
    ).scalar_one()
    if count >= org.max_devices:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PLAN_LIMIT_DEVICES",
                "message": f"Organization device limit ({org.max_devices}) reached",
            },
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _get_org_or_404(org_id: int, db: AsyncSession) -> Organization:
    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return org


async def _get_org_by_slug_or_404(slug: str, db: AsyncSession) -> Organization:
    res = await db.execute(select(Organization).where(Organization.slug == slug))
    org = res.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="organization not found")
    return org


async def _get_membership_or_403(
    org_id: int, user_id: int, db: AsyncSession
) -> OrganizationUser:
    res = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.org_id == org_id,
            OrganizationUser.user_id == user_id,
        )
    )
    membership = res.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=403, detail="not a member of this organization")
    return membership


async def _require_admin(org_id: int, user_id: int, db: AsyncSession) -> OrganizationUser:
    membership = await _get_membership_or_403(org_id, user_id, db)
    if membership.role not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="admin role required")
    return membership


async def _require_owner(org_id: int, user_id: int, db: AsyncSession) -> OrganizationUser:
    membership = await _get_membership_or_403(org_id, user_id, db)
    if membership.role != "owner":
        raise HTTPException(status_code=403, detail="owner role required")
    return membership


def _require_auth(user_id: int | None) -> int:
    if user_id is None:
        raise HTTPException(status_code=401, detail="authentication required")
    return user_id


# ---------------------------------------------------------------------------
# Org CRUD
# ---------------------------------------------------------------------------

@router.post("", response_model=OrgOut, status_code=201)
async def create_org(
    data: OrgCreateIn,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    uid = _require_auth(user_id)

    if not _SLUG_RE.match(data.slug):
        raise HTTPException(status_code=422, detail="invalid slug (lowercase alphanumeric + hyphens)")
    if data.plan not in VALID_PLANS:
        raise HTTPException(status_code=422, detail=f"unknown plan '{data.plan}'")

    existing = await db.execute(select(Organization).where(Organization.slug == data.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="slug already taken")

    from app.db.models.orgs import PLAN_DEFAULTS
    limits = PLAN_DEFAULTS[data.plan]
    now = datetime.now(timezone.utc)

    org = Organization(
        name=data.name,
        slug=data.slug,
        plan=data.plan,
        max_devices=limits["max_devices"],
        max_users=limits["max_users"],
        created_at=now,
        updated_at=now,
    )
    db.add(org)
    await db.flush()

    membership = OrganizationUser(
        org_id=org.id,
        user_id=uid,
        role="owner",
        invited_at=now,
        joined_at=now,
    )
    db.add(membership)
    await emit_system_event(db, "org.created", {"org_id": org.id, "slug": org.slug, "creator_user_id": uid})
    await db.commit()
    await db.refresh(org)
    return org


@router.get("", response_model=list[OrgOut])
async def list_my_orgs(
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    uid = _require_auth(user_id)
    res = await db.execute(
        select(Organization)
        .join(OrganizationUser, OrganizationUser.org_id == Organization.id)
        .where(OrganizationUser.user_id == uid)
        .order_by(Organization.id)
    )
    return list(res.scalars().all())


@router.get("/{org_id}", response_model=OrgOut)
async def get_org(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    uid = _require_auth(user_id)
    org = await _get_org_or_404(org_id, db)
    await _get_membership_or_403(org_id, uid, db)
    return org


@router.put("/{org_id}", response_model=OrgOut)
async def update_org(
    org_id: int,
    data: OrgUpdateIn,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    uid = _require_auth(user_id)
    org = await _get_org_or_404(org_id, db)
    await _require_admin(org_id, uid, db)

    if data.plan is not None and data.plan not in VALID_PLANS:
        raise HTTPException(status_code=422, detail=f"unknown plan '{data.plan}'")

    if data.name is not None:
        org.name = data.name
    if data.plan is not None:
        from app.db.models.orgs import PLAN_DEFAULTS
        org.plan = data.plan
        limits = PLAN_DEFAULTS[data.plan]
        org.max_devices = limits["max_devices"]
        org.max_users = limits["max_users"]

    org.updated_at = datetime.now(timezone.utc)
    await emit_system_event(db, "org.updated", {"org_id": org_id})
    await db.commit()
    await db.refresh(org)
    return org


@router.delete("/{org_id}", status_code=204)
async def delete_org(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    uid = _require_auth(user_id)
    org = await _get_org_or_404(org_id, db)
    await _require_owner(org_id, uid, db)
    await emit_system_event(db, "org.deleted", {"org_id": org_id, "slug": org.slug})
    await db.delete(org)
    await db.commit()


# ---------------------------------------------------------------------------
# Members API
# ---------------------------------------------------------------------------

@router.get("/{org_id}/members", response_model=list[OrgMemberOut])
async def list_members(
    org_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    uid = _require_auth(user_id)
    await _get_org_or_404(org_id, db)
    await _get_membership_or_403(org_id, uid, db)

    res = await db.execute(
        select(OrganizationUser, User.email)
        .join(User, User.id == OrganizationUser.user_id)
        .where(OrganizationUser.org_id == org_id)
        .order_by(OrganizationUser.invited_at)
    )
    rows = res.all()
    return [
        OrgMemberOut(
            user_id=ou.user_id,
            email=email,
            role=ou.role,
            invited_at=ou.invited_at,
            joined_at=ou.joined_at,
        )
        for ou, email in rows
    ]


@router.post("/{org_id}/members", response_model=OrgMemberOut, status_code=201)
async def invite_member(
    org_id: int,
    data: MemberInviteIn,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    uid = _require_auth(user_id)
    org = await _get_org_or_404(org_id, db)
    await _require_admin(org_id, uid, db)

    if data.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"unknown role '{data.role}'")
    if data.role == "owner":
        raise HTTPException(status_code=422, detail="cannot invite as owner; use role change")

    # Check plan user limit
    await check_user_limit(db, org)

    # Find user by email
    res = await db.execute(select(User).where(User.email == data.email))
    target_user = res.scalar_one_or_none()
    if target_user is None:
        raise HTTPException(status_code=404, detail=f"user '{data.email}' not found")

    # Check not already a member
    existing = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.org_id == org_id,
            OrganizationUser.user_id == target_user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="user is already a member")

    now = datetime.now(timezone.utc)
    membership = OrganizationUser(
        org_id=org_id,
        user_id=target_user.id,
        role=data.role,
        invited_at=now,
        joined_at=now,
    )
    db.add(membership)
    await emit_system_event(db, "org.member.invited", {
        "org_id": org_id,
        "invited_user_id": target_user.id,
        "role": data.role,
        "invited_by": uid,
    })
    await db.commit()
    await db.refresh(membership)
    return OrgMemberOut(
        user_id=target_user.id,
        email=target_user.email,
        role=membership.role,
        invited_at=membership.invited_at,
        joined_at=membership.joined_at,
    )


@router.put("/{org_id}/members/{target_user_id}", response_model=OrgMemberOut)
async def update_member_role(
    org_id: int,
    target_user_id: int,
    data: MemberRoleUpdateIn,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    uid = _require_auth(user_id)
    await _get_org_or_404(org_id, db)
    await _require_admin(org_id, uid, db)

    if data.role not in VALID_ROLES:
        raise HTTPException(status_code=422, detail=f"unknown role '{data.role}'")

    res = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.org_id == org_id,
            OrganizationUser.user_id == target_user_id,
        )
    )
    membership = res.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="member not found")

    old_role = membership.role
    membership.role = data.role
    await emit_system_event(db, "org.member.role_changed", {
        "org_id": org_id,
        "user_id": target_user_id,
        "old_role": old_role,
        "new_role": data.role,
        "changed_by": uid,
    })
    await db.commit()
    await db.refresh(membership)

    res_user = await db.execute(select(User).where(User.id == target_user_id))
    user_row = res_user.scalar_one()
    return OrgMemberOut(
        user_id=target_user_id,
        email=user_row.email,
        role=membership.role,
        invited_at=membership.invited_at,
        joined_at=membership.joined_at,
    )


@router.delete("/{org_id}/members/{target_user_id}", status_code=204)
async def remove_member(
    org_id: int,
    target_user_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int | None = Depends(get_jwt_user_id),
):
    uid = _require_auth(user_id)
    await _get_org_or_404(org_id, db)

    # Admin required, or user removing themselves
    if uid != target_user_id:
        await _require_admin(org_id, uid, db)

    res = await db.execute(
        select(OrganizationUser).where(
            OrganizationUser.org_id == org_id,
            OrganizationUser.user_id == target_user_id,
        )
    )
    membership = res.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="member not found")

    if membership.role == "owner":
        raise HTTPException(status_code=403, detail="cannot remove the owner")

    await db.delete(membership)
    await emit_system_event(db, "org.member.removed", {
        "org_id": org_id,
        "removed_user_id": target_user_id,
        "removed_by": uid,
    })
    await db.commit()
