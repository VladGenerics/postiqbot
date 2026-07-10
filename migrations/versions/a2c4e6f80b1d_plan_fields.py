"""add plan fields: users.tier_priority/tier_plan, payments.plan"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a2c4e6f80b1d"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("tier_priority", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("tier_plan", sa.String(length=16), nullable=True))
    op.add_column("payments", sa.Column("plan", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("payments", "plan")
    op.drop_column("users", "tier_plan")
    op.drop_column("users", "tier_priority")
