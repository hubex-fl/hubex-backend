"""Tests for Phase 5: Multi-Tenancy — Org CRUD, Members, Tenant Isolation,
Plan Limits, Switch-Org, System Events, Capability enforcement."""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.deps_org import get_current_org_id
from app.api.v1.auth import router as auth_router
from app.api.v1.entities import router as entities_router
from app.api.v1.orgs import router as orgs_router
from app.core.capabilities import CAPABILITY_MAP
from app.core.security import create_access_token, decode_access_token
from app.db.base import Base
from app.db.models.entities import Entity
from app.db.models.events import EventV1
from app.db.models.orgs import Organization, OrganizationUser
from app.db.models.revoked_token import RevokedToken
from app.db.models.user import User
from app.core.capabilities import CAPABILITY_MAP, PUBLIC_WHITELIST
from tests.conftest import make_token

# ---------------------------------------------------------------------------
# Autouse fixture — populate capability map & enforce mode for this module
# ---------------------------------------------------------------------------

_ORG_CAP_MAP: dict[tuple[str, str], list[str]] = {
    ("POST", "/api/v1/auth/register"): ["core.auth.register"],
    ("POST", "/api/v1/auth/login"): ["core.auth.login"],
    ("POST", "/api/v1/auth/switch-org"): ["core.auth.login"],
    ("POST", "/api/v1/orgs"): ["org.write"],
    ("GET", "/api/v1/orgs"): ["org.read"],
    ("GET", "/api/v1/orgs/{org_id}"): ["org.read"],
    ("PUT", "/api/v1/orgs/{org_id}"): ["org.write"],
    ("DELETE", "/api/v1/orgs/{org_id}"): ["org.admin"],
    ("GET", "/api/v1/orgs/{org_id}/members"): ["org.members.read"],
    ("POST", "/api/v1/orgs/{org_id}/members"): ["org.members.write"],
    ("PUT", "/api/v1/orgs/{org_id}/members/{target_user_id}"): ["org.members.write"],
    ("DELETE", "/api/v1/orgs/{org_id}/members/{target_user_id}"): ["org.members.write"],
    ("GET", "/api/v1/entities"): ["entities.read"],
    ("POST", "/api/v1/entities"): ["entities.write"],
}


@pytest.fixture(autouse=True)
def _cap_map_setup(monkeypatch):
    """Ensure org capability entries exist and enforcement is on for each test."""
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP.update(_ORG_CAP_MAP)
    PUBLIC_WHITELIST.add(("POST", "/api/v1/auth/register"))


# ---------------------------------------------------------------------------
# Test infrastructure
# ---------------------------------------------------------------------------

def _create_tables(metadata, conn) -> None:
    metadata.create_all(
        conn,
        tables=[
            User.__table__,
            Organization.__table__,
            OrganizationUser.__table__,
            Entity.__table__,
            EventV1.__table__,
            RevokedToken.__table__,
        ],
    )


async def _mk_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: _create_tables(Base.metadata, c))
    Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, Session


async def _mk_app(Session, routers=None):
    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    for r in (routers or [orgs_router]):
        app.include_router(r, prefix="/api/v1")
    return app


def _auth(caps: list[str], sub: str = "1", org_id: int | None = None) -> dict:
    return {"Authorization": f"Bearer {make_token(sub=sub, caps=caps, org_id=org_id) if org_id else make_token(sub=sub, caps=caps)}"}


def _token_with_org(sub: str, caps: list[str], org_id: int) -> str:
    return create_access_token(sub, caps=caps, org_id=org_id)


async def _seed_user(Session, email: str = "u@test.com", user_id_hint: int | None = None) -> int:
    async with Session() as db:
        user = User(email=email, password_hash="x")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user.id


