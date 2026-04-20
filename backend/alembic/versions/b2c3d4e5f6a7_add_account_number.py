"""add account_number to accounts

Permite mapear emails al Account correcto usando los últimos 4 dígitos del
número de cuenta extraídos del email del banco.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-19 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'accounts',
        sa.Column('account_number', sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('accounts', 'account_number')
