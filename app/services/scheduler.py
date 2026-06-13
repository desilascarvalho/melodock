import asyncio
import logging
import threading
import time
from datetime import datetime, timezone, timedelta

import schedule
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.album import Album
from app.models.artist import Artist
from app.models.download_job import DownloadJob
from app.services.deezer import DeezerClient
from app.services.downloader import download_engine
from app.services.library import scan_library
from app.ws.broadcast import broadcast
from app.config import settings

log = logging.getLogger(__name__)
_deezer = DeezerClient()

# shared event loop reference — set by start_scheduler()
_loop: asyncio.AbstractEventLoop | None = None


def _run_async(coro) -> None:
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, _loop)
    else:
        log.warning("No running event loop; skipping scheduled task")


# ── jobs ──────────────────────────────────────────────────────────────────────

def sync_all_artists_job() -> None:
    log.info("Scheduler: starting artist sync")
    _run_async(_sync_all_artists())


def library_scan_job() -> None:
    log.info("Scheduler: starting library scan")
    _run_async(_library_scan())


def cleanup_old_jobs() -> None:
    log.info("Scheduler: cleaning up old jobs")
    _run_async(_cleanup_old_jobs())


async def _sync_all_artists() -> None:
    new_albums_total = 0
    new_jobs_total = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Artist))
        artists = result.scalars().all()

    for artist in artists:
        try:
            raw_albums = await _deezer.get_artist_albums(artist.deezer_id)
        except Exception as exc:
            log.warning("Sync failed for artist %d: %s", artist.deezer_id, exc)
            continue

        async with AsyncSessionLocal() as db:
            for raw_album in raw_albums:
                ok, _ = download_engine.should_download_album(raw_album)
                if not ok:
                    continue

                existing = await db.execute(
                    select(Album).where(Album.deezer_id == raw_album["deezer_id"])
                )
                if existing.scalar_one_or_none():
                    continue

                album = Album(
                    deezer_id=raw_album["deezer_id"],
                    artist_id=artist.id,
                    title=raw_album["title"],
                    release_date=raw_album.get("release_date"),
                    cover_url=raw_album.get("cover_url"),
                    album_type=raw_album.get("album_type"),
                    nb_tracks=raw_album.get("nb_tracks"),
                    status="pending",
                )
                db.add(album)
                await db.flush()
                new_albums_total += 1

                job = DownloadJob(
                    deezer_id=raw_album["deezer_id"],
                    job_type="album",
                    artist_id=artist.id,
                    album_id=album.id,
                    quality=settings.DOWNLOAD_QUALITY,
                    status="queued",
                )
                db.add(job)
                new_jobs_total += 1

            await db.commit()

    log.info("Sync complete: %d new albums, %d new jobs", new_albums_total, new_jobs_total)
    await broadcast(
        "sync_complete",
        {"new_albums": new_albums_total, "new_jobs": new_jobs_total, "ts": datetime.now(timezone.utc).isoformat()},
    )


async def _library_scan() -> None:
    stats = await scan_library()
    await broadcast("library_scan_complete", stats)


async def _cleanup_old_jobs() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DownloadJob).where(
                DownloadJob.status == "done",
                DownloadJob.finished_at < cutoff,
            )
        )
        jobs = result.scalars().all()
        count = len(jobs)
        for job in jobs:
            await db.delete(job)
        await db.commit()
    log.info("Cleaned up %d old completed jobs", count)


# ── runner ────────────────────────────────────────────────────────────────────

def _scheduler_thread() -> None:
    while True:
        schedule.run_pending()
        time.sleep(30)


def start_scheduler(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop

    schedule.every().day.at("03:00").do(sync_all_artists_job)
    schedule.every().week.do(library_scan_job)
    schedule.every().day.at("04:00").do(cleanup_old_jobs)

    t = threading.Thread(target=_scheduler_thread, daemon=True, name="melodock-scheduler")
    t.start()
    log.info("Scheduler started (daemon thread)")