async def _seed_org(Session, name: str = "TestOrg", slug: str = "test-org") -> int:
    async with Session() as db:
        now = datetime.now(timezone.utc)
        org = Organization(
            name=name, slug=slug, plan="free",
            max_devices=10, max_users=3,
            created_at=now, updated_at=now,
        )
        db.add(org)
        await db.commit()
        await db.refresh(org)
        return org.id


async def _seed_membership(Session, org_id: int, user_id: int, role: str = "owner") -> None:
    async with Session() as db:
        now = datetime.now(timezone.utc)
        m = OrganizationUser(
            org_id=org_id, user_id=user_id,
            role=role, invited_at=now, joined_at=now,
        )
        db.add(m)
        await db.commit()


# ---------------------------------------------------------------------------
# Capability map coverage
# ---------------------------------------------------------------------------

def test_capability_map_has_org_entries():
    assert ("POST", "/api/v1/orgs") in CAPABILITY_MAP
    assert ("GET", "/api/v1/orgs") in CAPABILITY_MAP
    assert ("DELETE", "/api/v1/orgs/{org_id}") in CAPABILITY_MAP
    assert ("POST", "/api/v1/orgs/{org_id}/members") in CAPABILITY_MAP
    assert ("POST", "/api/v1/auth/switch-org") in CAPABILITY_MAP


# ---------------------------------------------------------------------------
# Org CRUD
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_org():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/orgs",
            json={"name": "Acme Corp", "slug": "acme-corp", "plan": "free"},
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.write'])}"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Corp"
    assert data["slug"] == "acme-corp"
    assert data["plan"] == "free"
    assert data["max_devices"] == 10
    assert data["max_users"] == 3

    # Verify membership was created
    async with Session() as db:
        res = await db.execute(select(OrganizationUser))
        memberships = list(res.scalars().all())
    assert len(memberships) == 1
    assert memberships[0].role == "owner"
    assert memberships[0].user_id == user_id


@pytest.mark.asyncio
async def test_create_org_duplicate_slug_returns_409():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    await _seed_org(Session, slug="taken")
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/orgs",
            json={"name": "X", "slug": "taken"},
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.write'])}"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_org_invalid_slug_returns_422():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/orgs",
            json={"name": "X", "slug": "UPPER_CASE"},
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.write'])}"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_my_orgs():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    org1 = await _seed_org(Session, slug="org-1")
    org2 = await _seed_org(Session, slug="org-2")
    other_org = await _seed_org(Session, slug="other")

    await _seed_membership(Session, org1, user_id, "owner")
    await _seed_membership(Session, org2, user_id, "member")
    # other_org has no membership for this user

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get(
            "/api/v1/orgs",
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.read'])}"},
        )

    assert resp.status_code == 200
    slugs = {o["slug"] for o in resp.json()}
    assert slugs == {"org-1", "org-2"}
    assert "other" not in slugs


@pytest.mark.asyncio
async def test_get_org_requires_membership():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    org_id = await _seed_org(Session)
    # No membership for this user

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get(
            f"/api/v1/orgs/{org_id}",
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.read'])}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_org_member_can_access():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, user_id, "viewer")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get(
            f"/api/v1/orgs/{org_id}",
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.read'])}"},
        )
    assert resp.status_code == 200
    assert resp.json()["id"] == org_id


