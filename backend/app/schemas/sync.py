from datetime import date as date_type, datetime
from typing import Optional

from pydantic import BaseModel

from app.models.sync_run import SyncStatus, SyncTrigger


class SyncRunRead(BaseModel):
    id: int
    trigger: SyncTrigger
    status: SyncStatus
    since_at: Optional[datetime]
    started_at: datetime
    finished_at: Optional[datetime]
    fetched: Optional[int]
    parsed: Optional[int]
    skipped: Optional[int]
    parse_errors: Optional[int]
    duplicates: Optional[int]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class SyncStatusResponse(BaseModel):
    """Lo que GET /api/sync/status devuelve a la UI."""
    last_run: Optional[SyncRunRead]
    active_run: Optional[SyncRunRead]  # Si hay uno RUNNING ahora


class BackfillRequest(BaseModel):
    """POST /api/sync/backfill — backfill desde una fecha (interpretada como
    medianoche local del usuario, convertida a UTC en el handler)."""
    since_date: date_type
