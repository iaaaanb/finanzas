from datetime import datetime, time, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.sync_run import SyncRun, SyncStatus, SyncTrigger
from app.schemas.sync import BackfillRequest, SyncRunRead, SyncStatusResponse
from app.services.gmail_sync import (
    SyncAlreadyRunningError,
    run_sync,
)

router = APIRouter(prefix="/api/sync", tags=["sync"])


# Chile (UTC-3 / UTC-4 según horario de verano). El backfill se interpreta
# como "desde las 00:00 hora chilena del día elegido". Hardcodeamos UTC-3
# porque (a) Chile eliminó horario de verano en la mayoría del país, (b) un
# día de margen no afecta porque ya hay un overlap explícito en el sync.
SANTIAGO_TZ = timezone(timedelta(hours=-3))


@router.get("/status", response_model=SyncStatusResponse)
def get_status(db: Session = Depends(get_db)):
    """Devuelve el último run y, si hay uno corriendo ahora, también ese."""
    last_run = db.scalars(
        select(SyncRun).order_by(SyncRun.started_at.desc()).limit(1)
    ).first()

    # Active = RUNNING y arrancado dentro de los últimos 30 min (más viejo se
    # considera zombi y permitimos arrancar otro encima).
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    active_run = db.scalars(
        select(SyncRun)
        .where(SyncRun.status == SyncStatus.RUNNING)
        .where(SyncRun.started_at >= cutoff)
        .order_by(SyncRun.started_at.desc())
        .limit(1)
    ).first()

    return SyncStatusResponse(
        last_run=SyncRunRead.model_validate(last_run) if last_run else None,
        active_run=SyncRunRead.model_validate(active_run) if active_run else None,
    )


@router.get("/runs", response_model=list[SyncRunRead])
def list_runs(limit: int = 20, db: Session = Depends(get_db)):
    """Historial reciente de runs para mostrar en la UI."""
    runs = db.scalars(
        select(SyncRun).order_by(SyncRun.started_at.desc()).limit(limit)
    ).all()
    return runs


@router.post("/incremental", response_model=SyncRunRead)
def trigger_incremental():
    """Trae emails nuevos desde el último que tenemos. Bloquea hasta terminar.

    El frontend debería mostrar un spinner mientras dura. Para mailboxes de
    pocos días es de segundos; para backlogs grandes puede tardar minutos.
    """
    try:
        run = run_sync(trigger=SyncTrigger.UI_INCREMENTAL, since_at=None)
    except SyncAlreadyRunningError as e:
        # 409 Conflict: hay otro sync corriendo. Le devolvemos al cliente cuál
        # para que pueda mostrar info útil.
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Ya hay un sync en progreso",
                "active_run": SyncRunRead.model_validate(e.run).model_dump(mode="json"),
            },
        )
    return run


@router.post("/backfill", response_model=SyncRunRead)
def trigger_backfill(data: BackfillRequest):
    """Backfill desde la fecha elegida (00:00 hora Chile) hasta ahora.

    Esto puede traer cientos de emails en un solo run. Bloquea hasta terminar.
    """
    # 00:00 hora Chile → UTC
    since_dt_local = datetime.combine(data.since_date, time.min, tzinfo=SANTIAGO_TZ)
    since_dt_utc = since_dt_local.astimezone(timezone.utc)

    if since_dt_utc > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="La fecha de backfill no puede ser en el futuro",
        )

    try:
        run = run_sync(trigger=SyncTrigger.UI_BACKFILL, since_at=since_dt_utc)
    except SyncAlreadyRunningError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Ya hay un sync en progreso",
                "active_run": SyncRunRead.model_validate(e.run).model_dump(mode="json"),
            },
        )
    return run
