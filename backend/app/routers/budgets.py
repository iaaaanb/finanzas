from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.budget import Budget
from app.models.budget_period import BudgetPeriod
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetRead, BudgetPeriodRead
from app.services.budget_periods import calculate_period_dates

router = APIRouter(prefix="/api/budgets", tags=["budgets"])


def _get_active_period(db: Session, budget_id: int) -> BudgetPeriod | None:
    return db.scalars(
        select(BudgetPeriod)
        .where(BudgetPeriod.budget_id == budget_id, BudgetPeriod.closed_at.is_(None))
    ).first()


def _to_read(budget: Budget, active_period: BudgetPeriod | None) -> BudgetRead:
    return BudgetRead(
        id=budget.id,
        name=budget.name,
        type=budget.type,
        color=budget.color,
        amount=budget.amount,
        created_at=budget.created_at,
        active_period=BudgetPeriodRead.model_validate(active_period) if active_period else None,
    )


@router.get("", response_model=list[BudgetRead])
def list_budgets(db: Session = Depends(get_db)):
    budgets = db.scalars(select(Budget).order_by(Budget.id)).all()
    result = []
    for b in budgets:
        period = _get_active_period(db, b.id)
        result.append(_to_read(b, period))
    return result


@router.get("/{budget_id}", response_model=BudgetRead)
def get_budget(budget_id: int, db: Session = Depends(get_db)):
    budget = db.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    period = _get_active_period(db, budget.id)
    return _to_read(budget, period)


@router.post("", response_model=BudgetRead, status_code=201)
def create_budget(data: BudgetCreate, db: Session = Depends(get_db)):
    budget = Budget(**data.model_dump())
    db.add(budget)
    db.flush()

    # Crear primer período activo
    start, end = calculate_period_dates(budget.type, date.today())
    period = BudgetPeriod(
        budget_id=budget.id,
        period_start=start,
        period_end=end,
        starting_amount=budget.amount,
        balance=budget.amount,
    )
    db.add(period)
    db.commit()
    db.refresh(budget)
    db.refresh(period)
    return _to_read(budget, period)


@router.patch("/{budget_id}", response_model=BudgetRead)
def update_budget(budget_id: int, data: BudgetUpdate, db: Session = Depends(get_db)):
    budget = db.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget)
    period = _get_active_period(db, budget.id)
    return _to_read(budget, period)


@router.get("/{budget_id}/periods", response_model=list[BudgetPeriodRead])
def list_budget_periods(budget_id: int, db: Session = Depends(get_db)):
    budget = db.get(Budget, budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    periods = db.scalars(
        select(BudgetPeriod)
        .where(BudgetPeriod.budget_id == budget_id)
        .order_by(BudgetPeriod.period_start.desc())
    ).all()
    return periods
