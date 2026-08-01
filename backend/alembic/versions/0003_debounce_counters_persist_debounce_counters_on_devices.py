"""persist debounce counters on devices

Revision ID: 0003_debounce_counters
Revises: 0002_check_results
Create Date: 2026-08-01 20:17:00.247503

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0003_debounce_counters'
down_revision: Union[str, None] = '0002_check_results'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('devices', sa.Column('consecutive_fail_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('devices', sa.Column('consecutive_ok_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('devices', 'consecutive_ok_count')
    op.drop_column('devices', 'consecutive_fail_count')
