"""merge weather and chat heads

Revision ID: 5f165b9082ae
Revises: 0539089229a6, 9f6220f7b1a0
Create Date: 2026-03-11 12:16:10.191525

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f165b9082ae'
down_revision = ('0539089229a6', '9f6220f7b1a0')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
