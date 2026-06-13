import asyncio
import logging
from typing import Any

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        # each connected client gets its own delivery queue
        self._queues: dict[int, asyncio.Queue] = {}
        self._connections: dict[int, WebSocket] = {}
        self._next_id = 0

    async def connect(self, ws: WebSocket) -> int:
        await ws.accept()
        cid = self._next_id
        self._next_id += 1
        self._connections[cid] = ws
        self._queues[cid] = asyncio.Queue()
        log.debug("WS client %d connected (%d total)", cid, len(self._connections))
        return cid

    def disconnect(self, cid: int) -> None:
        self._connections.pop(cid, None)
        self._queues.pop(cid, None)
        log.debug("WS client %d disconnected (%d total)", cid, len(self._connections))

    async def broadcast(self, message: dict[str, Any]) -> None:
        for cid, ws in list(self._connections.items()):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(cid)

    async def receive_for(self, cid: int, timeout: float = 30.0) -> dict[str, Any]:
        """Block until a message is available for this client or timeout."""
        return await asyncio.wait_for(self._queues[cid].get(), timeout=timeout)


manager = ConnectionManager()
