"""Backfill: parsea los últimos N emails de Gmail (por cantidad, no por fecha).

Para backfill por rango de fechas, ver gmail_diagnostic.py.
"""
import sys

from app.services.gmail import get_gmail_service, fetch_new_emails
from app.services.email_processor import process_email
from app.database import SessionLocal


def main(max_results: int = 100):
    print(f"Fetching últimos {max_results} emails de Gmail...")
    service = get_gmail_service()
    emails = fetch_new_emails(service, max_results=max_results)
    print(f"Encontrados: {len(emails)} emails")

    parsed = 0
    skipped = 0
    errors = 0

    with SessionLocal() as db:
        try:
            for i, email_data in enumerate(emails, 1):
                sender = email_data["sender"][:40]
                subject = email_data["subject"][:50]
                result = process_email(db, email_data)

                status = result.status.value  # "PARSED" | "PENDING" | "SKIPPED"
                if status == "PARSED":
                    parsed += 1
                elif status == "SKIPPED":
                    skipped += 1
                else:  # PENDING = error de parseo
                    errors += 1

                print(f"  [{i}/{len(emails)}] {status:8s} | {sender:40s} | {subject}")

            db.commit()
            print(f"\nResumen: {parsed} parseados, {skipped} sin parser, {errors} errores")
        except Exception as e:
            db.rollback()
            print(f"Error fatal: {e}")
            raise


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    main(n)
