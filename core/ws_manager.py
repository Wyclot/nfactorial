import asyncio
from typing import Dict, Set
from uuid import UUID

from fastapi import WebSocket


class WSManager:
    def __init__(self) -> None:
        self._rooms: Dict[UUID, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, game_id: UUID, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms.setdefault(game_id, set()).add(ws)

    async def disconnect(self, game_id: UUID, ws: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(game_id)
            if not room:
                return
            room.discard(ws)
            if not room:
                self._rooms.pop(game_id, None)

    async def broadcast(self, game_id: UUID, message: dict) -> None:
        async with self._lock:
            sockets = list(self._rooms.get(game_id, set()))
        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                pass


ws_manager = WSManager()
