"""add referral fields to users"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6c2d8a1b3e4"
down_revision: Union[str, None] = "e5b1f2a3c9d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("referred_by", sa.BigInteger(), nullable=True))
    op.add_column(
        "users",
        sa.Column("referral_rewarded", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "referral_rewarded")
    op.drop_column("users", "referred_by")
