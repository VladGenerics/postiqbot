"""add expiry_warned to users"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c7a3f9e2d5b8"
down_revision: Union[str, None] = "b2e5f8c1d4a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("expiry_warned", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "expiry_warned")
