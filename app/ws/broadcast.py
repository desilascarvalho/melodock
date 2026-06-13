import asyncio

ws_broadcast_queue: asyncio.Queue = asyncio.Queue()


async def broadcast(event_type: str, data: dict) -> None:
    await ws_broadcast_queue.put({"type": event_type, "data": data})
