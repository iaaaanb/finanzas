"""
Cierra períodos de presupuesto vencidos y crea los siguientes.

Ejecutar como cron diario a medianoche:
    docker compose exec api python -m app.scripts.close_periods
"""
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.database import SessionLocal
from app.models.budget import Budget
from app.models.budget_period import BudgetPeriod
from app.services.budget_periods import calculate_next_period_dates


def main():
    today = date.today()
    print(f"Revisando períodos vencidos (hoy: {today})...")

    with SessionLocal() as db:
        # Buscar períodos activos cuya fecha de fin ya pasó
        active_periods = db.scalars(
            select(BudgetPeriod).where(
                BudgetPeriod.closed_at.is_(None),
                BudgetPeriod.period_end < today,
            )
        ).all()

        if not active_periods:
            print("No hay períodos vencidos.")
            return

        for period in active_periods:
            budget = db.get(Budget, period.budget_id)
            print(f"  Cerrando: {budget.name} ({period.period_start} → {period.period_end})")

            # Cerrar período actual
            period.final_balance = period.balance
            period.closed_at = datetime.now(timezone.utc)

            # Crear siguiente período
            next_start, next_end = calculate_next_period_dates(
                budget.type, period.period_end
            )
            new_period = BudgetPeriod(
                budget_id=budget.id,
                period_start=next_start,
                period_end=next_end,
                starting_amount=budget.amount,
                balance=budget.amount,
            )
            db.add(new_period)
            print(f"  Nuevo período: {next_start} → {next_end} (${budget.amount:,})")

        db.commit()
        print(f"Listo. {len(active_periods)} período(s) cerrado(s).")


if __name__ == "__main__":
    main()
