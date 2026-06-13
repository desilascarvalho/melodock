import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import app.models  # noqa: F401 — registers all ORM models
from app.version import __version__
from app.database import async_engine, Base
from app.middleware.auth import ApiKeyMiddleware
from app.services.downloader import download_engine
from app.services.library import scan_library
from app.services.log_buffer import setup_log_handler
from app.services.scheduler import start_scheduler
from app.ws.broadcast import ws_broadcast_queue  # noqa: F401 — used by broadcaster
from app.ws.manager import manager

log = logging.getLogger(__name__)


def _apply_deemix_defaults() -> None:
    """Apply opinionated deemix metadata defaults on every startup.

    Goal: only the queried artist appears in metadata tags; featured
    artists go into the track title text only, never into artist/albumArtist fields.
    """
    try:
        from app.config import settings as app_settings
        from deemix.settings import load as dz_load, save as dz_save

        cfg = dz_load(app_settings.CONFIG_DIR)

        # Move featured artists into the track title ("feat. X" stays in title)
        # "1" = add feat to title if not already there and remove from artist fields
        cfg["featuredToTitle"] = "1"
        # Keep only the primary album artist in the albumArtist tag
        # (avoids "Artist A, Artist B" when there are feats)
        cfg["tags"]["singleAlbumArtist"] = True
        # Suppress the "artists" multi-value tag (populated with all contributors)
        cfg["tags"]["artists"] = False
        # Remove duplicate artist entries across artist/albumArtist
        cfg["removeDuplicateArtists"] = True

        dz_save(cfg, app_settings.CONFIG_DIR)
        log.info("⚙️ Deemix defaults aplicados (artist-only metadata)")
    except Exception as exc:
        log.warning("Não foi possível aplicar deemix defaults: %s", exc)


_background_tasks: set[asyncio.Task] = set()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_log_handler()

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    for coro in (download_engine.run_queue_worker(), _queue_broadcaster()):
        task = asyncio.create_task(coro)
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

    start_scheduler(asyncio.get_event_loop())

    _apply_deemix_defaults()

    try:
        await scan_library()
    except Exception as exc:
        log.warning("Startup library scan failed: %s", exc)

    log.info("🎵 Melodock v%s iniciado", __version__)
    yield

    for task in _background_tasks:
        task.cancel()
    if _background_tasks:
        await asyncio.gather(*_background_tasks, return_exceptions=True)


async def _queue_broadcaster() -> None:
    """Drain ws_broadcast_queue and fan-out to all WS clients."""
    while True:
        try:
            message = await ws_broadcast_queue.get()
            await manager.broadcast(message)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            log.debug("Broadcaster error: %s", exc)


app = FastAPI(title="Melodock", version=__version__, lifespan=lifespan)

app.add_middleware(ApiKeyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── error handlers ────────────────────────────────────────────────────────────


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": exc.status_code},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"error": str(exc), "code": 400})


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled exception on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "code": 500},
    )


# ── WebSocket ─────────────────────────────────────────────────────────────────


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    cid = await manager.connect(websocket)
    try:
        while True:
            # keep-alive: just wait for client messages (ignored) with a
            # ping sent every 30 s so proxies don't drop the connection
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(cid)
    except Exception as exc:
        log.debug("WebSocket error: %s", exc)
        manager.disconnect(cid)


# ── routers ───────────────────────────────────────────────────────────────────

from app.routers import artists, library, downloads, explorer  # noqa: E402
from app.routers import settings as settings_router  # noqa: E402
from app.routers import logs  # noqa: E402

app.include_router(artists.router, prefix="/api")
app.include_router(library.router, prefix="/api")
app.include_router(downloads.router, prefix="/api")
app.include_router(explorer.router, prefix="/api")
app.include_router(settings_router.router, prefix="/api")
app.include_router(logs.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}


# ── Static files (frontend) ───────────────────────────────────────────────────

_STATIC = Path(__file__).parent / "static"

app.mount("/", StaticFiles(directory=str(_STATIC), html=True), name="static")
