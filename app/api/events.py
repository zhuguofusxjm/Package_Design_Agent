from __future__ import annotations
import asyncio
from collections import defaultdict

class EventBus:
    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

    def queue(self, session_id: str) -> asyncio.Queue:
        return self._queues[session_id]

    async def publish(self, session_id: str, event: dict) -> None:
        await self._queues[session_id].put(event)

bus = EventBus()
