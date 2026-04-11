"""Server-side firmware builder (Sprint 4 — firmware_builder feature).

Architecture
------------

Each build request kicks off an **ephemeral Portainer-managed sidecar
container** that:

    1. Receives the generated PlatformIO project as a tar archive uploaded
       through ``put_container_archive`` (shared-volume-free, works on any
       docker host reachable by Portainer).
    2. Runs ``pip install platformio && cd /workspace && pio run`` as the
       container command, which exits with the build status.
    3. On success, the built ``.bin`` is read back out via
       ``get_container_archive`` on ``/workspace/.pio/build/<env>/firmware.bin``.
    4. The container is removed. State lives only in the
       ``firmware_builds`` table.

The build job itself is an ``asyncio.Task`` launched in-process on the
FastAPI backend — no external worker queue needed for v1. The API
endpoints are fire-and-forget: POST returns a job id immediately, clients
poll GET for status/logs/artifact. This keeps the surface area tiny and
works in a single-backend-container deployment.

Why no shared volume?
^^^^^^^^^^^^^^^^^^^^^

Portainer's container archive APIs (PUT + GET) stream tar over HTTP.
That means the backend never needs to see the build volume on its own
filesystem. Zero deployment work: the ``orchestrator`` feature (added in
Sprint 3) already wires the backend to Portainer.

Why python image instead of a PlatformIO-branded one?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Image size + reuse. ``python:3.11-slim`` is ~120 MB and likely already
cached because the HubEx backend itself runs on it. ``pip install
platformio`` adds ~400 MB of platform SDKs on first run (cached in a
named volume once the sprint has a chance to optimise). Trading first-
build latency for deploy simplicity.

Status state machine
^^^^^^^^^^^^^^^^^^^^

    queued   → set on INSERT, sidecar not yet created
    building → container created + started, pio run underway
    success  → container exited 0, artifact fetched
    failed   → any error (compile, portainer, artifact missing)
    cancelled → user hit cancel before completion
"""
from __future__ import annotations

import asyncio
import io
import logging
import re
import secrets
import tarfile
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.portainer_client import PortainerError, get_portainer_client
from app.db.models.firmware_build import FirmwareBuild
from app.db.models.hardware import BoardProfile
from app.db.session import AsyncSessionLocal

logger = logging.getLogger("uvicorn.error")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Python slim image — small and likely pre-cached on the host because
# hubex-backend itself uses it
_BUILDER_IMAGE = "python:3.11-slim"

# Max time a single build is allowed to run before being force-killed
_BUILD_TIMEOUT_SECONDS = 600  # 10 minutes
# Max log length kept in the DB row — pio output can be huge on compile errors
_MAX_LOG_BYTES = 64 * 1024
# Per-board mapping from HubEx `chip` → PlatformIO `env` name. Covers the
# four ship-with boards in `app/api/v1/hardware.py`.
_PIO_ENV_MAP: dict[str, str] = {
    "esp32": "esp32dev",
    "esp32s3": "esp32s3",
    "esp32c3": "esp32c3",
    "rp2040": "pico",
}


class FirmwareBuildError(Exception):
    """Structured builder error with a code + human-readable message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def pio_env_for_chip(chip: str) -> str:
    """Return the PlatformIO environment name for a hubex chip string."""
    return _PIO_ENV_MAP.get(chip, "esp32dev")


def build_project_tar(
    *,
    platformio_ini: str,
    main_cpp: str,
    extra_files: dict[str, str] | None = None,
) -> bytes:
    """Package a minimal PlatformIO project as a tar archive.

    The tar layout is:
        platformio.ini
        src/main.cpp
        <extra files with full relative paths>

    Returns the raw tar bytes ready to hand to
    ``portainer_client.put_container_archive``.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        def _add(name: str, data: str) -> None:
            info = tarfile.TarInfo(name=name)
            encoded = data.encode("utf-8")
            info.size = len(encoded)
            info.mtime = int(datetime.now(timezone.utc).timestamp())
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(encoded))

        _add("platformio.ini", platformio_ini)
        _add("src/main.cpp", main_cpp)
        for rel_path, content in (extra_files or {}).items():
            _add(rel_path, content)
    return buf.getvalue()


def extract_artifact_from_tar(tar_bytes: bytes, target_name: str = "firmware.bin") -> bytes | None:
    """Pull a single file (by basename) out of a tar archive returned by
    ``portainer_client.get_container_archive``. Returns ``None`` if the
    file isn't found.
    """
    try:
        with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r") as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                if member.name.endswith(target_name) or member.name == target_name:
                    f = tar.extractfile(member)
                    if f is not None:
                        return f.read()
    except tarfile.TarError as exc:
        logger.warning("firmware-builder: failed to extract tar: %s", exc)
    return None


