"""add schedule fields to connections"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3e8f1a2b4d6"
down_revision: Union[str, None] = "b7f3a9c2d1e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "connections",
        sa.Column("schedule_mode", sa.String(length=16), server_default="immediate", nullable=False),
    )
    op.add_column(
        "connections",
        sa.Column("interval_minutes", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("connections", sa.Column("post_times", sa.JSON(), nullable=True))
    op.add_column(
        "connections",
        sa.Column("tz", sa.String(length=48), server_default="UTC", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("connections", "tz")
    op.drop_column("connections", "post_times")
    op.drop_column("connections", "interval_minutes")
    op.drop_column("connections", "schedule_mode")
