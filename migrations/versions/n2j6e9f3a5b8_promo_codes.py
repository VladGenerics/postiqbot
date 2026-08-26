"""промокоды на скидку: promo_codes, promo_redemptions, привязка к юзеру и платежу"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "n2j6e9f3a5b8"
down_revision: Union[str, None] = "l8h4c7d9e3f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("percent", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(length=16), nullable=True),
        sa.Column("max_uses", sa.Integer(), server_default="0", nullable=False),
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("code", name="uq_promo_codes_code"),
    )
    op.create_table(
        "promo_redemptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("promo_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("payment_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["promo_id"], ["promo_codes.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("promo_id", "user_id", name="uq_promo_user"),
    )
    op.create_index("ix_promo_redemptions_promo_id", "promo_redemptions", ["promo_id"])
    op.create_index("ix_promo_redemptions_user_id", "promo_redemptions", ["user_id"])
    op.add_column("users", sa.Column("promo_code", sa.String(length=32), nullable=True))
    op.add_column("payments", sa.Column("promo_code", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "promo_code")
    op.drop_column("users", "promo_code")
    op.drop_index("ix_promo_redemptions_user_id", table_name="promo_redemptions")
    op.drop_index("ix_promo_redemptions_promo_id", table_name="promo_redemptions")
    op.drop_table("promo_redemptions")
    op.drop_table("promo_codes")
