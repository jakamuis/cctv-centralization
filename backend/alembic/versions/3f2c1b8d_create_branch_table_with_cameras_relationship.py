"""create branch table with cameras relationship

Revision ID: 3f2c1b8d
Revises: 1da1b116d228
Create Date: 2026-05-22 13:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as pg

# revision identifiers, used by Alembic.
revision = '3f2c1b8d'
down_revision = "1da1b116d228"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'branches',
        sa.Column('id', pg.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('code', sa.String(), nullable=False, unique=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table('branches')