@pytest.mark.asyncio
async def test_update_org_requires_admin():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, user_id, "viewer")  # not admin

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.put(
            f"/api/v1/orgs/{org_id}",
            json={"name": "Changed"},
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.write'])}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_org_owner_can_update():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    org_id = await _seed_org(Session, name="Original")
    await _seed_membership(Session, org_id, user_id, "owner")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.put(
            f"/api/v1/orgs/{org_id}",
            json={"name": "Updated"},
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.write'])}"},
        )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_update_org_plan_updates_limits():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, user_id, "owner")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.put(
            f"/api/v1/orgs/{org_id}",
            json={"plan": "pro"},
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.write'])}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["plan"] == "pro"
    assert data["max_devices"] == 100
    assert data["max_users"] == 20


@pytest.mark.asyncio
async def test_delete_org_requires_owner():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    admin_id = await _seed_user(Session, "admin@test.com")
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, owner_id, "owner")
    await _seed_membership(Session, org_id, admin_id, "admin")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.delete(
            f"/api/v1/orgs/{org_id}",
            headers={"Authorization": f"Bearer {make_token(sub=str(admin_id), caps=['org.admin'])}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_org_owner_can_delete():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, user_id, "owner")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        del_resp = await c.delete(
            f"/api/v1/orgs/{org_id}",
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.admin'])}"},
        )
        get_resp = await c.get(
            f"/api/v1/orgs/{org_id}",
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.read'])}"},
        )
    assert del_resp.status_code == 204
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Member management
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_members():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    member_id = await _seed_user(Session, "member@test.com")
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, owner_id, "owner")
    await _seed_membership(Session, org_id, member_id, "member")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.get(
            f"/api/v1/orgs/{org_id}/members",
            headers={"Authorization": f"Bearer {make_token(sub=str(owner_id), caps=['org.members.read'])}"},
        )
    assert resp.status_code == 200
    emails = {m["email"] for m in resp.json()}
    assert emails == {"owner@test.com", "member@test.com"}


@pytest.mark.asyncio
async def test_invite_member():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    invitee_id = await _seed_user(Session, "invitee@test.com")
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, owner_id, "owner")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "invitee@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {make_token(sub=str(owner_id), caps=['org.members.write'])}"},
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "invitee@test.com"
    assert data["role"] == "member"


@pytest.mark.asyncio
async def test_invite_member_user_not_found():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, owner_id, "owner")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "ghost@nowhere.com", "role": "member"},
            headers={"Authorization": f"Bearer {make_token(sub=str(owner_id), caps=['org.members.write'])}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invite_duplicate_member_returns_409():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    member_id = await _seed_user(Session, "member@test.com")
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, owner_id, "owner")
    await _seed_membership(Session, org_id, member_id, "member")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "member@test.com", "role": "viewer"},
            headers={"Authorization": f"Bearer {make_token(sub=str(owner_id), caps=['org.members.write'])}"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_member_role():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    member_id = await _seed_user(Session, "member@test.com")
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, owner_id, "owner")
    await _seed_membership(Session, org_id, member_id, "member")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.put(
            f"/api/v1/orgs/{org_id}/members/{member_id}",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {make_token(sub=str(owner_id), caps=['org.members.write'])}"},
        )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_remove_member():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    member_id = await _seed_user(Session, "member@test.com")
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, owner_id, "owner")
    await _seed_membership(Session, org_id, member_id, "member")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        del_resp = await c.delete(
            f"/api/v1/orgs/{org_id}/members/{member_id}",
            headers={"Authorization": f"Bearer {make_token(sub=str(owner_id), caps=['org.members.write'])}"},
        )
    assert del_resp.status_code == 204

    async with Session() as db:
        res = await db.execute(
            select(OrganizationUser).where(
                OrganizationUser.org_id == org_id,
                OrganizationUser.user_id == member_id,
            )
        )
        assert res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_cannot_remove_owner():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, owner_id, "owner")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.delete(
            f"/api/v1/orgs/{org_id}/members/{owner_id}",
            headers={"Authorization": f"Bearer {make_token(sub=str(owner_id), caps=['org.members.write'])}"},
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Plan limits
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_limit_enforced_on_invite():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    # Create 3 more users to fill the free plan (max_users=3)
    u2 = await _seed_user(Session, "u2@test.com")
    u3 = await _seed_user(Session, "u3@test.com")
    u4 = await _seed_user(Session, "u4@test.com")  # will hit the limit
    org_id = await _seed_org(Session, slug="full-org")

    # Set max_users=2 to make it easier to test
    async with Session() as db:
        org = await db.get(Organization, org_id)
        org.max_users = 2
        await db.commit()

    await _seed_membership(Session, org_id, owner_id, "owner")
    await _seed_membership(Session, org_id, u2, "member")
    # Now at 2/2 limit

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "u3@test.com", "role": "viewer"},
            headers={"Authorization": f"Bearer {make_token(sub=str(owner_id), caps=['org.members.write'])}"},
        )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "PLAN_LIMIT_USERS"


