"""remove_drive_fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("albums") as batch_op:
        batch_op.drop_column("drive_path")
        batch_op.drop_column("uploaded_to_drive")

    with op.batch_alter_table("tracks") as batch_op:
        batch_op.drop_column("drive_path")
        batch_op.drop_column("uploaded_to_drive")


def downgrade() -> None:
    with op.batch_alter_table("tracks") as batch_op:
        batch_op.add_column(sa.Column("drive_path", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("uploaded_to_drive", sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table("albums") as batch_op:
        batch_op.add_column(sa.Column("drive_path", sa.String(500), nullable=True))
        batch_op.add_column(sa.Column("uploaded_to_drive", sa.Boolean(), nullable=False, server_default=sa.false()))
