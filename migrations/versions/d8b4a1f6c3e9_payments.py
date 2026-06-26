"""add payments table"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8b4a1f6c3e9"
down_revision: Union[str, None] = "c7a3f9e2d5b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("days", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), server_default="RUB", nullable=False),
        sa.Column("provider", sa.String(length=16), server_default="platega", nullable=False),
        sa.Column("provider_payment_id", sa.String(length=64), nullable=True, index=True),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("payments")
