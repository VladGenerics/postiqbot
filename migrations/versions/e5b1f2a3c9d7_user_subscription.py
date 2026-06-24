"""add trial/subscription fields to users"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e5b1f2a3c9d7"
down_revision: Union[str, None] = "d4a9b1c7e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("trial_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users", sa.Column("subscription_until", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "subscription_until")
    op.drop_column("users", "trial_until")