async def run_build_job(build_id: int) -> None:
    """Drive a single build from queued → success/failed.

    Runs as a fire-and-forget ``asyncio.Task``. All state mutations go
    through a fresh DB session because the original request session is
    long gone by the time this runs.
    """
    portainer = get_portainer_client()
    container_name = f"hubex-firmware-build-{build_id}-{secrets.token_hex(3)}"

    async with AsyncSessionLocal() as db:
        build = await db.get(FirmwareBuild, build_id)
        if build is None:
            logger.warning("firmware-builder: build %s disappeared before start", build_id)
            return
        build.status = "building"
        build.container_name = container_name
        build.started_at = datetime.now(timezone.utc)
        board = await db.get(BoardProfile, build.board_profile_id)
        if board is None:
            build.status = "failed"
            build.error_code = "BOARD_NOT_FOUND"
            build.logs = f"Board profile {build.board_profile_id} not found."
            build.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return
        pio_env = build.pio_env or pio_env_for_chip(board.chip)
        build.pio_env = pio_env
        await db.commit()

    # Build the project tar AFTER the initial commit so the "building"
    # state is visible to clients polling while this (~100 ms) happens.
    platformio_ini = _make_platformio_ini(pio_env, board)
    main_cpp = _make_main_cpp(board.name)
    project_tar = build_project_tar(platformio_ini=platformio_ini, main_cpp=main_cpp)

    logs: list[str] = []
    error_code: str | None = None
    artifact: bytes | None = None

    try:
        # ── Step 1: create container (stopped state, with command ready) ──
        logs.append(f"[hubex] Creating build container {container_name}")
        docker_body = {
            "image": _BUILDER_IMAGE,
            "env": [],
            "ports": [],
            "volumes": [],
        }
        # Override the docker create body because we need custom Cmd +
        # WorkingDir + Env that the plugin_catalog docker helper doesn't
        # support. Fall back to PortainerClient.build_create_body and then
        # patch.
        create_body = portainer.build_create_body(docker_body)
        create_body["Cmd"] = [
            "sh", "-c",
            # Quiet install so logs are useful. Keep `2>&1` so pio errors
            # show up in the stdout stream.
            "pip install --quiet --no-cache-dir platformio && "
            "cd /workspace && pio run 2>&1"
        ]
        create_body["WorkingDir"] = "/workspace"
        create_body["HostConfig"]["RestartPolicy"] = {"Name": "no"}
        # create_body["Tty"] = False (default) so logs are multiplexed
        # and container_logs() strips frame headers correctly.

        create_resp = await portainer._request(  # low-level: custom body
            "POST",
            "/docker/containers/create",
            params={"name": container_name},
            json_body=create_body,
        )
        if create_resp.status_code not in (200, 201):
            raise PortainerError(
                "PORTAINER_CREATE_FAILED",
                f"create returned {create_resp.status_code}: {create_resp.text[:200]}",
                status=create_resp.status_code,
            )
        logs.append(f"[hubex] Created. Uploading project ({len(project_tar)} bytes).")

        # ── Step 2: upload project tar to /workspace ──
        # The container filesystem has /workspace empty (the image doesn't
        # create it), so we actually upload to / and let the tar carry a
        # `workspace/` top-level dir. Docker create puts WorkingDir there.
        # Simpler: upload to `/` with a tar that prefixes `workspace/`.
        project_tar_rooted = _rewrap_tar_with_prefix(project_tar, "workspace")
        await portainer.put_container_archive(container_name, "/", project_tar_rooted)
        logs.append("[hubex] Upload complete. Starting build.")

        # ── Step 3: start container (executes Cmd) ──
        await portainer.start_container(container_name)

        # ── Step 4: wait for exit ──
        final_status = await portainer.wait_for_container_exit(
            container_name,
            timeout_seconds=_BUILD_TIMEOUT_SECONDS,
            poll_interval=2.0,
        )
        logs.append(
            f"[hubex] Container exited: status={final_status.get('status')} "
            f"exit_code={final_status.get('exit_code')}"
        )

        # ── Step 5: fetch logs ──
        try:
            build_logs = await portainer.container_logs(container_name, tail=2000)
            logs.append("[hubex] ---- BUILD LOG ----")
            logs.append(build_logs)
        except PortainerError as exc:
            logs.append(f"[hubex] could not fetch build logs: {exc.code}")

        exit_code = final_status.get("exit_code") or 0
        if exit_code != 0:
            error_code = "PIO_COMPILE_FAILED"
            logs.append(f"[hubex] BUILD FAILED with exit code {exit_code}")
        else:
            # ── Step 6: fetch artifact ──
            artifact_path = f"/workspace/.pio/build/{pio_env}/firmware.bin"
            logs.append(f"[hubex] Fetching artifact: {artifact_path}")
            try:
                art_tar = await portainer.get_container_archive(container_name, artifact_path)
                artifact = extract_artifact_from_tar(art_tar, "firmware.bin")
                if artifact is None:
                    error_code = "ARTIFACT_NOT_IN_TAR"
                    logs.append("[hubex] ERROR: firmware.bin not found in container archive")
                else:
                    logs.append(f"[hubex] Artifact retrieved: {len(artifact)} bytes")
            except PortainerError as exc:
                error_code = exc.code
                logs.append(f"[hubex] ARTIFACT FETCH FAILED: {exc.code}: {exc.message}")

    except PortainerError as exc:
        error_code = exc.code
        logs.append(f"[hubex] Portainer error: {exc.code}: {exc.message}")
    except Exception as exc:  # pragma: no cover - defensive catchall
        error_code = "UNEXPECTED"
        logs.append(f"[hubex] Unexpected error: {exc}")
        logger.exception("firmware-builder: unexpected error in build %s", build_id)
    finally:
        # ── Step 7: cleanup container regardless of outcome ──
        try:
            await portainer.remove_container(container_name, force=True)
            logs.append(f"[hubex] Removed container {container_name}")
        except PortainerError as exc:
            logs.append(f"[hubex] Cleanup warning: {exc.code}: {exc.message}")

    # ── Step 8: persist final state ──
    log_text = "\n".join(logs)[-_MAX_LOG_BYTES:]
    async with AsyncSessionLocal() as db:
        build = await db.get(FirmwareBuild, build_id)
        if build is None:
            return
        if artifact is not None and error_code is None:
            build.status = "success"
            build.artifact_bytes = artifact
            build.artifact_size_kb = max(1, len(artifact) // 1024)
            build.artifact_filename = f"firmware-{build_id}.bin"
        else:
            build.status = "failed"
            build.error_code = error_code or "UNKNOWN"
        build.logs = log_text
        build.finished_at = datetime.now(timezone.utc)
        await db.commit()
    logger.info(
        "firmware-builder: build %s finished status=%s error=%s",
        build_id,
        "success" if artifact and not error_code else "failed",
        error_code,
    )


# ---------------------------------------------------------------------------
# Helpers — platformio.ini + main.cpp skeleton
# ---------------------------------------------------------------------------

# Minimal platformio.ini template. Users can customize later via a
# "Custom Code" feature (Sprint 5).
_PLATFORMIO_INI_TEMPLATE = """\
[env:{env}]
platform = {platform}
board = {board}
framework = arduino
monitor_speed = 115200
"""

# Map from hubex chip → PlatformIO platform + board name pair
_CHIP_TO_PLATFORM: dict[str, tuple[str, str]] = {
    "esp32":   ("espressif32", "esp32dev"),
    "esp32s3": ("espressif32", "esp32-s3-devkitc-1"),
    "esp32c3": ("espressif32", "esp32-c3-devkitm-1"),
    "rp2040":  ("raspberrypi", "pico"),
}


def _make_platformio_ini(env: str, board: BoardProfile) -> str:
    platform, board_name = _CHIP_TO_PLATFORM.get(
        board.chip, ("espressif32", "esp32dev")
    )
    return _PLATFORMIO_INI_TEMPLATE.format(
        env=env,
        platform=platform,
        board=board_name,
    )


# Trivial blink sketch. Sprint 5 can replace this with the M14b codegen
# output once we have a stable contract.
#
# Note: we hardcode pin 2 instead of LED_BUILTIN because the generic
# esp32dev environment doesn't define LED_BUILTIN, and this sketch has
# to compile out-of-the-box on every ship-with board profile. ESP32
# DevKit v1 onboard LED is GPIO 2. RP2040 Pico LED is GPIO 25 — fix
# that when/if a Pico profile lands.
_MAIN_CPP_TEMPLATE = """\
// HubEx firmware skeleton for {board_name}
// Generated automatically by the HubEx firmware_builder (Sprint 4).

#include <Arduino.h>

#define HUBEX_LED_PIN 2

void setup() {{
  Serial.begin(115200);
  pinMode(HUBEX_LED_PIN, OUTPUT);
  Serial.println("HubEx firmware booted on {board_name}");
}}

void loop() {{
  digitalWrite(HUBEX_LED_PIN, HIGH);
  delay(500);
  digitalWrite(HUBEX_LED_PIN, LOW);
  delay(500);
}}
"""


def _make_main_cpp(board_name: str) -> str:
    # Escape any stray braces in board name defensively
    return _MAIN_CPP_TEMPLATE.format(board_name=re.sub(r"[{}]", "", board_name))


def _rewrap_tar_with_prefix(tar_bytes: bytes, prefix: str) -> bytes:
    """Wrap every entry of ``tar_bytes`` so that ``prefix/`` is prepended.

    We do this because Portainer's ``put_container_archive`` extracts the
    tar verbatim at the given ``path``, and we want the caller to upload
    straight into ``/`` while still landing files inside ``/workspace/``.
    """
    src = tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r")
    dst_buf = io.BytesIO()
    dst = tarfile.open(fileobj=dst_buf, mode="w")
    try:
        for member in src.getmembers():
            new_member = tarfile.TarInfo(name=f"{prefix}/{member.name}")
            new_member.size = member.size
            new_member.mtime = member.mtime
            new_member.mode = member.mode
            new_member.type = member.type
            if member.isfile():
                f = src.extractfile(member)
                dst.addfile(new_member, f)
            else:
                dst.addfile(new_member)
    finally:
        dst.close()
        src.close()
    return dst_buf.getvalue()
