"""drop unique on transactions.email_id

Una transferencia entre cuentas propias en BancoEstado genera UN email pero
DOS transacciones (un EXPENSE en cuenta origen, un INCOME en cuenta destino).
La constraint unique impedía esto.

Revision ID: a1b2c3d4e5f6
Revises: ca341310e114
Create Date: 2026-04-19 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'ca341310e114'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop unique constraint on transactions.email_id.

    Postgres nombra la constraint automáticamente como '{table}_{col}_key'.
    """
    op.drop_constraint('transactions_email_id_key', 'transactions', type_='unique')


def downgrade() -> None:
    """Re-add unique constraint. Esto fallará si hay múltiples transacciones
    apuntando al mismo email_id (ej: transferencias entre cuentas propias)."""
    op.create_unique_constraint(
        'transactions_email_id_key', 'transactions', ['email_id']
    )
