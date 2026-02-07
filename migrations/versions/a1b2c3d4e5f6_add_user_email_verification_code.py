"""add user email_verification_code

Revision ID: a1b2c3d4e5f6
Revises: 7905211acebb
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "7905211acebb"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column("email_verification_code", sa.String(length=6), nullable=True),
    )


def downgrade():
    op.drop_column("user", "email_verification_code")
