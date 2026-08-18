"""connections: авто-публикация в TikTok (настройки один раз на связку)"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "k6f2a5b8d1c4"
down_revision: Union[str, None] = "j5e1f4a7c9b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FLAGS = (
    ("tt_auto", "false"),
    ("tt_disable_comment", "true"),
    ("tt_disable_duet", "true"),
    ("tt_disable_stitch", "true"),
    ("tt_brand_organic", "false"),
    ("tt_brand_content", "false"),
)


def upgrade() -> None:
    for name, default in _FLAGS:
        op.add_column(
            "connections",
            sa.Column(
                name, sa.Boolean(), nullable=False, server_default=sa.text(default)
            ),
        )
    op.add_column(
        "connections", sa.Column("tt_privacy", sa.String(32), nullable=True)
    )
    op.add_column(
        "connections",
        sa.Column("tt_consent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "jobs",
        sa.Column(
            "publish_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "publish_attempts")
    op.drop_column("connections", "tt_consent_at")
    op.drop_column("connections", "tt_privacy")
    for name, _ in reversed(_FLAGS):
        op.drop_column("connections", name)
