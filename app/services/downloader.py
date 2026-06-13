import asyncio
import logging
import random
import shutil
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.album import Album
from app.models.artist import Artist
from app.models.download_job import DownloadJob
from app.models.track import Track
from app.ws.broadcast import broadcast

log = logging.getLogger(__name__)

_AUDIO_EXTS = {".flac", ".mp3", ".ogg", ".opus", ".m4a"}


def _sanitize(name: str) -> str:
    """Remove characters unsafe for directory names."""
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip()


class DownloadEngine:
    def should_download_album(self, album: dict) -> tuple[bool, str]:
        album_type = (album.get("album_type") or "").lower()
        if settings.ALLOWED_TYPES and album_type not in [t.lower() for t in settings.ALLOWED_TYPES]:
            return False, f"type '{album_type}' not in ALLOWED_TYPES"

        title = (album.get("title") or "").lower()
        for kw in settings.KEYWORD_BLOCKLIST:
            if kw.lower() in title:
                return False, f"title matches blocklist keyword '{kw}'"

        nb = album.get("nb_tracks") or 0
        if settings.MAX_TRACKS_PER_ALBUM and nb > settings.MAX_TRACKS_PER_ALBUM:
            return False, f"nb_tracks {nb} exceeds MAX_TRACKS_PER_ALBUM {settings.MAX_TRACKS_PER_ALBUM}"

        return True, ""

    async def _stealth_delay(self) -> None:
        delay = random.uniform(settings.DOWNLOAD_DELAY_MIN, settings.DOWNLOAD_DELAY_MAX)
        await asyncio.sleep(delay)

    async def download_album(self, job_id: int, deezer_album_id: int, quality: str) -> bool:
        async with AsyncSessionLocal() as db:
            job = await db.get(DownloadJob, job_id)
            if not job:
                log.error("Job %d not found", job_id)
                return False

            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

        await broadcast("job_progress", {"job_id": job_id, "progress": 0, "status": "running"})

        async with AsyncSessionLocal() as db:
            job_info = await db.get(DownloadJob, job_id)
            album_label = str(deezer_album_id)
            if job_info and job_info.album_id:
                album = await db.get(Album, job_info.album_id)
                if album:
                    album_label = album.title
            artist_label = ""
            if job_info and job_info.artist_id:
                artist = await db.get(Artist, job_info.artist_id)
                if artist:
                    artist_label = artist.name + " — "
        log.info("⬇️ Iniciando download: %s%s (qualidade: %s)", artist_label, album_label, quality)

        try:
            listener, success = await asyncio.to_thread(self._run_deemix, deezer_album_id, quality, job_id)
        except Exception as exc:
            log.exception("Deemix error for job %d: %s", job_id, exc)
            await self._mark_error(job_id, str(exc))
            return False

        if not success:
            error_msg = (listener.first_error if listener else None) or "Deemix returned failure"
            log.error("❌ Download falhou: %s%s — %s", artist_label, album_label, error_msg)
            await self._mark_error(job_id, error_msg)
            return False

        await self._finalize_job(job_id, deezer_album_id, quality, listener)
        return True

    def _run_deemix(self, deezer_album_id: int, quality: str, job_id: int) -> bool:
        """Blocking deemix call — runs in a thread pool via asyncio.to_thread."""
        try:
            from deemix import generateDownloadObject
            from deemix.downloader import Downloader
            from deemix.settings import DEFAULTS as deemix_defaults
            from deezer import Deezer

            dz = Deezer()
            if settings.DEEZER_ARL:
                logged_in = dz.login_via_arl(settings.DEEZER_ARL)
                if not logged_in:
                    log.error("ARL login failed for job %d", job_id)
                    return False
            else:
                log.error("No DEEZER_ARL configured for job %d", job_id)
                return False

            deemix_settings = dict(deemix_defaults)
            deemix_settings["downloadLocation"] = settings.DOWNLOADS_DIR
            deemix_settings["maxBitrate"] = _quality_to_bitrate(quality)
            # fall back to lower bitrate instead of failing silently
            deemix_settings["fallbackBitrate"] = True

            url = f"https://www.deezer.com/album/{deezer_album_id}"
            obj = generateDownloadObject(dz, url, deemix_settings["maxBitrate"])
            if not obj:
                log.error("generateDownloadObject returned None for album %d", deezer_album_id)
                return False

            listener = _ProgressListener(job_id)
            downloader = Downloader(dz, obj, deemix_settings, listener)
            downloader.start()

            if listener.total > 0 and listener.failed >= listener.total:
                log.error(
                    "All %d tracks failed for album %d (first error: %s)",
                    listener.failed, deezer_album_id, listener.first_error,
                )
                return listener, False

            if listener.failed > 0:
                log.warning(
                    "%d/%d tracks failed for album %d",
                    listener.failed, listener.total, deezer_album_id,
                )

            return listener, True
        except Exception as exc:
            log.exception("_run_deemix error: %s", exc)
            return None, False

    async def _finalize_job(self, job_id: int, deezer_album_id: int, quality: str, listener: "_ProgressListener | None" = None) -> None:
        album_id: int | None = None
        artist_name = "Unknown Artist"
        album_title = str(deezer_album_id)
        local_album_path: str | None = None

        async with AsyncSessionLocal() as db:
            job = await db.get(DownloadJob, job_id)
            if not job:
                return

            result = await db.execute(select(Album).where(Album.deezer_id == deezer_album_id))
            album = result.scalar_one_or_none()

            if album:
                album_id = album.id
                album_title = album.title
                album.status = "done"

                result2 = await db.execute(select(Artist).where(Artist.id == album.artist_id))
                artist = result2.scalar_one_or_none()
                if artist:
                    artist_name = artist.name

                dest = Path(settings.MUSIC_DIR) / _sanitize(artist_name) / _sanitize(album_title)

                # deemix names the folder "{Artist} - {Album}" — try that first,
                # then fall back to just the album title.
                # For singles/EPs with one track, deemix may drop files directly
                # in downloads root instead of creating a subdirectory.
                downloads_root = Path(settings.DOWNLOADS_DIR)
                artist_album_dir = f"{_sanitize(artist_name)} - {_sanitize(album_title)}"
                src = downloads_root / artist_album_dir
                if not src.exists():
                    src = downloads_root / _sanitize(album_title)
                if not src.exists():
                    # find any subdirectory whose name contains the album title
                    candidates_dir = [
                        d for d in downloads_root.iterdir()
                        if d.is_dir() and _sanitize(album_title).lower() in d.name.lower()
                    ]
                    if candidates_dir:
                        src = candidates_dir[0]

                moved_files: list[Path] = []
                if src.exists() and src.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    for f in src.iterdir():
                        if f.suffix.lower() in _AUDIO_EXTS or f.suffix.lower() in {".jpg", ".png", ".nfo"}:
                            shutil.move(str(f), str(dest / f.name))
                            moved_files.append(dest / f.name)
                    try:
                        src.rmdir()
                    except OSError:
                        pass
                    album.local_path = str(dest)
                    local_album_path = str(dest)
                else:
                    # Fallback: deemix dropped files directly in downloads root.
                    # Collect audio files whose name matches "{Artist} - {Album}" pattern.
                    album_title_san = _sanitize(album_title).lower()
                    artist_name_san = _sanitize(artist_name).lower()
                    loose_files = [
                        f for f in downloads_root.iterdir()
                        if f.is_file()
                        and f.suffix.lower() in _AUDIO_EXTS
                        and (album_title_san in f.stem.lower() or artist_name_san in f.stem.lower())
                    ]
                    if loose_files:
                        dest.mkdir(parents=True, exist_ok=True)
                        for f in loose_files:
                            shutil.move(str(f), str(dest / f.name))
                            moved_files.append(dest / f.name)
                        album.local_path = str(dest)
                        local_album_path = str(dest)
                    else:
                        log.warning(
                            "⚠️ Nenhum arquivo encontrado em downloads para: %s — %s",
                            artist_name, album_title,
                        )

                all_audio_in_dest: list[Path] = (
                    [f for f in Path(album.local_path).iterdir() if f.suffix.lower() in _AUDIO_EXTS]
                    if album.local_path and Path(album.local_path).exists()
                    else []
                )

                result3 = await db.execute(select(Track).where(Track.album_id == album.id))
                db_tracks = result3.scalars().all()

                # If no tracks in DB yet, fetch from Deezer and create them
                if not db_tracks and all_audio_in_dest:
                    try:
                        from app.services.deezer import DeezerClient
                        dz_data = await DeezerClient().get_album(deezer_album_id)
                        dz_tracks = dz_data.get("tracks", [])
                        for dz_t in dz_tracks:
                            existing = await db.execute(select(Track).where(Track.deezer_id == dz_t["deezer_id"]))
                            if not existing.scalar_one_or_none():
                                db.add(Track(
                                    deezer_id=dz_t["deezer_id"],
                                    album_id=album.id,
                                    artist_id=album.artist_id,
                                    title=dz_t.get("title", ""),
                                    track_number=dz_t.get("track_number"),
                                    disc_number=dz_t.get("disc_number"),
                                    duration=dz_t.get("duration"),
                                    file_exists=False,
                                ))
                        await db.flush()
                        result3b = await db.execute(select(Track).where(Track.album_id == album.id))
                        db_tracks = result3b.scalars().all()
                        log.info("📋 %d faixa(s) criada(s) via Deezer para: %s", len(db_tracks), album_title)
                    except Exception as exc:
                        log.warning("Não foi possível buscar tracks do Deezer para %s: %s", album_title, exc)

                for track in db_tracks:
                    if not album.local_path:
                        continue
                    track_title_san = _sanitize(track.title).lower()
                    candidates = [
                        f for f in all_audio_in_dest
                        if track_title_san in f.stem.lower()
                        or (track.track_number and f.stem.startswith(str(track.track_number).zfill(2)))
                        or (track.track_number and f.stem.startswith(str(track.track_number) + " "))
                    ]
                    if not candidates and len(all_audio_in_dest) == 1 and len(db_tracks) == 1:
                        candidates = all_audio_in_dest
                    if candidates:
                        track.local_path = str(candidates[0])
                        track.file_exists = True
                        deezer_id_str = str(track.deezer_id)
                        if listener and deezer_id_str in listener.track_qualities:
                            track.quality = _bitrate_to_quality(listener.track_qualities[deezer_id_str])
                        else:
                            track.quality = _detect_file_quality(Path(candidates[0]))

            job.progress = 100
            await db.commit()

        await self._set_job_status(job_id, "done")
        log.info("✅ Download concluído: %s — %s → %s", artist_name, album_title, local_album_path or "?")
        await broadcast("job_progress", {"job_id": job_id, "progress": 100, "status": "done"})
        await broadcast("job_done", {"job_id": job_id, "album_title": album_title, "artist_name": artist_name})

        await self._update_queue_count()

    async def _set_job_status(self, job_id: int, status: str, error: str | None = None) -> None:
        async with AsyncSessionLocal() as db:
            job = await db.get(DownloadJob, job_id)
            if job:
                job.status = status
                if error:
                    job.error_message = error
                if status in ("done", "error"):
                    job.finished_at = datetime.now(timezone.utc)
                await db.commit()

    async def _mark_error(self, job_id: int, message: str) -> None:
        await self._set_job_status(job_id, "error", error=message)
        await broadcast("job_error", {"job_id": job_id, "error": message})
        await self._update_queue_count()

    async def _update_queue_count(self) -> None:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(DownloadJob).where(DownloadJob.status == "queued"))
            count = len(result.scalars().all())
        await broadcast("queue_updated", {"pending_count": count})

    async def download_track(self, job_id: int, deezer_track_id: int, quality: str) -> bool:
        async with AsyncSessionLocal() as db:
            job = await db.get(DownloadJob, job_id)
            if not job:
                return False
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

        await broadcast("job_progress", {"job_id": job_id, "progress": 0, "status": "running"})

        # snapshot files in downloads dir before calling deemix
        downloads_root = Path(settings.DOWNLOADS_DIR)
        before: set[Path] = set()
        if downloads_root.exists():
            before = {p for p in downloads_root.rglob("*") if p.is_file() and p.suffix.lower() in _AUDIO_EXTS}

        try:
            listener, success = await asyncio.to_thread(self._run_deemix_track, deezer_track_id, quality, job_id)
        except Exception as exc:
            log.exception("Deemix track error for job %d: %s", job_id, exc)
            await self._mark_error(job_id, str(exc))
            return False

        if not success:
            error_msg = (listener.first_error if listener else None) or "Deemix returned failure"
            await self._mark_error(job_id, error_msg)
            return False

        after: set[Path] = set()
        if downloads_root.exists():
            after = {p for p in downloads_root.rglob("*") if p.is_file() and p.suffix.lower() in _AUDIO_EXTS}
        new_files = list(after - before)

        await self._finalize_track_job(job_id, deezer_track_id, quality, new_files, listener)
        return True

    def _run_deemix_track(self, deezer_track_id: int, quality: str, job_id: int):
        try:
            from deemix import generateDownloadObject
            from deemix.downloader import Downloader
            from deemix.settings import DEFAULTS as deemix_defaults
            from deezer import Deezer

            dz = Deezer()
            if settings.DEEZER_ARL:
                logged_in = dz.login_via_arl(settings.DEEZER_ARL)
                if not logged_in:
                    log.error("ARL login failed for track job %d", job_id)
                    return None, False
            else:
                log.error("No DEEZER_ARL configured for track job %d", job_id)
                return None, False

            deemix_settings = dict(deemix_defaults)
            deemix_settings["downloadLocation"] = settings.DOWNLOADS_DIR
            deemix_settings["maxBitrate"] = _quality_to_bitrate(quality)
            deemix_settings["fallbackBitrate"] = True

            url = f"https://www.deezer.com/track/{deezer_track_id}"
            obj = generateDownloadObject(dz, url, deemix_settings["maxBitrate"])
            if not obj:
                log.error("generateDownloadObject returned None for track %d", deezer_track_id)
                return None, False

            listener = _ProgressListener(job_id)
            downloader = Downloader(dz, obj, deemix_settings, listener)
            downloader.start()

            if listener.total > 0 and listener.failed >= listener.total:
                return listener, False

            return listener, True
        except Exception as exc:
            log.exception("_run_deemix_track error: %s", exc)
            return None, False

    async def _finalize_track_job(self, job_id: int, deezer_track_id: int, quality: str, new_files: list[Path], listener) -> None:
        track_title = str(deezer_track_id)
        artist_name = "Unknown"
        album_title = "Unknown"

        async with AsyncSessionLocal() as db:
            job = await db.get(DownloadJob, job_id)
            if not job:
                return

            result = await db.execute(select(Track).where(Track.deezer_id == deezer_track_id))
            track = result.scalar_one_or_none()

            if track:
                track_title = track.title
                album_result = await db.execute(select(Album).where(Album.id == track.album_id))
                album = album_result.scalar_one_or_none()
                artist_result = await db.execute(select(Artist).where(Artist.id == track.artist_id))
                artist = artist_result.scalar_one_or_none()
                if artist:
                    artist_name = artist.name
                if album:
                    album_title = album.title

                # determine destination folder
                if album and album.local_path and Path(album.local_path).exists():
                    dest_dir = Path(album.local_path)
                else:
                    dest_dir = Path(settings.MUSIC_DIR) / _sanitize(artist_name) / _sanitize(album_title)
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    if album:
                        album.local_path = str(dest_dir)

                if new_files:
                    src_file = new_files[0]
                    dest_file = dest_dir / src_file.name
                    shutil.move(str(src_file), str(dest_file))
                    # clean up empty parent dir in downloads
                    try:
                        src_file.parent.rmdir()
                    except OSError:
                        pass
                    track.local_path = str(dest_file)
                    track.file_exists = True
                    deezer_id_str = str(deezer_track_id)
                    if listener and deezer_id_str in listener.track_qualities:
                        track.quality = _bitrate_to_quality(listener.track_qualities[deezer_id_str])
                    else:
                        track.quality = _detect_file_quality(dest_file)

            if job:
                job.progress = 100
            await db.commit()

        await self._set_job_status(job_id, "done")
        log.info("✅ Faixa baixada: %s — %s / %s", artist_name, album_title, track_title)
        await broadcast("job_progress", {"job_id": job_id, "progress": 100, "status": "done"})
        await broadcast("job_done", {"job_id": job_id, "album_title": album_title, "artist_name": artist_name})
        await self._update_queue_count()

    async def run_queue_worker(self) -> None:
        log.info("🚀 Melodock iniciado — worker de downloads ativo")
        while True:
            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(DownloadJob)
                        .where(DownloadJob.status == "queued")
                        .order_by(DownloadJob.created_at)
                        .limit(1)
                    )
                    job = result.scalar_one_or_none()

                if job is None:
                    await asyncio.sleep(5)
                    continue

                quality = job.quality or settings.DOWNLOAD_QUALITY
                if job.job_type == "track":
                    await self.download_track(job.id, job.deezer_id, quality)
                else:
                    await self.download_album(job.id, job.deezer_id, quality)
                await self._stealth_delay()

            except asyncio.CancelledError:
                log.info("Queue worker cancelled")
                break
            except Exception as exc:
                log.exception("Queue worker error: %s", exc)
                await asyncio.sleep(10)


