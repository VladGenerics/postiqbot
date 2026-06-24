"""add overlay fields to connections"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4a9b1c7e2f3"
down_revision: Union[str, None] = "c3e8f1a2b4d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("connections", sa.Column("overlay_file_id", sa.Text(), nullable=True))
    op.add_column(
        "connections", sa.Column("overlay_position", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "connections",
        sa.Column("overlay_scale", sa.Integer(), server_default="30", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("connections", "overlay_scale")
    op.drop_column("connections", "overlay_position")
    op.drop_column("connections", "overlay_file_id")
