"""add auto_confirm to auto_assign_rules

Permite marcar counterparties como auto-confirmables. Cuando una transacción
PENDING tiene contraparte con auto_confirm=True y category+budget poblados,
se confirma automáticamente al parsear (o ahora mismo, si ya existe).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-20 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'auto_assign_rules',
        sa.Column(
            'auto_confirm',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade() -> None:
    op.drop_column('auto_assign_rules', 'auto_confirm')
