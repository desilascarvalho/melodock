import logging
import math
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.download_job import DownloadJob
from app.schemas.artist import (
    ArtistAddRequest,
    ArtistAddResponse,
    ArtistResponse,
    ArtistSearchRequest,
    ArtistSearchResult,
    ArtistSyncResponse,
    PaginatedArtists,
)
from app.services.deezer import DeezerClient
from app.services.downloader import download_engine

router = APIRouter(prefix="/artists", tags=["artists"])
log = logging.getLogger(__name__)
_deezer = DeezerClient()

_PICTURES_DIR = Path(settings.CONFIG_DIR) / "pictures"


def _picture_path(deezer_id: int) -> Path:
    return _PICTURES_DIR / f"{deezer_id}.jpg"


async def _fetch_and_cache_picture(deezer_id: int, url: str) -> Path | None:
    _PICTURES_DIR.mkdir(parents=True, exist_ok=True)
    dest = _picture_path(deezer_id)
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
        return dest
    except Exception:
        return None


def _artist_to_schema(artist: Artist, album_count: int | None = None) -> ArtistResponse:
    data = ArtistResponse.model_validate(artist)
    data.album_count = album_count
    return data


@router.get("", response_model=PaginatedArtists)
async def list_artists(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Artist)
    if search:
        q = q.where(Artist.name.ilike(f"%{search}%"))

    total_result = await db.execute(select(func.count()).select_from(q.subquery()))
    total = total_result.scalar_one()

    offset = (page - 1) * limit
    result = await db.execute(q.order_by(Artist.name).offset(offset).limit(limit))
    artists = result.scalars().all()

    # batch album counts
    ids = [a.id for a in artists]
    counts: dict[int, int] = {}
    if ids:
        count_result = await db.execute(
            select(Album.artist_id, func.count(Album.id))
            .where(Album.artist_id.in_(ids))
            .group_by(Album.artist_id)
        )
        counts = {row[0]: row[1] for row in count_result.all()}

    items = [_artist_to_schema(a, counts.get(a.id, 0)) for a in artists]
    return PaginatedArtists(items=items, total=total, page=page, pages=max(1, math.ceil(total / limit)))


@router.get("/{artist_id}", response_model=ArtistResponse)
async def get_artist(artist_id: int, db: AsyncSession = Depends(get_db)):
    artist = await db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(404, "Artist not found")

    count_result = await db.execute(
        select(func.count(Album.id)).where(Album.artist_id == artist_id)
    )
    return _artist_to_schema(artist, count_result.scalar_one())


@router.get("/{artist_id}/picture")
async def artist_picture(artist_id: int, db: AsyncSession = Depends(get_db)):
    artist = await db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(404, "Artist not found")

    cached = _picture_path(artist.deezer_id)

    # serve from cache
    if cached.exists():
        return FileResponse(str(cached), media_type="image/jpeg")

    # download and cache
    if artist.picture_url:
        path = await _fetch_and_cache_picture(artist.deezer_id, artist.picture_url)
        if path:
            artist.picture_cached = True
            await db.commit()
            return FileResponse(str(path), media_type="image/jpeg")

    raise HTTPException(404, "No picture available")


@router.post("/search", response_model=list[ArtistSearchResult])
async def search_artists(body: ArtistSearchRequest, db: AsyncSession = Depends(get_db)):
    results = await _deezer.search_artist(body.query)

    deezer_ids = [r["deezer_id"] for r in results]
    db_map: dict[int, int] = {}  # deezer_id → db id
    if deezer_ids:
        rows = await db.execute(
            select(Artist.deezer_id, Artist.id).where(Artist.deezer_id.in_(deezer_ids))
        )
        db_map = {row[0]: row[1] for row in rows.all()}

    return [
        ArtistSearchResult(
            **r,
            in_library=r["deezer_id"] in db_map,
            library_id=db_map.get(r["deezer_id"]),
        )
        for r in results
    ]


