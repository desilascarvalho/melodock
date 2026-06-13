from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TrackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deezer_id: int
    album_id: int
    artist_id: int
    title: str
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    duration: Optional[int] = None
    local_path: Optional[str] = None
    file_exists: bool
    quality: Optional[str] = None
    added_at: datetime
