"""Backfill: parsea los últimos N emails de Gmail."""
import sys
from pathlib import Path

# Agregar backend al path para imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.gmail_service import get_gmail_service, fetch_new_emails
from app.services.email_processor import process_email
from app.database import SessionLocal


def main(max_results: int = 100):
    print(f"Fetching últimos {max_results} emails de Gmail...")
    service = get_gmail_service()
    emails = fetch_new_emails(service, max_results=max_results)
    print(f"Encontrados: {len(emails)} emails")

    db = SessionLocal()
    parsed = 0
    skipped = 0
    errors = 0

    try:
        for i, email_data in enumerate(emails, 1):
            sender = email_data["sender"]
            subject = email_data["subject"][:50]
            result = process_email(db, email_data)

            status = result.status.value
            if status == "parsed":
                parsed += 1
            elif status == "skipped":
                skipped += 1
            else:
                errors += 1

            print(f"  [{i}/{len(emails)}] {status.upper():8s} | {sender[:40]:40s} | {subject}")

        db.commit()
        print(f"\nResumen: {parsed} parseados, {skipped} ignorados, {errors} errores")
    except Exception as e:
        db.rollback()
        print(f"Error fatal: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    main(n)
