from typing import Optional

from pydantic import BaseModel


class RecentAlbum(BaseModel):
    artist: str
    title: str
    status: str
    cover_url: Optional[str] = None
    album_id: Optional[int] = None


class RecentJob(BaseModel):
    id: int
    artist: str
    album: str
    status: str
    progress: int = 0
    quality: str | None = None
    error: str | None = None


class LibraryStats(BaseModel):
    # frontend-friendly aliases
    artists: int
    albums: int
    tracks: int
    size_gb: float
    recent_albums: list[RecentAlbum] = []
    recent_jobs: list[RecentJob] = []
    # extra detail (kept for completeness)
    albums_by_status: dict[str, int] = {}
    tracks_by_quality: dict[str, int] = {}
