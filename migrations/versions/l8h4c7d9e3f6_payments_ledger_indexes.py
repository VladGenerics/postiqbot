"""платежи: идемпотентность Stars, granted_at, горячие индексы"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "l8h4c7d9e3f6"
down_revision: Union[str, None] = "k6f2a5b8d1c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_payments_provider_tx",
        "payments",
        ["provider", "provider_payment_id"],
        unique=True,
        postgresql_where=sa.text("provider_payment_id IS NOT NULL"),
    )
    op.add_column(
        "payments", sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.execute("UPDATE payments SET granted_at = paid_at WHERE status = 'paid'")
    op.add_column("jobs", sa.Column("yt_resumable_uri", sa.Text(), nullable=True))
    op.create_index(op.f("ix_jobs_connection_id"), "jobs", ["connection_id"])
    op.create_index("ix_jobs_status_updated_at", "jobs", ["status", "updated_at"])
    op.create_index(op.f("ix_connections_user_id"), "connections", ["user_id"])
    op.create_index(
        op.f("ix_publish_accounts_user_id"), "publish_accounts", ["user_id"]
    )
    op.alter_column("users", "tier_videos", server_default="4")


def downgrade() -> None:
    op.alter_column("users", "tier_videos", server_default="5")
    op.drop_index(
        op.f("ix_publish_accounts_user_id"), table_name="publish_accounts"
    )
    op.drop_index(op.f("ix_connections_user_id"), table_name="connections")
    op.drop_index("ix_jobs_status_updated_at", table_name="jobs")
    op.drop_index(op.f("ix_jobs_connection_id"), table_name="jobs")
    op.drop_column("jobs", "yt_resumable_uri")
    op.drop_column("payments", "granted_at")
    op.drop_index(
        "uq_payments_provider_tx",
        table_name="payments",
        postgresql_where=sa.text("provider_payment_id IS NOT NULL"),
    )
