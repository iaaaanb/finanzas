from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auto_assign_rule import AutoAssignRule
from app.schemas.auto_assign_rule import (
    AutoAssignRuleCreate,
    AutoAssignRuleUpdate,
    AutoAssignRuleRead,
)

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
