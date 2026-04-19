from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.email import Email, EmailStatus
from app.models.transaction import Transaction, TxType, TxStatus
from app.models.account import Account
from app.models.auto_assign_rule import AutoAssignRule
from app.models.budget_period import BudgetPeriod
from app.parsers.registry import find_parser
from app.parsers.base import extract_email_address
from app.parsers.senders import is_transactional


def process_email(db: Session, email_data: dict) -> Email:
    """Procesa un email crudo: lo guarda en DB y, si el remitente está en el
    registro de direcciones transaccionales, intenta parsearlo."""

    # Deduplicación
    existing = db.scalars(
        select(Email).where(Email.gmail_message_id == email_data["gmail_message_id"])
    ).first()
    if existing:
        return existing

    email = Email(
        gmail_message_id=email_data["gmail_message_id"],
        sender=email_data["sender"],
        subject=email_data["subject"],
        body_html=email_data["body_html"],
        received_at=email_data["received_at"],
    )

    # Gate 1: ¿el remitente está en el registro de direcciones transaccionales?
    addr = extract_email_address(email_data["sender"])
    if not is_transactional(addr):
        email.status = EmailStatus.SKIPPED
        db.add(email)
        return email

    # Gate 2: ¿algún parser reclama este remitente?
    # (Si el registro tiene una dirección sin parser asociado, se omite con un warning)
    parser = find_parser(email_data["sender"])
    if parser is None:
        email.status = EmailStatus.SKIPPED
        db.add(email)
        return email

    try:
        raw = parser.parse(email_data["body_html"], sender=email_data["sender"])
        results = raw if isinstance(raw, list) else [raw]

        email.status = EmailStatus.PARSED
        db.add(email)
        db.flush()

        for result in results:
            # Buscar cuenta por banco
            account = db.scalars(
                select(Account).where(Account.bank == result.account_bank)
            ).first()
            if not account:
                account = db.scalars(select(Account).order_by(Account.id)).first()

            # Auto-assign rule
            category_id = None
            budget_period_id = None
            rule = db.scalars(
                select(AutoAssignRule).where(
                    AutoAssignRule.counterpart == result.counterpart
                )
            ).first()
            if rule:
                category_id = rule.category_id
                if rule.budget_id:
                    period = db.scalars(
                        select(BudgetPeriod).where(
                            BudgetPeriod.budget_id == rule.budget_id,
                            BudgetPeriod.closed_at.is_(None),
                        )
                    ).first()
                    if period:
                        budget_period_id = period.id

            tx = Transaction(
                type=TxType(result.tx_type),
                amount=result.amount,
                date=result.date,
                counterpart=result.counterpart,
                account_id=account.id,
                category_id=category_id,
                budget_period_id=budget_period_id,
                status=TxStatus.PENDING,
                email_id=email.id,
            )
            db.add(tx)

    except Exception:
        # Error real de parseo: el remitente es transaccional pero el formato es nuevo
        email.status = EmailStatus.PENDING
        db.add(email)

    return email
