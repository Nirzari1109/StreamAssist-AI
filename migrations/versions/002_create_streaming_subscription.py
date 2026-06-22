"""Migration 2: Create streaming_subscription table

Revision ID: 002_create_streaming_subscription
Revises: 001_add_streaming_available
Create Date: 2025-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "002_streaming_sub"
down_revision = "001_streaming_avail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "streaming_subscription",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "customer_id",
            sa.Integer(),
            sa.ForeignKey("customer.customer_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("plan_name", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.true()),
    )

    # Seed subscriptions for the first 5 customers for local testing
    op.execute("""
        INSERT INTO streaming_subscription
            (customer_id, plan_name, status, start_date, end_date, auto_renew)
        SELECT
            customer_id,
            'Standard',
            'active',
            CURRENT_DATE - INTERVAL '30 days',
            CURRENT_DATE + INTERVAL '335 days',
            TRUE
        FROM customer
        ORDER BY customer_id
        LIMIT 5
    """)


def downgrade() -> None:
    op.drop_table("streaming_subscription")
