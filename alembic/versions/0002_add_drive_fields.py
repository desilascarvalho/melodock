"""add_drive_fields

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tracks", sa.Column("drive_path", sa.String(500), nullable=True))
    op.add_column("tracks", sa.Column("uploaded_to_drive", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column("albums", sa.Column("drive_path", sa.String(500), nullable=True))
    op.add_column("albums", sa.Column("uploaded_to_drive", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("tracks", "uploaded_to_drive")
    op.drop_column("tracks", "drive_path")
    op.drop_column("albums", "uploaded_to_drive")
    op.drop_column("albums", "drive_path")
