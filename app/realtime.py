from typing import Dict, Set
from fastapi import WebSocket


class Hub:
    """Per-device telemetry WebSocket hub (existing)."""

    def __init__(self) -> None:
        self.clients: Dict[int, Set[WebSocket]] = {}

    async def add(self, device_id: int, ws: WebSocket) -> None:
        self.clients.setdefault(device_id, set()).add(ws)

    def remove(self, device_id: int, ws: WebSocket) -> None:
        clients = self.clients.get(device_id)
        if not clients:
            return
        clients.discard(ws)
        if not clients:
            del self.clients[device_id]

    async def broadcast(self, device_id: int, payload: dict) -> None:
        for ws in list(self.clients.get(device_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.remove(device_id, ws)


class UserHub:
    """User-level WebSocket hub — notifications + channel events."""

    def __init__(self) -> None:
        self.clients: Dict[int, Set[WebSocket]] = {}  # user_id → websockets

    async def add(self, user_id: int, ws: WebSocket) -> None:
        self.clients.setdefault(user_id, set()).add(ws)

    def remove(self, user_id: int, ws: WebSocket) -> None:
        clients = self.clients.get(user_id)
        if not clients:
            return
        clients.discard(ws)
        if not clients:
            del self.clients[user_id]

    async def push(self, user_id: int, payload: dict) -> None:
        """Push a message to all connections for this user."""
        for ws in list(self.clients.get(user_id, set())):
            try:
                await ws.send_json(payload)
            except Exception:
                self.remove(user_id, ws)

    async def push_notification(self, user_id: int, notification: dict) -> None:
        """Push a notification envelope to a specific user."""
        await self.push(user_id, {"type": "notification", "data": notification})

    async def send_ui_command(self, user_id: int, command: str, payload: dict) -> None:
        """Send an AI Coop UI command to all browser sessions of this user."""
        msg = {"type": "ui_command", "command": command, "payload": payload}
        await self.push(user_id, msg)

    async def broadcast_event(self, channel: str, payload: dict) -> None:
        """Broadcast a channel event to ALL connected users."""
        msg = {"type": "event", "channel": channel, "data": payload}
        for user_id in list(self.clients.keys()):
            for ws in list(self.clients.get(user_id, set())):
                try:
                    await ws.send_json(msg)
                except Exception:
                    self.remove(user_id, ws)

    @property
    def connection_count(self) -> int:
        return sum(len(s) for s in self.clients.values())


hub = Hub()
user_hub = UserHub()
