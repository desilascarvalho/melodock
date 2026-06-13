from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DownloadJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deezer_id: int
    job_type: str
    artist_id: Optional[int] = None
    album_id: Optional[int] = None
    status: str
    quality: Optional[str] = None
    progress: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    # enriched at query time
    artist_name: Optional[str] = None
    album_title: Optional[str] = None


class DownloadJobCreate(BaseModel):
    deezer_id: int
    job_type: str = "album"
    quality: Optional[str] = None


class PaginatedJobs(BaseModel):
    items: list[DownloadJobResponse]
    total: int
    running_count: int
    queued_count: int
