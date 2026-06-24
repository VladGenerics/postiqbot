"""add tier limits + video usage to users"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1d4e7b9c2f5"
down_revision: Union[str, None] = "f6c2d8a1b3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("tier_accounts", sa.Integer(), server_default="1", nullable=False))
    op.add_column("users", sa.Column("tier_videos", sa.Integer(), server_default="5", nullable=False))
    op.add_column("users", sa.Column("videos_used", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "videos_used")
    op.drop_column("users", "tier_videos")
    op.drop_column("users", "tier_accounts")
