from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DownloadJob(Base):
    __tablename__ = "download_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deezer_id: Mapped[int] = mapped_column(Integer, nullable=False)
    job_type: Mapped[str] = mapped_column(String(20), nullable=False)
    artist_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("artists.id"), nullable=True)
    album_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("albums.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="queued", nullable=False)
    quality: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    artist = relationship("Artist", backref="download_jobs")
    album = relationship("Album", backref="download_jobs")
