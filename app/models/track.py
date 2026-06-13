from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deezer_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    album_id: Mapped[int] = mapped_column(Integer, ForeignKey("albums.id"), nullable=False)
    artist_id: Mapped[int] = mapped_column(Integer, ForeignKey("artists.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    track_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    disc_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    local_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_exists: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quality: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    album = relationship("Album", backref="tracks")
    artist = relationship("Artist", backref="tracks")
