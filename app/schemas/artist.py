from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ArtistBase(BaseModel):
    deezer_id: int
    name: str
    picture_url: Optional[str] = None
    followers: Optional[int] = None
    genres: Optional[list] = None


class ArtistResponse(ArtistBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    picture_cached: bool
    added_at: datetime
    last_synced: Optional[datetime] = None
    album_count: Optional[int] = None


class ArtistSearchResult(BaseModel):
    deezer_id: int
    name: str
    picture_url: Optional[str] = None
    followers: Optional[int] = None
    nb_album: Optional[int] = None
    in_library: bool = False
    library_id: Optional[int] = None  # banco id, presente quando in_library=True


class ArtistSearchRequest(BaseModel):
    query: str


class ArtistAddRequest(BaseModel):
    deezer_id: int
    auto_download: bool = True


class ArtistAddResponse(BaseModel):
    artist: ArtistResponse
    albums_found: int
    jobs_created: int
    albums_skipped: int


class ArtistSyncResponse(BaseModel):
    new_albums: int
    new_jobs: int


class PaginatedArtists(BaseModel):
    items: list[ArtistResponse]
    total: int
    page: int
    pages: int