@pytest.mark.asyncio
async def test_enterprise_plan_has_no_user_limit():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    u2 = await _seed_user(Session, "u2@test.com")
    org_id = await _seed_org(Session, slug="big-org")

    # Enterprise: max_users=0 means unlimited
    async with Session() as db:
        org = await db.get(Organization, org_id)
        org.plan = "enterprise"
        org.max_users = 0
        await db.commit()

    await _seed_membership(Session, org_id, owner_id, "owner")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "u2@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {make_token(sub=str(owner_id), caps=['org.members.write'])}"},
        )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_isolation_entities():
    """User with org_id=1 in JWT should NOT see entities from org_id=2."""
    _, Session = await _mk_session()
    org1_id = await _seed_org(Session, slug="org-alpha")
    org2_id = await _seed_org(Session, slug="org-beta")

    # Seed entities for each org
    async with Session() as db:
        now = datetime.now(timezone.utc)
        db.add(Entity(entity_id="alpha-1", type="sensor", org_id=org1_id, created_at=now))
        db.add(Entity(entity_id="beta-1", type="sensor", org_id=org2_id, created_at=now))
        await db.commit()

    app = await _mk_app(Session, routers=[entities_router])

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        # Token for org1 — should only see alpha-1
        token_org1 = make_token(caps=["entities.read"], org_id=org1_id)
        resp1 = await c.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token_org1}"},
        )
        # Token without org_id — should see all
        token_no_org = make_token(caps=["entities.read"])
        resp_all = await c.get(
            "/api/v1/entities",
            headers={"Authorization": f"Bearer {token_no_org}"},
        )

    assert resp1.status_code == 200
    assert {e["entity_id"] for e in resp1.json()} == {"alpha-1"}

    assert resp_all.status_code == 200
    assert {e["entity_id"] for e in resp_all.json()} == {"alpha-1", "beta-1"}


