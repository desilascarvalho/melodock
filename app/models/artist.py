from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deezer_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    picture_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    picture_cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    followers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    genres: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    last_synced: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
