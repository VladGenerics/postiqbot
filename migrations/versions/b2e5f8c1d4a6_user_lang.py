"""add lang to users"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2e5f8c1d4a6"
down_revision: Union[str, None] = "a1d4e7b9c2f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("lang", sa.String(length=2), server_default="ru", nullable=False)
    )


def downgrade() -> None:
    op.drop_column("users", "lang")
