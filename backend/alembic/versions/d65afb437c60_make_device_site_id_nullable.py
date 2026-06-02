"""make_device_site_id_nullable

Revision ID: d65afb437c60
Revises: e1f2a3b4c5d6
Create Date: 2026-06-02 15:07:49.890186

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = 'd65afb437c60'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('devices', 'site_id',
                    existing_type=UUID(as_uuid=True),
                    nullable=True)


def downgrade() -> None:
    op.alter_column('devices', 'site_id',
                    existing_type=UUID(as_uuid=True),
                    nullable=False)
