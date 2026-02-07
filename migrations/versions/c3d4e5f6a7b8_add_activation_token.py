"""add user activation_token for email link activation

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-07

"""
from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "user",
        sa.Column("activation_token", sa.String(length=64), nullable=True),
    )
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_user_activation_token"), ["activation_token"], unique=True)


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_activation_token"))
    op.drop_column("user", "activation_token")