@pytest.mark.asyncio
async def test_tenant_isolation_create_entity_sets_org_id():
    """Creating entity with org_id in JWT sets the entity's org_id."""
    _, Session = await _mk_session()
    org_id = await _seed_org(Session)

    app = await _mk_app(Session, routers=[entities_router])
    token = make_token(caps=["entities.write", "entities.read"], org_id=org_id)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        create_resp = await c.post(
            "/api/v1/entities",
            json={"entity_id": "my-entity", "type": "sensor"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert create_resp.status_code == 201

    async with Session() as db:
        res = await db.execute(select(Entity).where(Entity.entity_id == "my-entity"))
        entity = res.scalar_one()
    assert entity.org_id == org_id


# ---------------------------------------------------------------------------
# Switch-org and JWT org_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_switch_org_returns_token_with_org_id():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, user_id, "member")

    app = await _mk_app(Session, routers=[auth_router])
    token = make_token(sub=str(user_id), caps=["core.auth.login"])

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/auth/switch-org",
            json={"org_id": org_id},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    new_token = resp.json()["access_token"]
    payload = decode_access_token(new_token)
    assert payload["org_id"] == org_id
    assert payload["sub"] == str(user_id)


@pytest.mark.asyncio
async def test_switch_org_non_member_returns_403():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    org_id = await _seed_org(Session)
    # No membership

    app = await _mk_app(Session, routers=[auth_router])
    token = make_token(sub=str(user_id), caps=["core.auth.login"])

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/auth/switch-org",
            json={"org_id": org_id},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Default org on registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_creates_default_org():
    _, Session = await _mk_session()
    app = await _mk_app(Session, routers=[auth_router])

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        resp = await c.post(
            "/api/v1/auth/register",
            json={"email": "new@test.com", "password": "pass123"},
        )

    assert resp.status_code == 200
    token = resp.json()["access_token"]
    payload = decode_access_token(token)

    # org_id should be set in the token
    assert "org_id" in payload
    org_id = payload["org_id"]

    # Verify org + membership exist in DB
    async with Session() as db:
        org = await db.get(Organization, org_id)
        assert org is not None
        assert org.plan == "free"

        res = await db.execute(
            select(OrganizationUser).where(OrganizationUser.org_id == org_id)
        )
        membership = res.scalar_one()
        assert membership.role == "owner"


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409():
    _, Session = await _mk_session()
    app = await _mk_app(Session, routers=[auth_router])

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        await c.post(
            "/api/v1/auth/register",
            json={"email": "dup@test.com", "password": "p"},
        )
        resp = await c.post(
            "/api/v1/auth/register",
            json={"email": "dup@test.com", "password": "p"},
        )
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# System events for org mutations
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_org_emits_system_event():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    app = await _mk_app(Session)

    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        await c.post(
            "/api/v1/orgs",
            json={"name": "EventOrg", "slug": "event-org"},
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.write'])}"},
        )

    async with Session() as db:
        res = await db.execute(select(EventV1).where(EventV1.type == "org.created"))
        events = list(res.scalars().all())

    assert len(events) == 1
    assert events[0].payload["slug"] == "event-org"


@pytest.mark.asyncio
async def test_invite_member_emits_system_event():
    _, Session = await _mk_session()
    owner_id = await _seed_user(Session, "owner@test.com")
    invitee_id = await _seed_user(Session, "invited@test.com")
    org_id = await _seed_org(Session)
    await _seed_membership(Session, org_id, owner_id, "owner")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        await c.post(
            f"/api/v1/orgs/{org_id}/members",
            json={"email": "invited@test.com", "role": "member"},
            headers={"Authorization": f"Bearer {make_token(sub=str(owner_id), caps=['org.members.write'])}"},
        )

    async with Session() as db:
        res = await db.execute(select(EventV1).where(EventV1.type == "org.member.invited"))
        events = list(res.scalars().all())

    assert len(events) == 1
    assert events[0].payload["invited_user_id"] == invitee_id


@pytest.mark.asyncio
async def test_delete_org_emits_system_event():
    _, Session = await _mk_session()
    user_id = await _seed_user(Session)
    org_id = await _seed_org(Session, slug="to-delete")
    await _seed_membership(Session, org_id, user_id, "owner")

    app = await _mk_app(Session)
    async with httpx.AsyncClient(app=app, base_url="http://test") as c:
        await c.delete(
            f"/api/v1/orgs/{org_id}",
            headers={"Authorization": f"Bearer {make_token(sub=str(user_id), caps=['org.admin'])}"},
        )

    async with Session() as db:
        res = await db.execute(select(EventV1).where(EventV1.type == "org.deleted"))
        events = list(res.scalars().all())

    assert len(events) == 1
    assert events[0].payload["slug"] == "to-delete"


# ---------------------------------------------------------------------------
# JWT org_id encoding
# ---------------------------------------------------------------------------

def test_create_access_token_includes_org_id():
    from app.core.security import create_access_token, decode_access_token
    token = create_access_token("42", caps=["org.read"], org_id=99)
    payload = decode_access_token(token)
    assert payload["org_id"] == 99
    assert payload["sub"] == "42"


def test_create_access_token_without_org_id_has_no_org_id_claim():
    from app.core.security import create_access_token, decode_access_token
    token = create_access_token("1", caps=["org.read"])
    payload = decode_access_token(token)
    assert "org_id" not in payload


def test_make_token_with_org_id_extra_claim():
    token = make_token(sub="5", caps=["org.read"], org_id=7)
    from app.core.security import decode_access_token
    payload = decode_access_token(token)
    assert payload["org_id"] == 7
