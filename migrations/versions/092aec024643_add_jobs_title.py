"""add jobs.title"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '092aec024643'
down_revision: Union[str, None] = '5124a46f182d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('title', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'title')
