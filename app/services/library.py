import logging
from pathlib import Path
from typing import TypedDict

from mutagen import File as MutagenFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.track import Track

log = logging.getLogger(__name__)

_AUDIO_EXTS = {".flac", ".mp3", ".ogg", ".opus", ".m4a"}


class ScanStats(TypedDict):
    scanned: int
    new_found: int
    updated: int


async def scan_library() -> ScanStats:
    music_dir = Path(settings.MUSIC_DIR)
    if not music_dir.exists():
        log.warning("MUSIC_DIR %s does not exist", music_dir)
        return {"scanned": 0, "new_found": 0, "updated": 0}

    audio_files = [f for f in music_dir.rglob("*") if f.suffix.lower() in _AUDIO_EXTS]
    scanned = len(audio_files)
    new_found = 0
    updated = 0

    async with AsyncSessionLocal() as db:
        for path in audio_files:
            local_path = str(path)
            result = await db.execute(select(Track).where(Track.local_path == local_path))
            track = result.scalar_one_or_none()

            meta = _read_metadata(path)

            if track is None:
                # try to match an existing DB track by title + local path not set
                meta_title = (meta.get("title") or path.stem).strip()
                orphan_result = await db.execute(
                    select(Track).where(
                        Track.file_exists == False,  # noqa: E712
                        Track.local_path == None,  # noqa: E711
                    )
                )
                orphan = next(
                    (t for t in orphan_result.scalars().all() if t.title.strip().lower() == meta_title.lower()),
                    None,
                )
                if orphan:
                    orphan.local_path = local_path
                    orphan.file_exists = True
                    orphan.quality = _detect_quality(path)
                    if meta.get("duration"):
                        orphan.duration = meta["duration"]
                    new_found += 1
                else:
                    # orphan file not in DB — skip to avoid deezer_id=0 collisions
                    log.debug("Scan: arquivo sem track no banco, ignorado: %s", path.name)

            else:
                changed = False
                if not track.file_exists:
                    track.file_exists = True
                    changed = True
                if meta.get("duration") and track.duration != meta["duration"]:
                    track.duration = meta["duration"]
                    changed = True
                if changed:
                    updated += 1

        await db.commit()

    log.info("📚 Scan concluído: %d arquivo(s) · %d novo(s) · %d atualizado(s)", scanned, new_found, updated)
    return {"scanned": scanned, "new_found": new_found, "updated": updated}


def _read_metadata(path: Path) -> dict:
    try:
        audio = MutagenFile(path, easy=True)
        if not audio:
            return {}

        def _first(tag: str) -> str | None:
            val = audio.tags and audio.tags.get(tag)
            return val[0] if val else None

        duration = int(audio.info.length) if audio.info else None
        track_str = _first("tracknumber") or ""
        track_num = int(track_str.split("/")[0]) if track_str else None
        disc_str = _first("discnumber") or ""
        disc_num = int(disc_str.split("/")[0]) if disc_str else None

        return {
            "title": _first("title"),
            "track_number": track_num,
            "disc_number": disc_num,
            "duration": duration,
        }
    except Exception as exc:
        log.debug("Could not read metadata for %s: %s", path, exc)
        return {}


def _detect_quality(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".flac":
        return "FLAC"
    try:
        audio = MutagenFile(path)
        if audio and audio.info:
            bitrate = getattr(audio.info, "bitrate", 0)
            if bitrate >= 300_000:
                return "MP3_320"
    except Exception:
        pass
    return "MP3_128"
