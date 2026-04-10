from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget
from app.models.budget_period import BudgetPeriod
from app.models.transaction import Transaction, TxType, TxStatus
from app.models.auto_assign_rule import AutoAssignRule


def validate_expense_has_budget(tx_type: TxType, budget_period_id: int | None):
    """Los gastos deben tener presupuesto asignado."""
    if tx_type == TxType.EXPENSE and budget_period_id is None:
        raise HTTPException(
            status_code=422,
            detail="Expenses must have a budget_period_id",
        )


def validate_income_no_budget(tx_type: TxType, budget_period_id: int | None):
    """Los ingresos no se asignan a presupuesto."""
    if tx_type == TxType.INCOME and budget_period_id is not None:
        raise HTTPException(
            status_code=422,
            detail="Income transactions cannot have a budget_period_id",
        )


def confirm_transaction(db: Session, transaction: Transaction):
    """Confirma una transacción y ajusta saldos."""
    if transaction.status == TxStatus.CONFIRMED:
        raise HTTPException(status_code=400, detail="Transaction already confirmed")

    validate_expense_has_budget(transaction.type, transaction.budget_period_id)

    account = db.get(Account, transaction.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if transaction.type == TxType.EXPENSE:
        account.balance -= transaction.amount
        period = db.get(BudgetPeriod, transaction.budget_period_id)
        if not period:
            raise HTTPException(status_code=404, detail="Budget period not found")
        period.balance -= transaction.amount
    else:
        account.balance += transaction.amount

    transaction.status = TxStatus.CONFIRMED


def handle_confirmed_update(
    db: Session,
    transaction: Transaction,
    old_amount: int,
    old_account_id: int,
    old_budget_period_id: int | None,
    new_amount: int,
    new_account_id: int,
    new_budget_period_id: int | None,
):
    """Recalcula saldos cuando se edita una transacción ya confirmada."""

    # Revertir efecto anterior en cuenta
    old_account = db.get(Account, old_account_id)
    if transaction.type == TxType.EXPENSE:
        old_account.balance += old_amount
    else:
        old_account.balance -= old_amount

    # Revertir efecto anterior en período de presupuesto
    if old_budget_period_id is not None:
        old_period = db.get(BudgetPeriod, old_budget_period_id)
        if old_period:
            old_period.balance += old_amount

    # Aplicar nuevo efecto en cuenta
    new_account = db.get(Account, new_account_id)
    if not new_account:
        raise HTTPException(status_code=404, detail="Account not found")
    if transaction.type == TxType.EXPENSE:
        new_account.balance -= new_amount
    else:
        new_account.balance += new_amount

    # Aplicar nuevo efecto en período de presupuesto
    if new_budget_period_id is not None:
        new_period = db.get(BudgetPeriod, new_budget_period_id)
        if not new_period:
            raise HTTPException(status_code=404, detail="Budget period not found")
        new_period.balance -= new_amount


def handle_auto_assign_rules(
    db: Session,
    counterpart: str,
    category_id: int | None,
    budget_period_id: int | None,
    remember_category: bool,
    remember_budget: bool,
):
    """Crea o actualiza reglas de auto-assign según los checkboxes 'Recordar'."""
    if not remember_category and not remember_budget:
        return

    # Obtener el budget_id desde el período
    budget_id = None
    if budget_period_id is not None and remember_budget:
        period = db.get(BudgetPeriod, budget_period_id)
        if period:
            budget_id = period.budget_id

    rule = db.scalars(
        select(AutoAssignRule).where(AutoAssignRule.counterpart == counterpart)
    ).first()

    if rule:
        if remember_category:
            rule.category_id = category_id
        if remember_budget:
            rule.budget_id = budget_id
    else:
        rule = AutoAssignRule(
            counterpart=counterpart,
            category_id=category_id if remember_category else None,
            budget_id=budget_id if remember_budget else None,
        )
        db.add(rule)
