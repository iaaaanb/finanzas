"""add sync_runs table

Tabla para tracking de ejecuciones de sync con Gmail.
Sirve para mostrar "última actualización" en la UI y como concurrency guard.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-19 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sync_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column(
            'trigger',
            sa.Enum('CRON', 'UI_INCREMENTAL', 'UI_BACKFILL', name='sync_trigger'),
            nullable=False,
        ),
        sa.Column(
            'status',
            sa.Enum('RUNNING', 'SUCCESS', 'FAILED', name='sync_status'),
            nullable=False,
        ),
        sa.Column('since_at', sa.DateTime(), nullable=True),
        sa.Column(
            'started_at',
            sa.DateTime(),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('fetched', sa.Integer(), nullable=True),
        sa.Column('parsed', sa.Integer(), nullable=True),
        sa.Column('skipped', sa.Integer(), nullable=True),
        sa.Column('parse_errors', sa.Integer(), nullable=True),
        sa.Column('duplicates', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    # Index para la query "último run" que la UI hace a cada rato
    op.create_index(
        'ix_sync_runs_started_at_desc',
        'sync_runs',
        [sa.text('started_at DESC')],
    )


def downgrade() -> None:
    op.drop_index('ix_sync_runs_started_at_desc', table_name='sync_runs')
    op.drop_table('sync_runs')
    sa.Enum(name='sync_status').drop(op.get_bind(), checkfirst=False)
    sa.Enum(name='sync_trigger').drop(op.get_bind(), checkfirst=False)
