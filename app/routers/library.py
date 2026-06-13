import asyncio
import math
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.album import Album
from app.models.artist import Artist
from app.models.download_job import DownloadJob
from app.models.track import Track
from app.schemas.album import AlbumDetailResponse, AlbumResponse, PaginatedAlbums
from app.schemas.library import LibraryStats, RecentAlbum, RecentJob
from app.schemas.track import TrackResponse
from app.services.library import scan_library

router = APIRouter(prefix="/library", tags=["library"])


@router.get("", response_model=LibraryStats)
async def library_stats(db: AsyncSession = Depends(get_db)):
    total_artists = (await db.execute(select(func.count(Artist.id)))).scalar_one()
    total_albums = (await db.execute(select(func.count(Album.id)))).scalar_one()
    total_tracks = (await db.execute(select(func.count(Track.id)))).scalar_one()

    total_size_gb = 0.0
    music_path = Path(settings.MUSIC_DIR)
    if music_path.exists():
        total_bytes = sum(f.stat().st_size for f in music_path.rglob("*") if f.is_file())
        total_size_gb = round(total_bytes / (1024 ** 3), 3)

    status_rows = await db.execute(
        select(Album.status, func.count(Album.id)).group_by(Album.status)
    )
    albums_by_status = {row[0]: row[1] for row in status_rows.all()}

    quality_rows = await db.execute(
        select(Track.quality, func.count(Track.id)).group_by(Track.quality)
    )
    tracks_by_quality = {(row[0] or "unknown"): row[1] for row in quality_rows.all()}

    # Recent albums (last 10 with artist name)
    recent_album_rows = await db.execute(
        select(Album, Artist.name)
        .join(Artist, Album.artist_id == Artist.id)
        .order_by(Album.added_at.desc())
        .limit(10)
    )
    recent_albums = [
        RecentAlbum(artist=row[1], title=row[0].title, status=row[0].status, cover_url=row[0].cover_url, album_id=row[0].id)
        for row in recent_album_rows.all()
    ]

    # Recent jobs (last 10 with artist/album names)
    recent_job_rows = await db.execute(
        select(DownloadJob, Artist.name, Album.title)
        .outerjoin(Artist, DownloadJob.artist_id == Artist.id)
        .outerjoin(Album, DownloadJob.album_id == Album.id)
        .order_by(DownloadJob.created_at.desc())
        .limit(10)
    )
    recent_jobs = [
        RecentJob(
            id=row[0].id,
            artist=row[1] or "—",
            album=row[2] or str(row[0].deezer_id),
            status=row[0].status,
            progress=row[0].progress,
            quality=row[0].quality,
            error=row[0].error_message,
        )
        for row in recent_job_rows.all()
    ]

    return LibraryStats(
        artists=total_artists,
        albums=total_albums,
        tracks=total_tracks,
        size_gb=total_size_gb,
        recent_albums=recent_albums,
        recent_jobs=recent_jobs,
        albums_by_status=albums_by_status,
        tracks_by_quality=tracks_by_quality,
    )


@router.get("/albums", response_model=PaginatedAlbums)
async def list_albums(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    artist_id: int | None = Query(None),
    album_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Album)
    if status:
        q = q.where(Album.status == status)
    if artist_id:
        q = q.where(Album.artist_id == artist_id)
    if album_type:
        q = q.where(Album.album_type == album_type)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    offset = (page - 1) * limit
    result = await db.execute(q.order_by(Album.added_at.desc()).offset(offset).limit(limit))
    albums = result.scalars().all()

    return PaginatedAlbums(
        items=[AlbumResponse.model_validate(a) for a in albums],
        total=total,
        page=page,
        pages=max(1, math.ceil(total / limit)),
    )


@router.get("/albums/{album_id}", response_model=AlbumDetailResponse)
async def get_album(album_id: int, db: AsyncSession = Depends(get_db)):
    album = await db.get(Album, album_id)
    if not album:
        raise HTTPException(404, "Album not found")

    result = await db.execute(
        select(Track).where(Track.album_id == album_id).order_by(Track.disc_number, Track.track_number)
    )
    tracks = result.scalars().all()

    data = AlbumDetailResponse.model_validate(album)
    data.tracks = [TrackResponse.model_validate(t) for t in tracks]
    return data


@router.post("/scan")
async def trigger_scan():
    asyncio.create_task(scan_library())
    return {"task": "started"}


@router.post("/audit")
async def trigger_audit():
    asyncio.create_task(scan_library())
    return {"task": "started"}


