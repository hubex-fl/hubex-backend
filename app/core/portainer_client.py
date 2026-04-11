"""Portainer REST API client for plugin service orchestration.

Wraps the minimal Portainer endpoints HubEx needs to install / start / stop /
remove containers for Service Plugins (Sprint 3). HubEx never touches the
Docker socket directly — Portainer does. Authentication uses the admin JWT
from ``HUBEX_PORTAINER_USER`` / ``HUBEX_PORTAINER_PASS`` with an 8 h token
cache.

Every failure is raised as :class:`PortainerError` with a structured
``code`` / ``message`` pair so the plugin manager can surface consistent
errors to the UI.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("uvicorn.error")

_TOKEN_TTL_SECONDS = 8 * 60 * 60  # 8 h
_DEFAULT_TIMEOUT = 15.0
_DEFAULT_URL = "https://hubex-portainer:9443"
_DEFAULT_USER = "admin"


class PortainerError(Exception):
    """Structured error raised by the Portainer client."""

    def __init__(self, code: str, message: str, *, status: int | None = None) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.status = status


class PortainerClient:
    """Minimal async client for the Portainer REST API.

    Only the operations the HubEx plugin manager needs are implemented:
    login, endpoint discovery, and container create / start / stop / remove /
    inspect. The client is stateless except for a cached JWT (8 h TTL) and
    the auto-discovered Docker endpoint id.
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        endpoint_id: int | None = None,
        verify_tls: bool = False,
    ) -> None:
        self._base_url = (base_url or getattr(settings, "portainer_url", _DEFAULT_URL)).rstrip("/")
        self._username = username or getattr(settings, "portainer_user", _DEFAULT_USER)
        self._password = password or getattr(settings, "portainer_pass", "")
        self._endpoint_id = endpoint_id
        self._verify_tls = verify_tls
        self._token: str | None = None
        self._token_expires_at: float = 0.0
        # Sprint 4 — portainer 2.39+ uses gorilla CSRF tokens on non-GET
        # requests. After the first GET the server sends back both a
        # `_gorilla_csrf` cookie and an `X-Csrf-Token` header; subsequent
        # POST/PUT/DELETE requests must echo both. We cache them here so
        # multiple calls reuse the same anti-forgery pair without a
        # round-trip. The tuple is invalidated whenever the JWT expires.
        self._csrf_token: str | None = None
        self._csrf_cookie: str | None = None

    # ------------------------------------------------------------------
    # Auth & endpoint discovery
    # ------------------------------------------------------------------
    async def _login(self, client: httpx.AsyncClient) -> str:
        if not self._password:
            raise PortainerError(
                "PORTAINER_NOT_CONFIGURED",
                "HUBEX_PORTAINER_PASS is not set — cannot log in to Portainer.",
            )
        if self._token and time.time() < self._token_expires_at:
            return self._token
        try:
            resp = await client.post(
                f"{self._base_url}/api/auth",
                json={"username": self._username, "password": self._password},
                timeout=_DEFAULT_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise PortainerError(
                "PORTAINER_UNREACHABLE",
                f"Could not reach Portainer at {self._base_url}: {exc}",
            ) from exc
        if resp.status_code != 200:
            raise PortainerError(
                "PORTAINER_AUTH_FAILED",
                f"Portainer login failed (status={resp.status_code}).",
                status=resp.status_code,
            )
        token = (resp.json() or {}).get("jwt")
        if not token:
            raise PortainerError(
                "PORTAINER_AUTH_FAILED",
                "Portainer login response did not contain a jwt token.",
            )
        self._token = token
        self._token_expires_at = time.time() + _TOKEN_TTL_SECONDS
        # Fresh login invalidates any cached anti-forgery pair
        self._csrf_token = None
        self._csrf_cookie = None
        logger.info("portainer: authenticated, token cached for %ds", _TOKEN_TTL_SECONDS)
        return token

    async def _get_endpoint_id(
        self, client: httpx.AsyncClient, headers: dict[str, str]
    ) -> int:
        if self._endpoint_id is not None:
            return self._endpoint_id
        try:
            resp = await client.get(
                f"{self._base_url}/api/endpoints",
                headers=headers,
                timeout=_DEFAULT_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise PortainerError(
                "PORTAINER_UNREACHABLE",
                f"Could not fetch Portainer endpoints: {exc}",
            ) from exc
        if resp.status_code != 200:
            raise PortainerError(
                "PORTAINER_NO_ENDPOINTS",
                f"Failed to list Portainer endpoints (status={resp.status_code}).",
                status=resp.status_code,
            )
        endpoints = resp.json() or []
        if not isinstance(endpoints, list) or not endpoints:
            raise PortainerError(
                "PORTAINER_NO_ENDPOINTS",
                "Portainer has no configured Docker endpoints.",
            )
        self._endpoint_id = int(endpoints[0]["Id"])
        logger.info("portainer: discovered endpoint id=%d", self._endpoint_id)
        return self._endpoint_id

    async def _ensure_csrf(self, client: httpx.AsyncClient, token: str) -> None:
        """Prime the anti-forgery token/cookie pair used by portainer 2.39+.

        Issues a cheap GET (``/api/endpoints``) that portainer replies to
        with a ``_gorilla_csrf`` cookie and an ``X-Csrf-Token`` response
        header. We stash both on the instance so subsequent POST/PUT/DELETE
        calls can echo them; without them portainer returns 403 CSRF.
        Skipped if we already have a cached token (login invalidates it).
        """
        if self._csrf_token is not None and self._csrf_cookie is not None:
            return
        try:
            resp = await client.get(
                f"{self._base_url}/api/endpoints",
                headers={"Authorization": f"Bearer {token}"},
                timeout=_DEFAULT_TIMEOUT,
            )
        except httpx.RequestError as exc:
            raise PortainerError(
                "PORTAINER_UNREACHABLE",
                f"CSRF prime request failed: {exc}",
            ) from exc
        if resp.status_code != 200:
            raise PortainerError(
                "PORTAINER_CSRF_PRIME_FAILED",
                f"CSRF prime returned {resp.status_code}: {resp.text[:200]}",
                status=resp.status_code,
            )
        self._csrf_token = resp.headers.get("X-Csrf-Token") or ""
        # httpx.AsyncClient keeps cookies per-client; we extract the raw
        # _gorilla_csrf value and cache it for future ephemeral clients.
        for c in client.cookies.jar:
            if c.name == "_gorilla_csrf":
                self._csrf_cookie = c.value
                break

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(verify=self._verify_tls) as client:
            token = await self._login(client)
            await self._ensure_csrf(client, token)
            # Sprint 4 bugfix: Portainer 2.39+ has a three-part anti-CSRF
            # check on non-GET requests via bearer auth:
            #   1. Referer header must be present
            #   2. X-Csrf-Token header must carry the token the server
            #      issued on a prior GET
            #   3. The _gorilla_csrf cookie must be echoed back
            # Without all three, POST/PUT/DELETE return 403 even with a
            # valid JWT. This was also the root cause of the Sprint 3
            # fresh-spawn path being silently broken (we only ever adopted
            # pre-existing containers, never actually created one).
            headers = {
                "Authorization": f"Bearer {token}",
                "Referer": self._base_url + "/",
                "X-Csrf-Token": self._csrf_token or "",
            }
            if self._csrf_cookie:
                headers["Cookie"] = f"_gorilla_csrf={self._csrf_cookie}"
            endpoint_id = await self._get_endpoint_id(client, headers)
            url = f"{self._base_url}/api/endpoints/{endpoint_id}{path}"
            try:
                return await client.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    timeout=_DEFAULT_TIMEOUT,
                )
            except httpx.RequestError as exc:
                raise PortainerError(
                    "PORTAINER_UNREACHABLE",
                    f"Portainer request failed ({method} {path}): {exc}",
                ) from exc

    # ------------------------------------------------------------------
    # Manifest → Docker create body
    # ------------------------------------------------------------------
    @staticmethod
    def build_create_body(docker: dict[str, Any]) -> dict[str, Any]:
        """Translate a plugin manifest ``docker`` block into a Docker create body."""
        env_list: list[str] = []
        for entry in docker.get("env") or []:
            key = entry.get("key")
            if key:
                env_list.append(f"{key}={entry.get('value', '')}")

        exposed_ports: dict[str, dict[str, Any]] = {}
        port_bindings: dict[str, list[dict[str, str]]] = {}
        for p in docker.get("ports") or []:
            container_port = p.get("container")
            host_port = p.get("host")
            if container_port is None or host_port is None:
                continue
            key = f"{container_port}/tcp"
            exposed_ports[key] = {}
            port_bindings[key] = [{"HostPort": str(host_port)}]

        binds: list[str] = []
        for v in docker.get("volumes") or []:
            src, tgt = v.get("source"), v.get("target")
            if src and tgt:
                binds.append(f"{src}:{tgt}")

        return {
            "Image": docker["image"],
            "Env": env_list,
            "ExposedPorts": exposed_ports,
            "HostConfig": {
                "PortBindings": port_bindings,
                "Binds": binds,
                "RestartPolicy": {"Name": "unless-stopped"},
            },
        }

    # ------------------------------------------------------------------
    # Container operations
    # ------------------------------------------------------------------
    async def create_container(
        self, name: str, docker_manifest: dict[str, Any]
    ) -> dict[str, Any]:
        body = self.build_create_body(docker_manifest)
        resp = await self._request(
            "POST",
            "/docker/containers/create",
            params={"name": name},
            json_body=body,
        )
        if resp.status_code not in (200, 201):
            raise PortainerError(
                "PORTAINER_CREATE_FAILED",
                f"Failed to create container '{name}': {resp.text[:200]}",
                status=resp.status_code,
            )
        return resp.json() or {}

    async def start_container(self, name: str) -> None:
        resp = await self._request("POST", f"/docker/containers/{name}/start")
        if resp.status_code not in (204, 304):
            raise PortainerError(
                "PORTAINER_START_FAILED",
                f"Failed to start container '{name}': {resp.text[:200]}",
                status=resp.status_code,
            )

    async def stop_container(self, name: str) -> None:
        resp = await self._request("POST", f"/docker/containers/{name}/stop")
        if resp.status_code not in (204, 304):
            raise PortainerError(
                "PORTAINER_STOP_FAILED",
                f"Failed to stop container '{name}': {resp.text[:200]}",
                status=resp.status_code,
            )

    async def remove_container(self, name: str, *, force: bool = True) -> None:
        resp = await self._request(
            "DELETE",
            f"/docker/containers/{name}",
            params={"force": "true" if force else "false", "v": "false"},
        )
        if resp.status_code not in (204, 404):
            raise PortainerError(
                "PORTAINER_REMOVE_FAILED",
                f"Failed to remove container '{name}': {resp.text[:200]}",
                status=resp.status_code,
            )

    async def get_container_status(self, name: str) -> dict[str, Any] | None:
        """Inspect a container. Returns ``None`` if it does not exist."""
        resp = await self._request("GET", f"/docker/containers/{name}/json")
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise PortainerError(
                "PORTAINER_STATUS_FAILED",
                f"Failed to inspect container '{name}': {resp.text[:200]}",
                status=resp.status_code,
            )
        data = resp.json() or {}
        state = data.get("State") or {}
        health = state.get("Health") or {}
        return {
            "name": name,
            "id": data.get("Id"),
            "status": state.get("Status"),  # running|exited|created|...
            "running": bool(state.get("Running")),
            "exit_code": state.get("ExitCode"),
            "health": health.get("Status"),  # healthy|unhealthy|starting|None
            "started_at": state.get("StartedAt"),
        }

    async def container_exists(self, name: str) -> bool:
        return (await self.get_container_status(name)) is not None

    # ------------------------------------------------------------------
    # Sprint 4 additions — exec, archive read, and a wait-for-exit helper
    # so the firmware_builder sidecar pattern can: start container →
    # exec `pio run` → wait → fetch artifact as tar → remove.
    # ------------------------------------------------------------------

    async def container_logs(self, name: str, *, tail: int = 200) -> str:
        """Fetch stdout+stderr logs from a container. Returns the last
        ``tail`` lines as a single string. Docker's logs endpoint returns
        a multiplexed framed stream when TTY is false — we strip the 8-byte
        frame headers to get clean text.
        """
        resp = await self._request(
            "GET",
            f"/docker/containers/{name}/logs",
            params={"stdout": "true", "stderr": "true", "tail": str(tail), "timestamps": "false"},
        )
        if resp.status_code not in (200, 101):
            raise PortainerError(
                "PORTAINER_LOGS_FAILED",
                f"Failed to get logs for '{name}': {resp.text[:200]}",
                status=resp.status_code,
            )
        raw = resp.content
        # Strip docker multiplex frame headers (8 bytes per frame).
        # Frame layout: [stream_type:1, 0, 0, 0, size:4 big-endian]
        out: list[bytes] = []
        i = 0
        while i < len(raw):
            if len(raw) - i < 8:
                out.append(raw[i:])
                break
            # Heuristic: valid frame headers start with 0x00/0x01/0x02
            stream_type = raw[i]
            if stream_type not in (0, 1, 2):
                out.append(raw[i:])
                break
            size = int.from_bytes(raw[i + 4 : i + 8], "big")
            payload_start = i + 8
            payload_end = payload_start + size
            if payload_end > len(raw):
                out.append(raw[payload_start:])
                break
            out.append(raw[payload_start:payload_end])
            i = payload_end
        try:
            return b"".join(out).decode("utf-8", errors="replace")
        except Exception:
            return raw.decode("utf-8", errors="replace")

    async def put_container_archive(self, name: str, path: str, tar_bytes: bytes) -> None:
        """Upload a tar archive into a container, unpacking it at ``path``.

        The tar MUST use forward-slash paths relative to ``path``. Used by
        the firmware_builder to inject the generated PlatformIO project
        into an ephemeral build container.
        """
        async with httpx.AsyncClient(verify=self._verify_tls) as client:
            token = await self._login(client)
            await self._ensure_csrf(client, token)
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/x-tar",
                # Sprint 4 — referer + csrf token + gorilla cookie all needed
                "Referer": self._base_url + "/",
                "X-Csrf-Token": self._csrf_token or "",
            }
            if self._csrf_cookie:
                headers["Cookie"] = f"_gorilla_csrf={self._csrf_cookie}"
            endpoint_id = await self._get_endpoint_id(client, headers)
            url = (
                f"{self._base_url}/api/endpoints/{endpoint_id}"
                f"/docker/containers/{name}/archive"
            )
            try:
                resp = await client.put(
                    url,
                    params={"path": path, "noOverwriteDirNonDir": "false"},
                    headers=headers,
                    content=tar_bytes,
                    timeout=_DEFAULT_TIMEOUT * 4,  # uploads can be slower
                )
            except httpx.RequestError as exc:
                raise PortainerError(
                    "PORTAINER_UNREACHABLE",
                    f"Upload to '{name}' failed: {exc}",
                ) from exc
        if resp.status_code not in (200, 204):
            raise PortainerError(
                "PORTAINER_UPLOAD_FAILED",
                f"Failed to upload tar to '{name}:{path}': {resp.text[:200]}",
                status=resp.status_code,
            )

    async def get_container_archive(self, name: str, path: str) -> bytes:
        """Return the tar-stream of a file or directory inside a container.

        The caller is responsible for unpacking (single-file tars are easy
        with the stdlib ``tarfile`` module). Useful for retrieving build
        artifacts without mounting shared volumes.
        """
        resp = await self._request(
            "GET",
            f"/docker/containers/{name}/archive",
            params={"path": path},
        )
        if resp.status_code != 200:
            raise PortainerError(
                "PORTAINER_ARCHIVE_FAILED",
                f"Failed to archive '{path}' from '{name}': {resp.text[:200]}",
                status=resp.status_code,
            )
        return resp.content

    async def wait_for_container_exit(
        self,
        name: str,
        *,
        timeout_seconds: int = 300,
        poll_interval: float = 2.0,
    ) -> dict[str, Any]:
        """Poll ``get_container_status`` until the container exits or the
        timeout expires. Returns the final status dict. Raises
        :class:`PortainerError` on timeout.
        """
        import asyncio as _asyncio
        deadline = _asyncio.get_event_loop().time() + timeout_seconds
        while True:
            status = await self.get_container_status(name)
            if status is None:
                # Container vanished — treat as error
                raise PortainerError(
                    "PORTAINER_CONTAINER_GONE",
                    f"Container '{name}' disappeared while waiting for exit",
                )
            if not status["running"]:
                return status
            if _asyncio.get_event_loop().time() >= deadline:
                raise PortainerError(
                    "PORTAINER_WAIT_TIMEOUT",
                    f"Container '{name}' still running after {timeout_seconds}s",
                )
            await _asyncio.sleep(poll_interval)


# Module-level lazy singleton — reused across requests so the JWT cache works.
_client: PortainerClient | None = None


def get_portainer_client() -> PortainerClient:
    global _client
    if _client is None:
        _client = PortainerClient()
    return _client
