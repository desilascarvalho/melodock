from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AlbumBase(BaseModel):
    deezer_id: int
    title: str
    release_date: Optional[str] = None
    cover_url: Optional[str] = None
    album_type: Optional[str] = None
    nb_tracks: Optional[int] = None


class AlbumResponse(AlbumBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artist_id: int
    cover_cached: bool
    status: str
    local_path: Optional[str] = None
    added_at: datetime


class AlbumDetailResponse(AlbumResponse):
    tracks: list["TrackResponse"] = []


class PaginatedAlbums(BaseModel):
    items: list[AlbumResponse]
    total: int
    page: int
    pages: int


# avoid circular import — resolved at bottom
from app.schemas.track import TrackResponse  # noqa: E402

AlbumDetailResponse.model_rebuild()
