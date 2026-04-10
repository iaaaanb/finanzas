from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transaction import Transaction, TxType, TxStatus
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionRead
from app.services.transactions import (
    validate_expense_has_budget,
    validate_income_no_budget,
    confirm_transaction,
    handle_confirmed_update,
    handle_auto_assign_rules,
)

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionRead])
def list_transactions(
    status: TxStatus | None = None,
    type: TxType | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
    budget_period_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = select(Transaction).order_by(Transaction.date.desc(), Transaction.id.desc())
    if status is not None:
        query = query.where(Transaction.status == status)
    if type is not None:
        query = query.where(Transaction.type == type)
    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if budget_period_id is not None:
        query = query.where(Transaction.budget_period_id == budget_period_id)
    return db.scalars(query).all()


@router.get("/{tx_id}", response_model=TransactionRead)
def get_transaction(tx_id: int, db: Session = Depends(get_db)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


@router.post("", response_model=TransactionRead, status_code=201)
def create_transaction(data: TransactionCreate, db: Session = Depends(get_db)):
    validate_income_no_budget(data.type, data.budget_period_id)
    # No validamos budget obligatorio aquí porque se crea como PENDING

    tx = Transaction(
        type=data.type,
        amount=data.amount,
        date=data.date,
        counterpart=data.counterpart,
        comment=data.comment,
        account_id=data.account_id,
        category_id=data.category_id,
        budget_period_id=data.budget_period_id,
    )
    db.add(tx)

    handle_auto_assign_rules(
        db, data.counterpart, data.category_id, data.budget_period_id,
        data.remember_category, data.remember_budget,
    )

    db.commit()
    db.refresh(tx)
    return tx


@router.patch("/{tx_id}", response_model=TransactionRead)
def update_transaction(tx_id: int, data: TransactionUpdate, db: Session = Depends(get_db)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Guardar valores anteriores para recálculo
    old_amount = tx.amount
    old_account_id = tx.account_id
    old_budget_period_id = tx.budget_period_id

    # Aplicar cambios
    for field, value in data.model_dump(exclude_unset=True, exclude={"remember_category", "remember_budget"}).items():
        setattr(tx, field, value)

    validate_income_no_budget(tx.type, tx.budget_period_id)

    # Si está confirmada, recalcular saldos
    if tx.status == TxStatus.CONFIRMED:
        validate_expense_has_budget(tx.type, tx.budget_period_id)
        handle_confirmed_update(
            db, tx,
            old_amount, old_account_id, old_budget_period_id,
            tx.amount, tx.account_id, tx.budget_period_id,
        )

    handle_auto_assign_rules(
        db, tx.counterpart, tx.category_id, tx.budget_period_id,
        data.remember_category, data.remember_budget,
    )

    db.commit()
    db.refresh(tx)
    return tx


@router.post("/{tx_id}/confirm", response_model=TransactionRead)
def confirm(tx_id: int, db: Session = Depends(get_db)):
    tx = db.get(Transaction, tx_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    confirm_transaction(db, tx)
    db.commit()
    db.refresh(tx)
    return tx
