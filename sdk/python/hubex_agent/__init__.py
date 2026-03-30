"""HUBEX Agent SDK — Universal Agent for HUBEX IoT Platform.

Agents are first-class device types in HUBEX. They connect via HTTP/WebSocket,
send system telemetry as variables, and can receive commands.

Usage:
    from hubex_agent import HubexAgent

    agent = HubexAgent(
        server_url="http://localhost:8000",
        device_uid="my-agent-01",
        device_token="your-device-token",
    )
    agent.set_variable("cpu_usage", 45.2)
    agent.set_variable("memory_free_mb", 1024)
    agent.start()  # begins heartbeat + telemetry loop
"""

from hubex_agent.agent import HubexAgent

__version__ = "0.1.0"
__all__ = ["HubexAgent"]
