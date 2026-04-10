from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.email import Email, EmailStatus
from app.models.transaction import Transaction, TxStatus
from app.schemas.email import EmailRead
from app.schemas.transaction import TransactionRead

router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.get("/errors", response_model=list[EmailRead])
def list_error_emails(db: Session = Depends(get_db)):
    """Emails con estado PENDING (error de parseo)."""
    return db.scalars(
        select(Email)
        .where(Email.status == EmailStatus.PENDING)
        .order_by(Email.received_at.desc())
    ).all()


@router.get("/{email_id}", response_model=EmailRead)
def get_email(email_id: int, db: Session = Depends(get_db)):
    email = db.get(Email, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


@router.post("/{email_id}/resolve", response_model=TransactionRead)
def resolve_email(email_id: int, data: dict, db: Session = Depends(get_db)):
    """Resolver un email con error de parseo creando una transacción manualmente."""
    from app.models.account import Account

    email = db.get(Email, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")

    tx = Transaction(
        type=data["type"],
        amount=int(data["amount"]),
        date=data["date"],
        counterpart=data["counterpart"],
        account_id=int(data["account_id"]),
        email_id=email.id,
        status=TxStatus.PENDING,
    )
    db.add(tx)
    email.status = EmailStatus.PARSED
    db.commit()
    db.refresh(tx)
    return tx
