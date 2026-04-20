from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auto_assign_rule import AutoAssignRule
from app.models.transaction import Transaction, TxStatus
from app.schemas.auto_assign_rule import (
    AutoAssignRuleCreate,
    AutoAssignRuleUpdate,
    AutoAssignRuleRead,
    EnableAutoConfirmResponse,
)
from app.services.transactions import confirm_transaction

router = APIRouter(prefix="/api/auto-assign-rules", tags=["auto-assign-rules"])


@router.get("", response_model=list[AutoAssignRuleRead])
def list_rules(db: Session = Depends(get_db)):
    return db.scalars(select(AutoAssignRule).order_by(AutoAssignRule.id)).all()


@router.get("/by-counterpart/{counterpart}", response_model=AutoAssignRuleRead)
def get_rule_by_counterpart(counterpart: str, db: Session = Depends(get_db)):
    rule = db.scalars(
        select(AutoAssignRule).where(AutoAssignRule.counterpart == counterpart)
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.post("", response_model=AutoAssignRuleRead, status_code=201)
def create_rule(data: AutoAssignRuleCreate, db: Session = Depends(get_db)):
    rule = AutoAssignRule(**data.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=AutoAssignRuleRead)
def update_rule(rule_id: int, data: AutoAssignRuleUpdate, db: Session = Depends(get_db)):
    rule = db.get(AutoAssignRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(AutoAssignRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()


@router.post(
    "/enable-auto-confirm/{counterpart}",
    response_model=EnableAutoConfirmResponse,
)
def enable_auto_confirm(counterpart: str, db: Session = Depends(get_db)):
    """Activa auto_confirm para una contraparte y barre las PENDING existentes.

    Si ya existe una regla para esta contraparte, la actualiza con auto_confirm=True.
    Si no existe, la crea (el caller ya debería haber poblado category/budget
    guardando la transacción con los checkboxes 'Recordar' antes de llamar acá).

    Después del upsert, busca TODAS las PENDING con esta contraparte y las
    confirma (siempre que tengan category_id y budget_period_id). Las que no
    los tienen se cuentan como "skipped" y se reportan en la respuesta para
    que el frontend pueda mostrar algo útil.
    """
    rule = db.scalars(
        select(AutoAssignRule).where(AutoAssignRule.counterpart == counterpart)
    ).first()

    if rule is None:
        rule = AutoAssignRule(counterpart=counterpart, auto_confirm=True)
        db.add(rule)
        db.flush()
    else:
        rule.auto_confirm = True

    # Sweep de PENDING matcheando por counterpart
    pending_txs = db.scalars(
        select(Transaction)
        .where(Transaction.counterpart == counterpart)
        .where(Transaction.status == TxStatus.PENDING)
    ).all()

    confirmed_count = 0
    skipped_count = 0

    for tx in pending_txs:
        # Gasto sin budget → no se puede confirmar. Lo saltamos.
        # Ingreso sin categoría también se puede confirmar, así que solo
        # chequeamos lo imprescindible: EXPENSE requiere budget_period_id.
        if tx.type.value == "EXPENSE" and tx.budget_period_id is None:
            skipped_count += 1
            continue
        try:
            confirm_transaction(db, tx)
            confirmed_count += 1
        except HTTPException:
            # Cualquier otro fallo (cuenta borrada, period borrado, etc):
            # lo saltamos en el sweep masivo en vez de tumbar todo.
            skipped_count += 1

    db.commit()
    db.refresh(rule)

    return EnableAutoConfirmResponse(
        rule=AutoAssignRuleRead.model_validate(rule),
        retroactive_confirmed=confirmed_count,
        retroactive_skipped=skipped_count,
    )


@router.post("/disable-auto-confirm/{counterpart}", response_model=AutoAssignRuleRead)
def disable_auto_confirm(counterpart: str, db: Session = Depends(get_db)):
    """Desactiva auto_confirm (no-op si la regla no existe)."""
    rule = db.scalars(
        select(AutoAssignRule).where(AutoAssignRule.counterpart == counterpart)
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    rule.auto_confirm = False
    db.commit()
    db.refresh(rule)
    return rule
