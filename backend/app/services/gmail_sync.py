"""Sync con Gmail. Único punto de entrada para fetching + processing.

Lo llaman:
  - El endpoint POST /api/sync/incremental (UI: botón "Sincronizar ahora")
  - El endpoint POST /api/sync/backfill (UI: backfill desde fecha)
  - app.scripts.run_sync (cron en la droplet, ejecutado por systemd timer)

Mantiene un row en sync_runs por cada ejecución, con contadores y status.
Implementa concurrency guard para evitar dobles fetches si cron y UI coinciden.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.email import Email
from app.models.sync_run import SyncRun, SyncStatus, SyncTrigger
from app.services.gmail import get_gmail_service
from app.services.email_processor import process_email


# Margen de seguridad para clock skew entre nuestra DB, Docker y Gmail.
# El último email registrado se vuelve a buscar (será dedup-eado por
# gmail_message_id), pero así no perdemos nada por diferencias de segundos.
INCREMENTAL_OVERLAP = timedelta(minutes=1)

# Si hay un run en RUNNING más viejo que esto, asumimos que crasheó y permitimos
# arrancar uno nuevo. Sin esto, un crash del proceso (OOM, restart, etc.) dejaría
# bloqueado el sync para siempre.
STALE_RUN_THRESHOLD = timedelta(minutes=30)


class SyncAlreadyRunningError(Exception):
    """Hay otro sync corriendo. Lleva el SyncRun in-progress en .run."""
    def __init__(self, run: SyncRun):
        self.run = run
        super().__init__(f"Sync run #{run.id} ya está en progreso")


def get_incremental_since(db: Session) -> datetime:
    """Calcula desde cuándo pedir emails para un sync incremental.

    Es el `received_at` del último email guardado, menos el overlap.
    Si la DB está vacía, vuelve 30 días para atrás (primera corrida).
    """
    last = db.scalar(select(Email.received_at).order_by(Email.received_at.desc()).limit(1))
    if last is None:
        return datetime.now(timezone.utc) - timedelta(days=30)
    # Postgres devuelve datetime naive aunque guardemos UTC. Lo marcamos.
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return last - INCREMENTAL_OVERLAP


def _check_no_active_run(db: Session) -> Optional[SyncRun]:
    """Retorna el SyncRun activo si lo hay, None si está libre."""
    cutoff = datetime.now(timezone.utc) - STALE_RUN_THRESHOLD
    active = db.scalars(
        select(SyncRun)
        .where(SyncRun.status == SyncStatus.RUNNING)
        .where(SyncRun.started_at >= cutoff)
        .order_by(SyncRun.started_at.desc())
    ).first()
    return active


def _fetch_emails_after(service, after_dt: datetime) -> list[dict]:
    """Trae todos los emails después de after_dt, con paginación completa.

    Adaptado de gmail_diagnostic.fetch_all_after pero importable y sin prints.
    """
    from app.services.gmail import _extract_html

    after_ts = int(after_dt.timestamp())
    query = f"after:{after_ts}"
    emails: list[dict] = []
    page_token = None

    while True:
        kwargs = {"userId": "me", "q": query, "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = service.users().messages().list(**kwargs).execute()
        msgs = resp.get("messages", [])

        for msg_meta in msgs:
            msg = service.users().messages().get(
                userId="me", id=msg_meta["id"], format="full",
            ).execute()
            headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
            internal_date = int(msg.get("internalDate", 0))
            received_at = datetime.fromtimestamp(internal_date / 1000, tz=timezone.utc)
            body_html = _extract_html(msg["payload"])

            emails.append({
                "gmail_message_id": msg["id"],
                "sender": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "body_html": body_html or "",
                "received_at": received_at,
            })

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return emails


def run_sync(
    trigger: SyncTrigger,
    since_at: Optional[datetime] = None,
) -> SyncRun:
    """Ejecuta un sync completo. Bloquea hasta terminar.

    Args:
        trigger: quién está disparando el sync (cron, ui-incremental, ui-backfill).
        since_at: desde cuándo pedir. Si None, modo incremental (calcula automáticamente).

    Returns:
        El SyncRun finalizado (con status SUCCESS o FAILED) y contadores poblados.

    Raises:
        SyncAlreadyRunningError: si hay otro run RUNNING (no stale).

    Estrategia de sesiones: una sesión separada por cada email procesado, igual
    que gmail_diagnostic.backfill. Esto aísla errores de parseo y duplicados.
    El SyncRun en sí usa sesiones cortas para crear/actualizar la fila.
    """
    # ---- Reservar el slot ----
    with SessionLocal() as db:
        active = _check_no_active_run(db)
        if active is not None:
            raise SyncAlreadyRunningError(active)

        run = SyncRun(
            trigger=trigger,
            status=SyncStatus.RUNNING,
            since_at=since_at,
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id

    # ---- Resolver since_at si vino vacío (modo incremental) ----
    if since_at is None:
        with SessionLocal() as db:
            since_at = get_incremental_since(db)
        # También guardarlo en el run para mostrarlo en la UI
        with SessionLocal() as db:
            run = db.get(SyncRun, run_id)
            run.since_at = since_at
            db.commit()

    # ---- Fetch + process ----
    fetched = parsed = skipped = parse_errors = duplicates = 0
    error_message: Optional[str] = None
    seen_gmids: set[str] = set()

    try:
        service = get_gmail_service()
        all_emails = _fetch_emails_after(service, since_at)
        fetched = len(all_emails)

        for email_data in all_emails:
            gmid = email_data["gmail_message_id"]
            # Dedup en memoria como primera línea de defensa: la paginación
            # de Gmail a veces retorna el mismo mensaje en páginas distintas.
            if gmid in seen_gmids:
                duplicates += 1
                continue
            seen_gmids.add(gmid)

            try:
                with SessionLocal() as db:
                    email = process_email(db, email_data)
                    db.commit()
                    if email.status.value == "PARSED":
                        parsed += 1
                    elif email.status.value == "SKIPPED":
                        skipped += 1
                    else:  # PENDING = parser falló
                        parse_errors += 1
            except IntegrityError:
                # gmail_message_id duplicado a nivel DB (race con run anterior
                # solapado, por ejemplo). No es un error real.
                duplicates += 1

        final_status = SyncStatus.SUCCESS

    except Exception as e:
        # Error fatal (auth, red, Gmail caído, etc). Lo guardamos con el run
        # como FAILED. Cualquier email que haya alcanzado a procesarse antes
        # del crash queda guardado: cada uno commitea por separado.
        final_status = SyncStatus.FAILED
        error_message = f"{type(e).__name__}: {e}"[:1000]

    # ---- Cerrar el run con resultado ----
    with SessionLocal() as db:
        run = db.get(SyncRun, run_id)
        run.status = final_status
        run.finished_at = datetime.now(timezone.utc)
        run.fetched = fetched
        run.parsed = parsed
        run.skipped = skipped
        run.parse_errors = parse_errors
        run.duplicates = duplicates
        run.error_message = error_message
        db.commit()
        db.refresh(run)
        # Detach para que sea seguro retornarlo después de cerrar la sesión
        db.expunge(run)
        return run