def _detect_file_quality(path: Path) -> str:
    if path.suffix.lower() == ".flac":
        return "FLAC"
    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(path)
        if audio and audio.info:
            bitrate = getattr(audio.info, "bitrate", 0)
            if bitrate >= 300_000:
                return "MP3_320"
    except Exception:
        pass
    return "MP3_128"


def _quality_to_bitrate(quality: str) -> int:
    return {"FLAC": 9, "MP3_320": 3, "MP3_128": 1}.get(quality.upper(), 3)


def _bitrate_to_quality(bitrate: int) -> str:
    return {9: "FLAC", 3: "MP3_320", 1: "MP3_128"}.get(bitrate, "MP3_128")


class _ProgressListener:
    """Deemix listener — forwards progress to WS and tracks failures."""

    def __init__(self, job_id: int) -> None:
        self.job_id = job_id
        self.total = 0
        self.failed = 0
        self.first_error: str | None = None
        # maps deezer track id → actual downloaded bitrate
        self.track_qualities: dict[str, int] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            pass

    def send(self, key: str, value) -> None:  # noqa: ANN001
        if key == "updateQueue" and isinstance(value, dict):
            if value.get("failed"):
                self.failed += 1
                errid = value.get("errid", "")
                error_msg = value.get("error", "")
                if not self.first_error:
                    title = value.get("data", {}).get("title", "?")
                    self.first_error = f"{errid}: {title} — {error_msg}"
                log.warning(
                    "Track failed (job %d): %s — %s",
                    self.job_id, errid,
                    value.get("data", {}).get("title", "?"),
                )
            else:
                progress = value.get("progress")
                if progress is not None:
                    self._emit("job_progress", {"job_id": self.job_id, "progress": progress, "status": "running"})

                    async def _persist(job_id: int, prog: int) -> None:
                        async with AsyncSessionLocal() as db:
                            job = await db.get(DownloadJob, job_id)
                            if job:
                                job.progress = prog
                                await db.commit()

                    if self._loop and self._loop.is_running():
                        asyncio.run_coroutine_threadsafe(_persist(self.job_id, progress), self._loop)

        elif key == "downloadInfo" and isinstance(value, dict):
            state = value.get("state")
            track_id = str(value.get("data", {}).get("id", ""))
            if state == "getTags":
                self.total += 1
            elif state == "downloaded" and track_id:
                # deemix reports the actual bitrate used after fallback
                bitrate = value.get("data", {}).get("bitrate") or value.get("bitrate")
                if bitrate is not None:
                    self.track_qualities[track_id] = int(bitrate)

    def _emit(self, event: str, data: dict) -> None:
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(broadcast(event, data), self._loop)


download_engine = DownloadEngine()
