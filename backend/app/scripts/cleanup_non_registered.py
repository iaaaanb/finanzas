"""Limpia emails+transacciones de remitentes que NO están en el registro.

Caso de uso: antes de introducir TRANSACTIONAL_SENDERS, el parser aceptaba
cualquier email de ciertos dominios y creaba transacciones. Después de
agregar el registro, esos emails viejos quedaron como PARSED/PENDING con
sus transacciones asociadas, aunque el registro actual los rechazaría.

Este script lista esos stragglers y los borra (junto con sus transacciones
PENDING). Por seguridad, preserva emails con transacciones CONFIRMED.

Uso:
    # Ver qué hay sin borrar nada
    docker compose exec api python -m app.scripts.cleanup_non_registered --dry-run

    # Borrar interactivamente (pide confirmación)
    docker compose exec api python -m app.scripts.cleanup_non_registered

    # Sin preguntar
    docker compose exec api python -m app.scripts.cleanup_non_registered --yes
"""
import argparse
from collections import defaultdict

from sqlalchemy import select

from app.database import SessionLocal
from app.models.email import Email, EmailStatus
from app.models.transaction import Transaction, TxStatus
from app.parsers.base import extract_email_address
from app.parsers.senders import TRANSACTIONAL_SENDERS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="No preguntar confirmación")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar, no borrar")
    args = parser.parse_args()

    with SessionLocal() as db:
        # Traer todos los emails que NO están SKIPPED y cuyo remitente no está en el registro
        all_emails = db.scalars(
            select(Email).where(Email.status != EmailStatus.SKIPPED)
        ).all()

        stragglers = [
            e for e in all_emails
            if extract_email_address(e.sender) not in TRANSACTIONAL_SENDERS
        ]

        if not stragglers:
            print("✓ No hay stragglers. Todo limpio.")
            return

        # Agrupar por remitente para inspección
        by_sender: dict[str, list[Email]] = defaultdict(list)
        for e in stragglers:
            by_sender[extract_email_address(e.sender)].append(e)

        # Traer transacciones asociadas
        email_ids = [e.id for e in stragglers]
        txs = db.scalars(
            select(Transaction).where(Transaction.email_id.in_(email_ids))
        ).all()
        txs_by_email: dict[int, list[Transaction]] = defaultdict(list)
        for t in txs:
            txs_by_email[t.email_id].append(t)

        confirmed_txs = [t for t in txs if t.status == TxStatus.CONFIRMED]
        pending_txs = [t for t in txs if t.status == TxStatus.PENDING]
        confirmed_email_ids = {t.email_id for t in confirmed_txs}

        emails_to_delete = [e for e in stragglers if e.id not in confirmed_email_ids]
        emails_to_keep = [e for e in stragglers if e.id in confirmed_email_ids]

        # Resumen por remitente
        print(f"Stragglers: {len(stragglers)} email(s) de {len(by_sender)} remitente(s) no registrados")
        print()
        print(f"{'PARSED':>7} {'PENDING':>8} {'TXs':>5}  REMITENTE")
        print("-" * 80)
        for addr, emails in sorted(by_sender.items(), key=lambda kv: -len(kv[1])):
            parsed = sum(1 for e in emails if e.status == EmailStatus.PARSED)
            pending = sum(1 for e in emails if e.status == EmailStatus.PENDING)
            tx_count = sum(len(txs_by_email.get(e.id, [])) for e in emails)
            print(f"{parsed:>7} {pending:>8} {tx_count:>5}  {addr}")
        print()

        print(f"Total emails a borrar: {len(emails_to_delete)}")
        print(f"Total emails conservados (tienen tx CONFIRMED): {len(emails_to_keep)}")
        print(f"Transacciones PENDING a borrar: {len(pending_txs)}")
        print(f"Transacciones CONFIRMED conservadas: {len(confirmed_txs)}")
        print()

        if confirmed_txs:
            print("Transacciones CONFIRMED que se conservan:")
            for t in confirmed_txs[:10]:
                e = next(em for em in stragglers if em.id == t.email_id)
                addr = extract_email_address(e.sender)
                print(f"  - tx#{t.id} {t.type.value} ${t.amount:,} {t.counterpart} (email#{e.id}, {addr})")
            if len(confirmed_txs) > 10:
                print(f"  ... y {len(confirmed_txs) - 10} más")
            print()

        if pending_txs:
            print("Primeras 10 transacciones PENDING que se borrarán:")
            for t in pending_txs[:10]:
                e = next(em for em in stragglers if em.id == t.email_id)
                addr = extract_email_address(e.sender)
                print(f"  - tx#{t.id} {t.type.value} ${t.amount:,} {t.counterpart} (email#{e.id}, {addr})")
            if len(pending_txs) > 10:
                print(f"  ... y {len(pending_txs) - 10} más")
            print()

        if args.dry_run:
            print("[--dry-run] No se borra nada.")
            return

        if not args.yes:
            resp = input("¿Continuar? [y/N]: ").strip().lower()
            if resp != "y":
                print("Cancelado.")
                return

        for t in pending_txs:
            db.delete(t)
        for e in emails_to_delete:
            db.delete(e)

        db.commit()
        print(f"✓ Eliminadas {len(pending_txs)} transacciones PENDING")
        print(f"✓ Eliminados {len(emails_to_delete)} emails")


if __name__ == "__main__":
    main()
