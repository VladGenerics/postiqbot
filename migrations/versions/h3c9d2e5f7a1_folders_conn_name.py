"""folders + connections.name/folder_id — папки и переименование связок"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "h3c9d2e5f7a1"
down_revision: Union[str, None] = "g1h2i3j4k5l6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("users.telegram_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_folders_user_id", "folders", ["user_id"])
    op.add_column("connections", sa.Column("name", sa.String(64), nullable=True))
    op.add_column(
        "connections",
        sa.Column(
            "folder_id",
            sa.Integer(),
            sa.ForeignKey("folders.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("connections", "folder_id")
    op.drop_column("connections", "name")
    op.drop_index("ix_folders_user_id", table_name="folders")
    op.drop_table("folders")
