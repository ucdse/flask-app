"""add verification code expires_at and sent_at

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column("email_verification_code_expires_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("email_verification_code_sent_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column("user", "email_verification_code_sent_at")
    op.drop_column("user", "email_verification_code_expires_at")
