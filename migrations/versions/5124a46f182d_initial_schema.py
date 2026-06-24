"""initial schema"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5124a46f182d'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('source_channels',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('platform', sa.String(length=16), nullable=False),
    sa.Column('channel_id', sa.String(length=64), nullable=False),
    sa.Column('channel_title', sa.String(length=255), nullable=False),
    sa.Column('last_seen_video_id', sa.String(length=64), nullable=True),
    sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('platform', 'channel_id', name='uq_source_channel')
    )
    op.create_table('users',
    sa.Column('telegram_id', sa.BigInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('telegram_id')
    )
    op.create_table('oauth_projects',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=False),
    sa.Column('client_id', sa.String(length=255), nullable=False),
    sa.Column('client_secret_enc', sa.Text(), nullable=False),
    sa.Column('owner_telegram_id', sa.BigInteger(), nullable=True),
    sa.Column('daily_quota', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_telegram_id'], ['users.telegram_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('client_id')
    )
    op.create_table('publish_accounts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('platform', sa.String(length=16), nullable=False),
    sa.Column('channel_id', sa.String(length=64), nullable=False),
    sa.Column('channel_title', sa.String(length=255), nullable=False),
    sa.Column('refresh_token_enc', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['oauth_projects.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'platform', 'channel_id', name='uq_publish_channel')
    )
    op.create_table('connections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.BigInteger(), nullable=False),
    sa.Column('publish_account_id', sa.Integer(), nullable=False),
    sa.Column('source_channel_id', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('privacy', sa.String(length=16), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['publish_account_id'], ['publish_accounts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_channel_id'], ['source_channels.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.telegram_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('publish_account_id', 'source_channel_id', name='uq_connection')
    )
    op.create_table('jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('connection_id', sa.Integer(), nullable=False),
    sa.Column('source_video_id', sa.String(length=64), nullable=False),
    sa.Column('video_url', sa.Text(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('local_path', sa.Text(), nullable=True),
    sa.Column('youtube_video_id', sa.String(length=64), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['connection_id'], ['connections.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('connection_id', 'source_video_id', name='uq_job_source_video')
    )
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_jobs_status'), table_name='jobs')
    op.drop_table('jobs')
    op.drop_table('connections')
    op.drop_table('publish_accounts')
    op.drop_table('oauth_projects')
    op.drop_table('users')
    op.drop_table('source_channels')
