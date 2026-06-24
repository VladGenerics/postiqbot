"""make publish_accounts.project_id nullable for tiktok"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b7f3a9c2d1e8"
down_revision: Union[str, None] = "092aec024643"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "publish_accounts", "project_id", existing_type=sa.Integer(), nullable=True
    )


def downgrade() -> None:
    op.alter_column(
        "publish_accounts", "project_id", existing_type=sa.Integer(), nullable=False
    )
