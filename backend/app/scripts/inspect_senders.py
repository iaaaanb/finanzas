"""Muestra distribución de remitentes agrupados por status.

Uso:
    docker compose exec api python -m app.scripts.inspect_senders
"""
from collections import Counter, defaultdict

from sqlalchemy import select

from app.database import SessionLocal
from app.models.email import Email, EmailStatus
from app.models.transaction import Transaction


def main():
    with SessionLocal() as db:
        emails = db.scalars(select(Email)).all()

        by_sender = defaultdict(lambda: {"PARSED": 0, "PENDING": 0, "SKIPPED": 0})
        for e in emails:
            by_sender[e.sender][e.status.value] += 1

        # Orden: los que generaron transacciones PARSED primero, luego por total
        rows = sorted(
            by_sender.items(),
            key=lambda kv: (-kv[1]["PARSED"], -sum(kv[1].values())),
        )

        print(f"Total emails: {len(emails)}")
        print(f"Remitentes únicos: {len(rows)}")
        print()
        print(f"{'PARSED':>8} {'PENDING':>8} {'SKIPPED':>8}  SENDER")
        print("-" * 80)
        for sender, counts in rows:
            print(f"{counts['PARSED']:>8} {counts['PENDING']:>8} {counts['SKIPPED']:>8}  {sender[:70]}")


if __name__ == "__main__":
    main()
