"""initial

Revision ID: 0001
Revises:
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deezer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("picture_url", sa.String(500), nullable=True),
        sa.Column("picture_cached", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("followers", sa.Integer(), nullable=True),
        sa.Column("genres", sa.JSON(), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_synced", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("deezer_id"),
    )
    op.create_index("ix_artists_deezer_id", "artists", ["deezer_id"])

    op.create_table(
        "albums",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deezer_id", sa.Integer(), nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("release_date", sa.String(20), nullable=True),
        sa.Column("cover_url", sa.String(500), nullable=True),
        sa.Column("cover_cached", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("album_type", sa.String(50), nullable=True),
        sa.Column("nb_tracks", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("local_path", sa.String(500), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("deezer_id"),
    )
    op.create_index("ix_albums_deezer_id", "albums", ["deezer_id"])

    op.create_table(
        "tracks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deezer_id", sa.Integer(), nullable=False),
        sa.Column("album_id", sa.Integer(), sa.ForeignKey("albums.id"), nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("track_number", sa.Integer(), nullable=True),
        sa.Column("disc_number", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("local_path", sa.String(500), nullable=True),
        sa.Column("file_exists", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quality", sa.String(20), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("deezer_id"),
    )
    op.create_index("ix_tracks_deezer_id", "tracks", ["deezer_id"])

    op.create_table(
        "download_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("deezer_id", sa.Integer(), nullable=False),
        sa.Column("job_type", sa.String(20), nullable=False),
        sa.Column("artist_id", sa.Integer(), sa.ForeignKey("artists.id"), nullable=True),
        sa.Column("album_id", sa.Integer(), sa.ForeignKey("albums.id"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("quality", sa.String(20), nullable=True),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("download_jobs")
    op.drop_index("ix_tracks_deezer_id", table_name="tracks")
    op.drop_table("tracks")
    op.drop_index("ix_albums_deezer_id", table_name="albums")
    op.drop_table("albums")
    op.drop_index("ix_artists_deezer_id", table_name="artists")
    op.drop_table("artists")
