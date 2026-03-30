"""HUBEX Agent — connects to HUBEX as a device of type 'agent'.

The agent:
  1. Registers itself via device pairing (or uses existing token)
  2. Sends periodic heartbeats
  3. Reports system telemetry as variables
  4. Listens for variable-write commands (optional WebSocket)
"""

import logging
import platform
import threading
import time
from typing import Any, Callable, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger("hubex.agent")


class HubexAgent:
    """HUBEX Agent SDK — connects a machine/process to HUBEX as an agent device."""

    def __init__(
        self,
        server_url: str,
        device_uid: str,
        device_token: str,
        heartbeat_interval: int = 30,
        telemetry_interval: int = 60,
        collectors: Optional[list[Callable[[], dict[str, Any]]]] = None,
    ):
        self.server_url = server_url.rstrip("/")
        self.device_uid = device_uid
        self.device_token = device_token
        self.heartbeat_interval = heartbeat_interval
        self.telemetry_interval = telemetry_interval
        self.collectors = collectors or []

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._variables: dict[str, Any] = {}
        self._session = requests.Session() if requests else None

        if not self._session:
            raise RuntimeError("requests library required: pip install requests")

        self._session.headers.update({
            "X-Device-Token": self.device_token,
            "Content-Type": "application/json",
        })

    # ── Public API ────────────────────────────────────────────────────────

    def set_variable(self, key: str, value: Any) -> None:
        """Set a variable value to send in next telemetry."""
        self._variables[key] = value

    def send_telemetry(self, payload: Optional[dict] = None) -> bool:
        """Send telemetry data immediately."""
        data = payload or {}

        # Merge collected variables
        for collector in self.collectors:
            try:
                data.update(collector())
            except Exception as e:
                logger.warning("Collector failed: %s", e)

        # Add any manually set variables
        data.update(self._variables)

        # Add agent metadata
        data["_agent"] = {
            "sdk_version": "0.1.0",
            "platform": platform.system(),
            "hostname": platform.node(),
            "python": platform.python_version(),
        }

        try:
            resp = self._session.post(
                f"{self.server_url}/api/v1/telemetry",
                json={
                    "device_uid": self.device_uid,
                    "event_type": "agent.telemetry",
                    "payload": data,
                },
            )
            if resp.status_code in (200, 201):
                logger.debug("Telemetry sent: %d keys", len(data))
                return True
            else:
                logger.warning("Telemetry failed: HTTP %d", resp.status_code)
                return False
        except Exception as e:
            logger.error("Telemetry error: %s", e)
            return False

    def heartbeat(self) -> bool:
        """Send heartbeat to mark device as online."""
        try:
            resp = self._session.post(
                f"{self.server_url}/api/v1/telemetry",
                json={
                    "device_uid": self.device_uid,
                    "event_type": "agent.heartbeat",
                    "payload": {"status": "alive", "uptime": self._uptime()},
                },
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            logger.error("Heartbeat error: %s", e)
            return False

    def start(self) -> None:
        """Start background heartbeat and telemetry loop."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(
            "Agent started: %s → %s (heartbeat=%ds, telemetry=%ds)",
            self.device_uid, self.server_url,
            self.heartbeat_interval, self.telemetry_interval,
        )

    def stop(self) -> None:
        """Stop the background loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Agent stopped: %s", self.device_uid)

    # ── Private ───────────────────────────────────────────────────────────

    def _loop(self) -> None:
        last_heartbeat = 0.0
        last_telemetry = 0.0

        while self._running:
            now = time.time()

            if now - last_heartbeat >= self.heartbeat_interval:
                self.heartbeat()
                last_heartbeat = now

            if now - last_telemetry >= self.telemetry_interval:
                self.send_telemetry()
                last_telemetry = now

            time.sleep(1)

    def _uptime(self) -> float:
        return time.time() - getattr(self, "_start_time", time.time())


# ── Built-in Collectors ──────────────────────────────────────────────────


def system_collector() -> dict[str, Any]:
    """Collect basic system metrics."""
    import os

    data: dict[str, Any] = {
        "platform": platform.system(),
        "hostname": platform.node(),
        "architecture": platform.machine(),
    }

    # CPU load (Unix only)
    try:
        load = os.getloadavg()
        data["cpu_load_1m"] = round(load[0], 2)
        data["cpu_load_5m"] = round(load[1], 2)
        data["cpu_load_15m"] = round(load[2], 2)
    except (OSError, AttributeError):
        pass

    # Try psutil if available
    try:
        import psutil
        data["cpu_percent"] = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        data["memory_total_mb"] = round(mem.total / 1048576)
        data["memory_used_percent"] = round(mem.percent, 1)
        disk = psutil.disk_usage("/")
        data["disk_used_percent"] = round(disk.percent, 1)
    except ImportError:
        pass

    return data


def network_collector() -> dict[str, Any]:
    """Collect network interface information."""
    import socket

    data: dict[str, Any] = {}
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        data["ip_address"] = ip
        data["hostname"] = hostname
    except Exception:
        pass

    try:
        import psutil
        counters = psutil.net_io_counters()
        data["net_bytes_sent"] = counters.bytes_sent
        data["net_bytes_recv"] = counters.bytes_recv
    except ImportError:
        pass

    return data
