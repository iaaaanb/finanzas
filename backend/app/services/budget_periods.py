from datetime import date, timedelta
from calendar import monthrange

from app.models.budget import BudgetType


def calculate_period_dates(budget_type: BudgetType, ref_date: date) -> tuple[date, date]:
    """Calcula start y end del período que contiene ref_date."""

    if budget_type == BudgetType.L_V:
        # Lunes de esta semana hasta viernes
        start = ref_date - timedelta(days=ref_date.weekday())  # weekday 0=lunes
        end = start + timedelta(days=4)
        return start, end

    if budget_type == BudgetType.V_D:
        # Viernes hasta domingo
        days_since_friday = (ref_date.weekday() - 4) % 7
        start = ref_date - timedelta(days=days_since_friday)
        end = start + timedelta(days=2)
        return start, end

    if budget_type == BudgetType.L_D:
        # Lunes a domingo
        start = ref_date - timedelta(days=ref_date.weekday())
        end = start + timedelta(days=6)
        return start, end

    if budget_type == BudgetType.MONTHLY:
        start = ref_date.replace(day=1)
        last_day = monthrange(ref_date.year, ref_date.month)[1]
        end = ref_date.replace(day=last_day)
        return start, end

    raise ValueError(f"Unknown budget type: {budget_type}")


def calculate_next_period_dates(budget_type: BudgetType, prev_end: date) -> tuple[date, date]:
    """Calcula start y end del período siguiente al que terminó en prev_end."""
    next_start = prev_end + timedelta(days=1)
    return calculate_period_dates(budget_type, next_start)
