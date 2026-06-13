import asyncio
import logging
from collections import deque
from datetime import datetime, timezone


class LogBuffer:
    def __init__(self, maxlen: int = 500) -> None:
        self.entries: deque[dict[str, str]] = deque(maxlen=maxlen)

    def append(self, entry: dict[str, str]) -> None:
        self.entries.append(entry)


log_buffer = LogBuffer()

# loggers de app que queremos capturar
_APP_LOGGERS = [
    "app.routers.artists",
    "app.routers.downloads",
    "app.routers.library",
    "app.routers.settings",
    "app.services.downloader",
    "app.services.library",
    "app.services.scheduler",
    "app.main",
]


class WebSocketLogHandler(logging.Handler):
    """Feeds log records into LogBuffer and the WS broadcast queue."""

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "level": record.levelname,
            "msg": self.format(record),
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
        }
        log_buffer.append(entry)

        try:
            from app.ws.broadcast import ws_broadcast_queue
            try:
                ws_broadcast_queue.put_nowait({"type": "log", "data": entry})
            except asyncio.QueueFull:
                pass
        except Exception:
            pass


def setup_log_handler() -> None:
    handler = WebSocketLogHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.setLevel(logging.INFO)

    # attach to each app logger directly (avoids root logger level filtering)
    for name in _APP_LOGGERS:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        # avoid duplicates if called twice
        if not any(isinstance(h, WebSocketLogHandler) for h in logger.handlers):
            logger.addHandler(handler)
