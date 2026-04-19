"""
Diagnóstico y backfill de Gmail.

Pasos:
  1. Verifica que el token sea válido y que podamos autenticarnos.
  2. Muestra perfil (email + total de mensajes) como prueba de conectividad.
  3. Lista los últimos N mensajes crudos (sin filtro) para confirmar lectura.
  4. Hace backfill de los últimos `days` días, procesando cada email.

Uso:
    docker compose exec api python -m app.scripts.gmail_diagnostic
    docker compose exec api python -m app.scripts.gmail_diagnostic --days 30
    docker compose exec api python -m app.scripts.gmail_diagnostic --test-only
"""
import argparse
import sys
import traceback
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.services.gmail import get_gmail_service, fetch_new_emails
from app.services.email_processor import process_email


def test_auth():
    """Paso 1+2: autenticación y perfil."""
    print("=" * 60)
    print("PASO 1: Autenticación con Gmail")
    print("=" * 60)
    try:
        service = get_gmail_service()
        print("✓ Token cargado correctamente")
    except FileNotFoundError as e:
        print(f"✗ Archivo de token/credenciales no encontrado: {e}")
        print("  → Revisar que /app/credentials esté montado con gmail_token.json")
        return None
    except Exception as e:
        print(f"✗ Fallo autenticando: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None

    print()
    print("=" * 60)
    print("PASO 2: Obtener perfil (prueba de conectividad)")
    print("=" * 60)
    try:
        profile = service.users().getProfile(userId="me").execute()
        print(f"✓ Email: {profile['emailAddress']}")
        print(f"✓ Total mensajes en cuenta: {profile['messagesTotal']}")
        print(f"✓ Total threads: {profile['threadsTotal']}")
    except Exception as e:
        print(f"✗ Fallo llamando a getProfile: {type(e).__name__}: {e}")
        traceback.print_exc()
        return None

    return service


def test_list_recent(service, n=5):
    """Paso 3: listar los últimos N mensajes sin filtro."""
    print()
    print("=" * 60)
    print(f"PASO 3: Listar últimos {n} mensajes (sin filtro)")
    print("=" * 60)
    try:
        r = service.users().messages().list(userId="me", maxResults=n).execute()
        messages = r.get("messages", [])
        if not messages:
            print("⚠ No se devolvieron mensajes. ¿Cuenta vacía?")
            return False

        print(f"✓ Devolvió {len(messages)} mensaje(s). IDs:")
        for m in messages:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()
            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            print(f"  · {m['id']}")
            print(f"      From:    {headers.get('From', '(no from)')[:80]}")
            print(f"      Subject: {headers.get('Subject', '(no subject)')[:80]}")
            print(f"      Date:    {headers.get('Date', '(no date)')}")
        return True
    except Exception as e:
        print(f"✗ Fallo listando mensajes: {type(e).__name__}: {e}")
        traceback.print_exc()
        return False


def backfill(service, days: int):
    """Paso 4: backfill de últimos N días.

    Estrategia: una sesión por email. Si Gmail devuelve el mismo gmail_message_id
    dos veces (lo cual ocurre en backfills largos por temas de paginación),
    la segunda inserción falla con IntegrityError y se ignora silenciosamente.
    Si un email individual falla por otra razón, lo registramos y seguimos
    con los demás en lugar de abortar todo el backfill.
    """
    print()
    print("=" * 60)
    print(f"PASO 4: Backfill últimos {days} día(s)")
    print("=" * 60)

    after_dt = datetime.now(timezone.utc) - timedelta(days=days)
    after_ts = int(after_dt.timestamp())
    print(f"Buscando emails después de: {after_dt.isoformat()} (ts={after_ts})")

    try:
        all_emails = fetch_all_after(service, after_ts)
    except Exception as e:
        print(f"✗ Fallo fetching: {type(e).__name__}: {e}")
        traceback.print_exc()
        return

    print(f"✓ Encontrados {len(all_emails)} email(s)")
    if not all_emails:
        print("  (nada que procesar)")
        return

    parsed = 0
    skipped = 0
    errors = 0
    dup = 0
    fatal = 0

    # Track gmail_message_ids vistos en este run para dedup en memoria,
    # como primera línea de defensa antes de ir a la DB
    seen_in_run: set[str] = set()

    for i, email_data in enumerate(all_emails, 1):
        sender = email_data["sender"][:40]
        subject = email_data["subject"][:50]
        gmid = email_data["gmail_message_id"]

        if gmid in seen_in_run:
            dup += 1
            print(f"  [{i}/{len(all_emails)}] DUP-MEM  | {sender:40s} | {subject}")
            continue
        seen_in_run.add(gmid)

        # Sesión separada por email = una commit por email = aislamiento total de errores
        try:
            with SessionLocal() as db:
                try:
                    email = process_email(db, email_data)
                    db.commit()
                    status = email.status.value
                    if status == "PARSED":
                        parsed += 1
                    elif status == "SKIPPED":
                        skipped += 1
                    else:  # PENDING = error de parseo
                        errors += 1
                    print(f"  [{i}/{len(all_emails)}] {status:8s} | {sender:40s} | {subject}")
                except IntegrityError as e:
                    db.rollback()
                    # Casi siempre: gmail_message_id duplicado por race con paginación.
                    # Si no es eso, lo logueamos pero no abortamos.
                    dup += 1
                    msg = str(e.orig)[:100] if e.orig else str(e)[:100]
                    print(f"  [{i}/{len(all_emails)}] DUP-DB   | {sender:40s} | {subject}  ({msg})")
                except Exception as e:
                    db.rollback()
                    fatal += 1
                    print(f"  [{i}/{len(all_emails)}] FATAL    | {sender:40s} | {subject}")
                    print(f"      → {type(e).__name__}: {e}")
        except Exception as e:
            fatal += 1
            print(f"  [{i}/{len(all_emails)}] CONN-ERR | {type(e).__name__}: {e}")

    print()
    print("-" * 60)
    print(f"Resumen: {parsed} parseados · {skipped} sin parser · "
          f"{errors} errores parseo · {dup} duplicados · {fatal} errores fatales")
    print("-" * 60)


def fetch_all_after(service, after_timestamp: int) -> list[dict]:
    """Como fetch_new_emails pero con paginación completa."""
    from datetime import datetime, timezone
    from app.services.gmail import _extract_html

    query = f"after:{after_timestamp}"
    emails = []
    page_token = None
    page = 0

    while True:
        page += 1
        kwargs = {"userId": "me", "q": query, "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = service.users().messages().list(**kwargs).execute()
        msgs = resp.get("messages", [])
        print(f"  · Página {page}: {len(msgs)} mensaje(s)")

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30,
                        help="Días hacia atrás para backfill (default 30)")
    parser.add_argument("--test-only", action="store_true",
                        help="Solo ejecutar pasos 1-3, no hacer backfill")
    parser.add_argument("--list-n", type=int, default=5,
                        help="Cuántos mensajes listar en paso 3 (default 5)")
    args = parser.parse_args()

    service = test_auth()
    if service is None:
        sys.exit(1)

    ok = test_list_recent(service, n=args.list_n)
    if not ok:
        sys.exit(1)

    if args.test_only:
        print("\n[--test-only] Terminando sin backfill.")
        return

    backfill(service, days=args.days)


if __name__ == "__main__":
    main()
