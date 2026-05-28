"""rename site_code to code in discovered_nvrs

Revision ID: e1f2a3b4c5d6
Revises: d5e6f7a8b9c0
Create Date: 2026-05-28

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('uq_discovered_nvr_site_ip_port', 'discovered_nvrs', type_='unique')
    op.drop_index('ix_discovered_nvrs_site_code', table_name='discovered_nvrs')

    op.alter_column('discovered_nvrs', 'site_code', new_column_name='code')
    op.alter_column('discovered_nvrs', 'branch_name', nullable=False)

    op.create_index('ix_discovered_nvrs_code', 'discovered_nvrs', ['code'])
    op.create_unique_constraint(
        'uq_discovered_nvr_code_ip_port',
        'discovered_nvrs',
        ['code', 'nvr_ip', 'http_port'],
    )


def downgrade() -> None:
    op.drop_constraint('uq_discovered_nvr_code_ip_port', 'discovered_nvrs', type_='unique')
    op.drop_index('ix_discovered_nvrs_code', table_name='discovered_nvrs')

    op.alter_column('discovered_nvrs', 'code', new_column_name='site_code')
    op.alter_column('discovered_nvrs', 'branch_name', nullable=True)

    op.create_index('ix_discovered_nvrs_site_code', 'discovered_nvrs', ['site_code'])
    op.create_unique_constraint(
        'uq_discovered_nvr_site_ip_port',
        'discovered_nvrs',
        ['site_code', 'nvr_ip', 'http_port'],
    )
