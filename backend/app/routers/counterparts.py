from fastapi import APIRouter, Depends
from sqlalchemy import select, distinct
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transaction import Transaction

router = APIRouter(prefix="/api/counterparts", tags=["counterparts"])


@router.get("", response_model=list[str])
def list_counterparts(db: Session = Depends(get_db)):
    results = db.scalars(
        select(distinct(Transaction.counterpart)).order_by(Transaction.counterpart)
    ).all()
    return results
