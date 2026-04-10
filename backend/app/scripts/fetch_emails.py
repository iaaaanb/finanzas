"""
Ejecutar como cron:
    docker compose exec api python -m app.scripts.fetch_emails
"""
from sqlalchemy import select, func

from app.database import SessionLocal
from app.models.email import Email
from app.services.gmail import get_gmail_service, fetch_new_emails
from app.services.email_processor import process_email


def main():
    service = get_gmail_service()

    with SessionLocal() as db:
        # Obtener timestamp del último email procesado
        last_ts = db.scalar(select(func.max(Email.received_at)))
        after_timestamp = None
        if last_ts:
            after_timestamp = int(last_ts.timestamp())

        print(f"Buscando emails después de {last_ts or 'siempre'}...")
        raw_emails = fetch_new_emails(service, after_timestamp=after_timestamp)
        print(f"Encontrados: {len(raw_emails)}")

        for email_data in raw_emails:
            email = process_email(db, email_data)
            print(f"  [{email.status.value}] {email.subject}")

        db.commit()
        print("Listo.")


if __name__ == "__main__":
    main()
