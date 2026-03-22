"""Tests for Webhook CRUD, dispatcher retry logic, and signature verification."""
from __future__ import annotations

import hashlib
import hmac
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import Depends, FastAPI

from app.api.deps import get_db
from app.api.deps_caps import capability_guard
from app.api.v1.webhooks import router as webhooks_router
from app.core.capabilities import CAPABILITY_MAP
from app.db.models.webhooks import WebhookSubscription, WebhookDelivery
from tests.conftest import make_test_session, make_token


def _auth(caps: list[str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(caps=caps)}"}


async def _mk_app():
    _, Session = await make_test_session(
        tables=[WebhookSubscription.__table__, WebhookDelivery.__table__]
    )

    async def _get_test_db():
        async with Session() as s:
            yield s

    app = FastAPI(dependencies=[Depends(capability_guard)])
    app.dependency_overrides[get_db] = _get_test_db
    app.include_router(webhooks_router, prefix="/api/v1")
    return app


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_webhook(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/webhooks")] = ["webhooks.write"]

    app = await _mk_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks",
            json={"url": "http://example.com/hook", "secret": "mysecret", "event_filter": ["device.online"]},
            headers=_auth(["webhooks.write"]),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["url"] == "http://example.com/hook"
    assert data["event_filter"] == ["device.online"]
    assert data["active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_create_webhook_empty_filter(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/webhooks")] = ["webhooks.write"]

    app = await _mk_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/webhooks",
            json={"url": "http://example.com/hook2", "secret": "s"},
            headers=_auth(["webhooks.write"]),
        )
    assert resp.status_code == 201
    assert resp.json()["event_filter"] == []


@pytest.mark.asyncio
async def test_list_webhooks(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/webhooks")] = ["webhooks.write"]
    CAPABILITY_MAP[("GET", "/api/v1/webhooks")] = ["webhooks.read"]

    app = await _mk_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/webhooks",
            json={"url": "http://a.com", "secret": "s1"},
            headers=_auth(["webhooks.write"]),
        )
        await client.post(
            "/api/v1/webhooks",
            json={"url": "http://b.com", "secret": "s2"},
            headers=_auth(["webhooks.write"]),
        )
        resp = await client.get("/api/v1/webhooks", headers=_auth(["webhooks.read"]))

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    urls = {item["url"] for item in items}
    assert urls == {"http://a.com", "http://b.com"}


@pytest.mark.asyncio
async def test_get_webhook(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/webhooks")] = ["webhooks.write"]
    CAPABILITY_MAP[("GET", "/api/v1/webhooks/{webhook_id}")] = ["webhooks.read"]

    app = await _mk_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/webhooks",
            json={"url": "http://c.com", "secret": "s"},
            headers=_auth(["webhooks.write"]),
        )
        wid = create_resp.json()["id"]
        resp = await client.get(f"/api/v1/webhooks/{wid}", headers=_auth(["webhooks.read"]))

    assert resp.status_code == 200
    assert resp.json()["id"] == wid


