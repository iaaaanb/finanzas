import enum
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, DateTime, Date, Enum, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SyncStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class SyncTrigger(str, enum.Enum):
    """Quién disparó el sync. Útil para distinguir cron de UI en el historial."""
    CRON = "CRON"
    UI_INCREMENTAL = "UI_INCREMENTAL"
    UI_BACKFILL = "UI_BACKFILL"


class SyncRun(Base):
    """Registro de cada ejecución de sync con Gmail.

    Sirve dos propósitos:
      1. Mostrar en la UI "última actualización" + historial de runs.
      2. Concurrency guard: antes de lanzar un sync nuevo verificamos que no haya
         otro en estado RUNNING en los últimos 30 min (para evitar dobles fetches
         si cron y UI coinciden, sin quedar trabados por runs zombi).
    """
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    trigger: Mapped[SyncTrigger] = mapped_column(
        Enum(SyncTrigger, name="sync_trigger"), nullable=False
    )
    status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus, name="sync_status"), nullable=False, default=SyncStatus.RUNNING
    )
    # Fecha (inclusive) desde la que se pidieron los emails. Para incremental
    # es el momento del último email procesado; para backfill es la fecha que
    # eligió el usuario.
    since_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Contadores del run. Nullables porque están vacíos mientras status=RUNNING.
    fetched: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parsed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    skipped: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parse_errors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duplicates: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Si status=FAILED guardamos el mensaje de error acá (no el traceback completo,
    # solo type+message para mostrar en la UI).
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
