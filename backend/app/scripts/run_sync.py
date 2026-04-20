"""Sync incremental disparado por cron / systemd timer.

Llama a la misma función `run_sync` que usa la UI, pero con trigger=CRON.
Idempotente y safe-to-run-frequently: el concurrency guard evita dobles fetches
si por alguna razón se solapa con un trigger manual.

Uso (en la droplet, instalado como systemd timer):
    docker compose -f docker-compose.prod.yml exec -T api \\
        python -m app.scripts.run_sync

El -T es importante en cron: sin TTY allocation.

Exit codes:
    0  - sync exitoso
    0  - había otro sync corriendo (no es un error, simplemente saltamos)
    1  - sync falló (la fila SyncRun queda con status=FAILED y error_message)
"""
import sys

from app.models.sync_run import SyncTrigger
from app.services.gmail_sync import SyncAlreadyRunningError, run_sync


def main():
    try:
        run = run_sync(trigger=SyncTrigger.CRON, since_at=None)
    except SyncAlreadyRunningError as e:
        print(f"[skip] Sync run #{e.run.id} ya está en progreso.")
        # Exit 0: no es un error, es comportamiento esperado del concurrency guard
        sys.exit(0)

    if run.status.value == "FAILED":
        print(
            f"[fail] Run #{run.id}: {run.error_message}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(
        f"[ok] Run #{run.id}: "
        f"fetched={run.fetched} parsed={run.parsed} "
        f"skipped={run.skipped} errors={run.parse_errors} dup={run.duplicates}"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
