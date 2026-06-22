"""Migration 1: Add streaming_available to film table

Revision ID: 001_add_streaming_available
Revises: 
Create Date: 2025-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "001_streaming_avail"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "film",
        sa.Column(
            "streaming_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Seed some films as streamable for demo purposes
    op.execute("""
        UPDATE film
        SET streaming_available = TRUE
        WHERE film_id IN (
            SELECT film_id FROM film ORDER BY film_id LIMIT 50
        )
    """)


def downgrade() -> None:
    op.drop_column("film", "streaming_available")
