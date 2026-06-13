from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deezer_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    artist_id: Mapped[int] = mapped_column(Integer, ForeignKey("artists.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    release_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cover_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cover_cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    album_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nb_tracks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    local_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    artist = relationship("Artist", backref="albums")