@pytest.mark.asyncio
async def test_get_webhook_not_found(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("GET", "/api/v1/webhooks/{webhook_id}")] = ["webhooks.read"]

    app = await _mk_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/webhooks/9999", headers=_auth(["webhooks.read"]))

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_webhook(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("POST", "/api/v1/webhooks")] = ["webhooks.write"]
    CAPABILITY_MAP[("GET", "/api/v1/webhooks/{webhook_id}")] = ["webhooks.read"]
    CAPABILITY_MAP[("DELETE", "/api/v1/webhooks/{webhook_id}")] = ["webhooks.write"]

    app = await _mk_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/v1/webhooks",
            json={"url": "http://del.com", "secret": "s"},
            headers=_auth(["webhooks.write"]),
        )
        wid = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/v1/webhooks/{wid}", headers=_auth(["webhooks.write"]))
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/api/v1/webhooks/{wid}", headers=_auth(["webhooks.read"]))
        assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_webhook_not_found(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP[("DELETE", "/api/v1/webhooks/{webhook_id}")] = ["webhooks.write"]

    app = await _mk_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/api/v1/webhooks/9999", headers=_auth(["webhooks.write"]))

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Signature verification tests
# ---------------------------------------------------------------------------

def _verify_signature(secret: str, body: bytes, signature: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def test_signature_verification_correct():
    secret = "mysupersecret"
    body = b'{"event": "device.online", "data": {}}'
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert _verify_signature(secret, body, sig)


def test_signature_verification_wrong_secret():
    body = b'{"event": "device.online"}'
    sig = hmac.new(b"correct", body, hashlib.sha256).hexdigest()
    assert not _verify_signature("wrong", body, sig)


def test_signature_verification_tampered_body():
    secret = "mysecret"
    original = b'{"event": "device.online"}'
    sig = hmac.new(secret.encode(), original, hashlib.sha256).hexdigest()
    tampered = b'{"event": "device.offline"}'
    assert not _verify_signature(secret, tampered, sig)


# ---------------------------------------------------------------------------
# Dispatcher retry logic tests
# ---------------------------------------------------------------------------

def _make_fake_db(deliveries: list):
    """Return a callable (like AsyncSessionLocal) that yields a fake async db session."""
    db = AsyncMock()
    db.add = lambda obj: deliveries.append(obj)
    db.commit = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=db)


@pytest.mark.asyncio
async def test_dispatcher_succeeds_on_first_attempt():
    """Dispatcher records one delivery with success=True when HTTP 200."""
    from app.core.webhook_dispatcher import _dispatch_with_retry

    webhook = MagicMock()
    webhook.id = 1
    webhook.secret = "secret"
    webhook.url = "http://example.com/hook"

    event = MagicMock()
    event.id = 42
    event.type = "device.online"
    event.stream = "system"
    event.ts = None
    event.payload = {"device_uid": "dev-001"}

    deliveries = []

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.core.webhook_dispatcher.AsyncSessionLocal", _make_fake_db(deliveries)):
        await _dispatch_with_retry(webhook, event, mock_client)

    assert mock_client.post.call_count == 1
    assert len(deliveries) == 1
    assert deliveries[0].success is True
    assert deliveries[0].attempt == 1


@pytest.mark.asyncio
async def test_dispatcher_retries_on_failure():
    """Dispatcher tries 4 times total (initial + 3 retries) on persistent failure."""
    from app.core.webhook_dispatcher import _dispatch_with_retry

    webhook = MagicMock()
    webhook.id = 2
    webhook.secret = "secret"
    webhook.url = "http://example.com/hook"

    event = MagicMock()
    event.id = 99
    event.type = "task.failed"
    event.stream = "system"
    event.ts = None
    event.payload = {}

    deliveries = []
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("app.core.webhook_dispatcher.AsyncSessionLocal", _make_fake_db(deliveries)):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await _dispatch_with_retry(webhook, event, mock_client)

    # 4 total: 1 initial + 3 retries (delays: 1s, 5s, 25s)
    assert mock_client.post.call_count == 4
    assert len(deliveries) == 4
    assert all(not d.success for d in deliveries)
    assert [d.attempt for d in deliveries] == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_dispatcher_succeeds_on_second_attempt():
    """Dispatcher stops retrying after first success."""
    from app.core.webhook_dispatcher import _dispatch_with_retry

    webhook = MagicMock()
    webhook.id = 3
    webhook.secret = "secret"
    webhook.url = "http://example.com/hook"

    event = MagicMock()
    event.id = 77
    event.type = "telemetry.received"
    event.stream = "system"
    event.ts = None
    event.payload = {}

    deliveries = []
    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.status_code = 200 if call_count == 2 else 503
        return resp

    mock_client = AsyncMock()
    mock_client.post = mock_post

    with patch("app.core.webhook_dispatcher.AsyncSessionLocal", _make_fake_db(deliveries)):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await _dispatch_with_retry(webhook, event, mock_client)

    assert call_count == 2
    assert len(deliveries) == 2
    assert deliveries[0].success is False
    assert deliveries[1].success is True


# ---------------------------------------------------------------------------
# Dispatcher event filter tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dispatcher_skips_non_matching_filter():
    """Webhook with non-matching event_filter does not receive the event."""
    from app.core.webhook_dispatcher import _run_dispatch_cycle

    event = MagicMock()
    event.id = 10
    event.type = "device.offline"
    event.stream = "system"
    event.ts = None
    event.payload = {}

    webhook = MagicMock()
    webhook.id = 1
    webhook.secret = "s"
    webhook.url = "http://x.com"
    webhook.active = True
    webhook.event_filter = ["device.online"]  # does NOT match device.offline

    call_count = [0]

    async def fake_execute(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalars.return_value.all.return_value = [event]
        else:
            result.scalars.return_value.all.return_value = [webhook]
        return result

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    db.execute = fake_execute

    with patch("app.core.webhook_dispatcher.AsyncSessionLocal", return_value=db):
        with patch("app.core.webhook_dispatcher._dispatch_with_retry", new_callable=AsyncMock) as mock_dispatch:
            with patch("httpx.AsyncClient") as mock_hx:
                hx_instance = AsyncMock()
                mock_hx.return_value.__aenter__ = AsyncMock(return_value=hx_instance)
                mock_hx.return_value.__aexit__ = AsyncMock(return_value=False)
                await _run_dispatch_cycle(0)
            mock_dispatch.assert_not_called()


@pytest.mark.asyncio
async def test_dispatcher_matches_empty_filter():
    """Webhook with empty event_filter receives all events."""
    from app.core.webhook_dispatcher import _run_dispatch_cycle

    event = MagicMock()
    event.id = 20
    event.type = "variable.changed"
    event.stream = "system"
    event.ts = None
    event.payload = {}

    webhook = MagicMock()
    webhook.id = 2
    webhook.secret = "s"
    webhook.url = "http://y.com"
    webhook.active = True
    webhook.event_filter = []  # empty = receive all

    call_count = [0]

    async def fake_execute(stmt):
        call_count[0] += 1
        result = MagicMock()
        if call_count[0] == 1:
            result.scalars.return_value.all.return_value = [event]
        else:
            result.scalars.return_value.all.return_value = [webhook]
        return result

    db = AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    db.execute = fake_execute

    with patch("app.core.webhook_dispatcher.AsyncSessionLocal", return_value=db):
        with patch("app.core.webhook_dispatcher._dispatch_with_retry", new_callable=AsyncMock) as mock_dispatch:
            with patch("httpx.AsyncClient") as mock_hx:
                hx_instance = AsyncMock()
                mock_hx.return_value.__aenter__ = AsyncMock(return_value=hx_instance)
                mock_hx.return_value.__aexit__ = AsyncMock(return_value=False)
                await _run_dispatch_cycle(0)
            mock_dispatch.assert_called_once()
