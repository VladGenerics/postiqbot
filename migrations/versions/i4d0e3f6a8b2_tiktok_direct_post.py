"""jobs: опции TikTok Direct Post + статус awaiting"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "i4d0e3f6a8b2"
down_revision: Union[str, None] = "h3c9d2e5f7a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FLAGS = (
    ("tt_disable_comment", "true"),
    ("tt_disable_duet", "true"),
    ("tt_disable_stitch", "true"),
    ("tt_brand_organic", "false"),
    ("tt_brand_content", "false"),
)


def upgrade() -> None:
    op.add_column("jobs", sa.Column("tt_privacy", sa.String(32), nullable=True))
    for name, default in _FLAGS:
        op.add_column(
            "jobs",
            sa.Column(
                name, sa.Boolean(), nullable=False, server_default=sa.text(default)
            ),
        )
    op.add_column("jobs", sa.Column("tt_publish_id", sa.String(64), nullable=True))
    op.add_column(
        "jobs", sa.Column("awaiting_since", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("jobs", sa.Column("card_message_id", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "card_message_id")
    op.drop_column("jobs", "awaiting_since")
    op.drop_column("jobs", "tt_publish_id")
    for name, _ in reversed(_FLAGS):
        op.drop_column("jobs", name)
    op.drop_column("jobs", "tt_privacy")
