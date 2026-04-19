"""Limpia emails+transacciones para forzar reprocesamiento con la lógica nueva.

Estrategia: borra todos los emails (y sus transacciones PENDING) cuyo remitente
esté en el registro de direcciones transaccionales, para que el siguiente
backfill los reprocese desde cero.

Por seguridad:
  - Las transacciones CONFIRMED no se tocan (son trabajo del usuario)
  - Los emails con transacción CONFIRMED tampoco se borran
  - Pide confirmación antes de borrar a menos que se pase --yes

Uso:
    docker compose exec api python -m app.scripts.cleanup_after_parser_fix
    docker compose exec api python -m app.scripts.cleanup_after_parser_fix --yes
"""
import argparse

from sqlalchemy import select

from app.database import SessionLocal
from app.models.email import Email
from app.models.transaction import Transaction, TxStatus
from app.parsers.base import extract_email_address
from app.parsers.senders import TRANSACTIONAL_SENDERS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="No preguntar confirmación")
    args = parser.parse_args()

    with SessionLocal() as db:
        all_emails = db.scalars(select(Email)).all()
        target_emails = [
            e for e in all_emails
            if extract_email_address(e.sender) in TRANSACTIONAL_SENDERS
        ]

        if not target_emails:
            print("No hay emails de remitentes transaccionales para resetear.")
            return

        # Identificar transacciones asociadas
        email_ids = [e.id for e in target_emails]
        txs = db.scalars(
            select(Transaction).where(Transaction.email_id.in_(email_ids))
        ).all()

        pending_txs = [t for t in txs if t.status == TxStatus.PENDING]
        confirmed_txs = [t for t in txs if t.status == TxStatus.CONFIRMED]
        confirmed_email_ids = {t.email_id for t in confirmed_txs}

        emails_to_delete = [e for e in target_emails if e.id not in confirmed_email_ids]

        print(f"Emails de remitentes transaccionales: {len(target_emails)}")
        print(f"  · A borrar (sin tx CONFIRMED): {len(emails_to_delete)}")
        print(f"  · A conservar (tienen tx CONFIRMED): {len(confirmed_email_ids)}")
        print(f"Transacciones PENDING a borrar: {len(pending_txs)}")
        print(f"Transacciones CONFIRMED conservadas: {len(confirmed_txs)}")
        print()

        if confirmed_txs:
            print("Transacciones CONFIRMED que se conservan:")
            for t in confirmed_txs[:5]:
                e = next(em for em in target_emails if em.id == t.email_id)
                print(f"  - tx#{t.id} {t.counterpart} ${t.amount:,} (email#{e.id}, {extract_email_address(e.sender)})")
            if len(confirmed_txs) > 5:
                print(f"  ... y {len(confirmed_txs) - 5} más")
            print()

        if emails_to_delete:
            print("Primeros 10 emails que se van a borrar:")
            for e in emails_to_delete[:10]:
                print(f"  - #{e.id} [{e.status.value}] {extract_email_address(e.sender):50s} | {e.subject[:50]}")
            if len(emails_to_delete) > 10:
                print(f"  ... y {len(emails_to_delete) - 10} más")
            print()

        if not args.yes:
            resp = input("¿Continuar? [y/N]: ").strip().lower()
            if resp != "y":
                print("Cancelado.")
                return

        # Borrar PENDING txs
        for t in pending_txs:
            db.delete(t)

        # Borrar emails sin txs CONFIRMED
        for e in emails_to_delete:
            db.delete(e)

        db.commit()
        print(f"✓ Eliminadas {len(pending_txs)} transacciones PENDING")
        print(f"✓ Eliminados {len(emails_to_delete)} emails")
        print()
        print("Siguiente paso:")
        print("  docker compose exec api python -m app.scripts.gmail_diagnostic --days 30")


if __name__ == "__main__":
    main()
