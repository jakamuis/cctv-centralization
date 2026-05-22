"""create camera table with branch relationship

Revision ID: add_camera_table_001
Revises: create_branch_table_with_cameras_relationship
Create Date: 2026-05-22 14:08:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psql

# revision identifiers, used by Alembic.
revision = 'add_camera_table_001'
down_revision = '3f2c1b8d'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'cameras',
        sa.Column('id', psql.UUID(as_uuid=True), primary_key=True, nullable=False, unique=True),
        sa.Column('branch_id', psql.UUID(as_uuid=True), sa.ForeignKey('branches.id'), nullable=False, index=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('stream_name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('rtsp_channel', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(op.f('ix_cameras_branch_id'), 'cameras', ['branch_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_cameras_branch_id'), table_name='cameras', if_exists=True)
    op.drop_table('cameras')