@router.post("/add", response_model=ArtistAddResponse)
async def add_artist(body: ArtistAddRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Artist).where(Artist.deezer_id == body.deezer_id))
    artist = existing.scalar_one_or_none()

    if not artist:
        raw = await _deezer.get_artist(body.deezer_id)
        artist = Artist(
            deezer_id=raw["deezer_id"],
            name=raw["name"],
            picture_url=raw.get("picture_url"),
            followers=raw.get("followers"),
            last_synced=datetime.now(timezone.utc),
        )
        db.add(artist)
        await db.flush()

    raw_albums = await _deezer.get_artist_albums(body.deezer_id)
    albums_found = len(raw_albums)
    jobs_created = 0
    albums_skipped = 0

    for raw_album in raw_albums:
        ok, reason = download_engine.should_download_album(raw_album)
        if not ok:
            albums_skipped += 1
            continue

        existing_album = await db.execute(
            select(Album).where(Album.deezer_id == raw_album["deezer_id"])
        )
        album = existing_album.scalar_one_or_none()
        if not album:
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

        if body.auto_download:
            existing_job = await db.execute(
                select(DownloadJob).where(
                    DownloadJob.album_id == album.id,
                    DownloadJob.status.in_(["queued", "running", "done"]),
                )
            )
            if not existing_job.scalar_one_or_none():
                job = DownloadJob(
                    deezer_id=raw_album["deezer_id"],
                    job_type="album",
                    artist_id=artist.id,
                    album_id=album.id,
                    quality=settings.DOWNLOAD_QUALITY,
                    status="queued",
                )
                db.add(job)
                jobs_created += 1

    artist.last_synced = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(artist)

    count_result = await db.execute(
        select(func.count(Album.id)).where(Album.artist_id == artist.id)
    )
    log.info(
        "🎤 Artista adicionado: %s — %d álbum(ns) encontrado(s), %d job(s) criado(s), %d ignorado(s)",
        artist.name, albums_found, jobs_created, albums_skipped,
    )
    return ArtistAddResponse(
        artist=_artist_to_schema(artist, count_result.scalar_one()),
        albums_found=albums_found,
        jobs_created=jobs_created,
        albums_skipped=albums_skipped,
    )


@router.get("/{artist_id}/albums")
async def get_artist_albums(artist_id: int, db: AsyncSession = Depends(get_db)):
    from app.models.track import Track
    from app.schemas.album import AlbumDetailResponse
    from app.schemas.track import TrackResponse

    artist = await db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(404, "Artist not found")

    album_result = await db.execute(
        select(Album).where(Album.artist_id == artist_id).order_by(Album.release_date.desc())
    )
    albums = album_result.scalars().all()

    out = []
    for album in albums:
        track_result = await db.execute(
            select(Track).where(Track.album_id == album.id).order_by(Track.disc_number, Track.track_number)
        )
        tracks = track_result.scalars().all()
        # build dict explicitly to avoid triggering lazy-load of album.tracks relationship
        album_dict = {c.key: getattr(album, c.key) for c in Album.__table__.columns}
        data = AlbumDetailResponse.model_validate(album_dict)
        data.tracks = [TrackResponse.model_validate(t) for t in tracks]
        out.append(data)

    return out


@router.delete("/{artist_id}", status_code=204)
async def delete_artist(artist_id: int, db: AsyncSession = Depends(get_db)):
    artist = await db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(404, "Artist not found")
    log.info("🗑️ Artista removido da biblioteca: %s", artist.name)
    await db.delete(artist)
    await db.commit()


@router.post("/{artist_id}/sync", response_model=ArtistSyncResponse)
async def sync_artist(artist_id: int, db: AsyncSession = Depends(get_db)):
    artist = await db.get(Artist, artist_id)
    if not artist:
        raise HTTPException(404, "Artist not found")

    raw_albums = await _deezer.get_artist_albums(artist.deezer_id)
    new_albums = 0
    new_jobs = 0

    for raw_album in raw_albums:
        ok, _ = download_engine.should_download_album(raw_album)
        if not ok:
            continue

        existing = await db.execute(
            select(Album).where(Album.deezer_id == raw_album["deezer_id"])
        )
        album = existing.scalar_one_or_none()
        if album:
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
        new_albums += 1

        job = DownloadJob(
            deezer_id=raw_album["deezer_id"],
            job_type="album",
            artist_id=artist.id,
            album_id=album.id,
            quality=settings.DOWNLOAD_QUALITY,
            status="queued",
        )
        db.add(job)
        new_jobs += 1

    artist.last_synced = datetime.now(timezone.utc)
    await db.commit()
    if new_albums:
        log.info("🔄 Sync concluído: %s — %d novo(s) álbum(ns), %d job(s) na fila", artist.name, new_albums, new_jobs)
    else:
        log.info("🔄 Sync concluído: %s — nenhuma novidade", artist.name)
    return ArtistSyncResponse(new_albums=new_albums, new_jobs=new_jobs)
