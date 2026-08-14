"""jobs: счётчик попыток скачивания (мягкий ретрай вместо failed)"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "j5e1f4a7c9b3"
down_revision: Union[str, None] = "i4d0e3f6a8b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "download_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("jobs", "download_attempts")
