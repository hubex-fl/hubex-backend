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
            headers = {"Authorization": f"Bearer {token}"}
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


# Module-level lazy singleton — reused across requests so the JWT cache works.
_client: PortainerClient | None = None


def get_portainer_client() -> PortainerClient:
    global _client
    if _client is None:
        _client = PortainerClient()
    return _client
