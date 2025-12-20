from typing import Dict, Set
from fastapi import WebSocket


class Hub:
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


hub = Hub()
