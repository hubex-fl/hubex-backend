"""HUBEX Bridge Framework (M24).

A Bridge is a special agent that translates between external protocols
(Serial/UART, Modbus, BLE, CAN) and HUBEX's variable/telemetry system.

Architecture:
    External Protocol → Bridge Plugin → HUBEX Agent → Variables

Usage:
    from hubex_agent.bridge import HubexBridge, BridgePlugin

    class MyModbusPlugin(BridgePlugin):
        name = "modbus_rtu"
        protocol = "modbus"

        async def discover(self):
            # Scan for Modbus devices
            return [{"address": 1, "name": "Sensor #1"}]

        async def poll(self):
            # Read Modbus registers → return as variable dict
            return {"temperature": 23.5, "humidity": 65}

    bridge = HubexBridge(
        server_url="http://localhost:8000",
        device_uid="bridge-modbus-01",
        device_token="your-token",
    )
    bridge.register_plugin(MyModbusPlugin())
    bridge.start()
"""

import abc
import asyncio
import logging
import threading
import time
from typing import Any, Optional

from hubex_agent.agent import HubexAgent

logger = logging.getLogger("hubex.bridge")


class BridgePlugin(abc.ABC):
    """Base class for bridge protocol plugins."""

    name: str = "unnamed"
    protocol: str = "unknown"
    poll_interval: int = 10  # seconds

    @abc.abstractmethod
    async def discover(self) -> list[dict[str, Any]]:
        """Discover devices on this protocol.

        Returns list of dicts with at least: {address, name}
        """
        ...

    @abc.abstractmethod
    async def poll(self) -> dict[str, Any]:
        """Poll current values from the external device(s).

        Returns dict of variable_key → value.
        """
        ...

    async def write(self, key: str, value: Any) -> bool:
        """Write a value to the external device (optional).

        Override for bidirectional bridges.
        """
        logger.warning("Write not implemented for plugin '%s'", self.name)
        return False

    async def setup(self) -> None:
        """Initialize the plugin (open serial port, connect BLE, etc.)."""
        pass

    async def teardown(self) -> None:
        """Clean up resources."""
        pass


class SerialBridgePlugin(BridgePlugin):
    """Example: Serial/UART bridge plugin stub."""

    name = "serial_uart"
    protocol = "serial"

    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200):
        self.port = port
        self.baud = baud
        self._connection = None

    async def discover(self) -> list[dict[str, Any]]:
        return [{"address": self.port, "name": f"Serial@{self.port}"}]

    async def poll(self) -> dict[str, Any]:
        # Stub — real implementation would read serial data
        return {"serial.connected": True, "serial.port": self.port}


class ModbusBridgePlugin(BridgePlugin):
    """Example: Modbus RTU/TCP bridge plugin stub."""

    name = "modbus_rtu"
    protocol = "modbus"
    poll_interval = 5

    def __init__(self, host: str = "localhost", port: int = 502, unit_id: int = 1):
        self.host = host
        self.port = port
        self.unit_id = unit_id

    async def discover(self) -> list[dict[str, Any]]:
        return [{"address": self.unit_id, "name": f"Modbus@{self.host}:{self.port}"}]

    async def poll(self) -> dict[str, Any]:
        # Stub — real implementation would use pymodbus
        return {"modbus.connected": True, "modbus.unit": self.unit_id}


class BLEBridgePlugin(BridgePlugin):
    """Example: Bluetooth Low Energy bridge plugin stub."""

    name = "ble_scanner"
    protocol = "ble"
    poll_interval = 15

    async def discover(self) -> list[dict[str, Any]]:
        # Stub — real implementation would use bleak
        return []

    async def poll(self) -> dict[str, Any]:
        return {"ble.scanning": True}


class HubexBridge:
    """Bridge agent that manages multiple protocol plugins."""

    def __init__(
        self,
        server_url: str,
        device_uid: str,
        device_token: str,
        heartbeat_interval: int = 30,
    ):
        self._plugins: list[BridgePlugin] = []
        self._agent = HubexAgent(
            server_url=server_url,
            device_uid=device_uid,
            device_token=device_token,
            heartbeat_interval=heartbeat_interval,
            telemetry_interval=999999,  # We handle telemetry per-plugin
        )
        self._running = False
        self._threads: list[threading.Thread] = []

    def register_plugin(self, plugin: BridgePlugin) -> None:
        """Register a protocol plugin."""
        self._plugins.append(plugin)
        logger.info("Registered bridge plugin: %s (%s)", plugin.name, plugin.protocol)

    def start(self) -> None:
        """Start the bridge agent and all plugins."""
        if self._running:
            return
        self._running = True

        # Start the base agent (heartbeat)
        self._agent.start()

        # Start a poll loop per plugin
        for plugin in self._plugins:
            t = threading.Thread(
                target=self._plugin_loop,
                args=(plugin,),
                daemon=True,
                name=f"bridge-{plugin.name}",
            )
            t.start()
            self._threads.append(t)

        logger.info("Bridge started with %d plugins", len(self._plugins))

    def stop(self) -> None:
        """Stop the bridge and all plugins."""
        self._running = False
        self._agent.stop()
        for t in self._threads:
            t.join(timeout=5)
        logger.info("Bridge stopped")

    def _plugin_loop(self, plugin: BridgePlugin) -> None:
        """Poll loop for a single plugin."""
        loop = asyncio.new_event_loop()

        # Setup
        try:
            loop.run_until_complete(plugin.setup())
        except Exception as e:
            logger.error("Plugin %s setup failed: %s", plugin.name, e)
            return

        while self._running:
            try:
                data = loop.run_until_complete(plugin.poll())
                if data:
                    # Prefix keys with plugin name
                    prefixed = {
                        f"{plugin.name}.{k}": v
                        for k, v in data.items()
                    }
                    self._agent.send_telemetry(prefixed)
            except Exception as e:
                logger.error("Plugin %s poll error: %s", plugin.name, e)

            time.sleep(plugin.poll_interval)

        # Teardown
        try:
            loop.run_until_complete(plugin.teardown())
        except Exception:
            pass
        loop.close()
