"""users.channel_verified — гейт подписки на канал"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "a2c4e6f80b1d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column(
        "channel_verified", sa.Boolean(), nullable=False, server_default="false"
    ))


def downgrade() -> None:
    op.drop_column("users", "channel_verified")
