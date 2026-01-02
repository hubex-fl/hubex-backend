import os

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps_caps import capability_guard
from app.core.capabilities import CAPABILITY_MAP, PUBLIC_WHITELIST
from app.core.security import create_access_token


def _make_app():
    app = FastAPI(dependencies=[Depends(capability_guard)])

    @app.get("/public")
    def public():
        return {"ok": True}

    @app.get("/protected")
    def protected():
        return {"ok": True}

    @app.get("/unmapped")
    def unmapped():
        return {"ok": True}

    return app


def test_whitelist_allows_without_token(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP.clear()
    CAPABILITY_MAP.update(
        {
            ("GET", "/public"): ["core.public"],
            ("GET", "/protected"): ["vars.read"],
        }
    )
    PUBLIC_WHITELIST.clear()
    PUBLIC_WHITELIST.add(("GET", "/public"))

    app = _make_app()
    client = TestClient(app)

    res = client.get("/public")
    assert res.status_code == 200


def test_protected_requires_token_and_caps(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "1")
    CAPABILITY_MAP.clear()
    CAPABILITY_MAP.update(
        {
            ("GET", "/public"): ["core.public"],
            ("GET", "/protected"): ["vars.read"],
        }
    )
    PUBLIC_WHITELIST.clear()
    PUBLIC_WHITELIST.add(("GET", "/public"))

    app = _make_app()
    client = TestClient(app)

    res = client.get("/protected")
    assert res.status_code == 401

    token = create_access_token("1", caps=["vars.read"])
    res = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200

    token = create_access_token("1", caps=["vars.ack"])
    res = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403


def test_enforce_off_allows_unmapped(monkeypatch):
    monkeypatch.setenv("HUBEX_CAPS_ENFORCE", "0")
    CAPABILITY_MAP.clear()
    CAPABILITY_MAP.update({("GET", "/public"): ["core.public"]})
    PUBLIC_WHITELIST.clear()

    app = _make_app()
    client = TestClient(app)

    res = client.get("/unmapped")
    assert res.status_code == 200
