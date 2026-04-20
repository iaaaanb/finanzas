from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.email import Email, EmailStatus
from app.models.transaction import Transaction, TxType, TxStatus
from app.models.account import Account
from app.models.auto_assign_rule import AutoAssignRule
from app.models.budget_period import BudgetPeriod
from app.parsers.registry import find_parser
from app.parsers.base import extract_email_address, ParseResult
from app.parsers.senders import is_transactional
from app.services.transactions import confirm_transaction


def _resolve_account(db: Session, result: ParseResult) -> Account:
    """Encuentra la Account correcta en orden de precisión:
    1. Match exacto por account_number (últimos 4 dígitos)
    2. Match por nombre de banco
    3. Fallback al primer Account (típicamente "Efectivo")
    """
    if result.account_number:
        account = db.scalars(
            select(Account).where(Account.account_number == result.account_number)
        ).first()
        if account:
            return account

    account = db.scalars(
        select(Account).where(Account.bank == result.account_bank)
    ).first()
    if account:
        return account

    return db.scalars(select(Account).order_by(Account.id)).first()


def _record_email_as_pending(db: Session, email_data: dict) -> Email:
    """Guarda el email con status=PENDING en una transacción limpia.

    Se llama después de un rollback, cuando el parseo (o cualquier paso
    siguiente) falló y solo queremos dejar constancia del email para que
    aparezca en /errors y el usuario pueda resolverlo manualmente.
    """
    email = Email(
        gmail_message_id=email_data["gmail_message_id"],
        sender=email_data["sender"],
        subject=email_data["subject"],
        body_html=email_data["body_html"],
        received_at=email_data["received_at"],
        status=EmailStatus.PENDING,
    )
    db.add(email)
    return email


def process_email(db: Session, email_data: dict) -> Email:
    """Procesa un email crudo: lo guarda en DB y, si el remitente está en el
    registro de direcciones transaccionales, intenta parsearlo.

    Si el parser produce transacciones cuya contraparte tiene auto_confirm=True
    y todos los datos necesarios (category + budget_period para EXPENSE),
    se confirma automáticamente aquí mismo en vez de dejarla PENDING.

    Manejo de errores: si cualquier paso falla entre "email parseado" y
    "transacciones creadas+confirmadas", hacemos rollback completo y
    re-insertamos el email con status=PENDING en una sesión limpia. Esto evita
    dejar el session en estado 'InFailedSqlTransaction', que tumbaría el resto
    del batch si alguien está reusando la misma sesión.
    """

    # Deduplicación
    existing = db.scalars(
        select(Email).where(Email.gmail_message_id == email_data["gmail_message_id"])
    ).first()
    if existing:
        return existing

    # Gate 1: ¿remitente en el registro de transaccionales?
    addr = extract_email_address(email_data["sender"])
    if not is_transactional(addr):
        email = Email(
            gmail_message_id=email_data["gmail_message_id"],
            sender=email_data["sender"],
            subject=email_data["subject"],
            body_html=email_data["body_html"],
            received_at=email_data["received_at"],
            status=EmailStatus.SKIPPED,
        )
        db.add(email)
        return email

    # Gate 2: ¿algún parser lo reclama?
    parser = find_parser(email_data["sender"])
    if parser is None:
        email = Email(
            gmail_message_id=email_data["gmail_message_id"],
            sender=email_data["sender"],
            subject=email_data["subject"],
            body_html=email_data["body_html"],
            received_at=email_data["received_at"],
            status=EmailStatus.SKIPPED,
        )
        db.add(email)
        return email

    # ---- Parseo + creación de transacciones ----
    # Este bloque es la parte "delicada": si cualquier paso acá falla, la
    # sesión entera puede quedar en estado inválido. Lo envolvemos en try/except
    # y en caso de error hacemos rollback + guardamos el email como PENDING en
    # una sesión limpia.
    try:
        raw = parser.parse(
            email_data["body_html"],
            sender=email_data["sender"],
            subject=email_data["subject"],
        )
        results = raw if isinstance(raw, list) else [raw]

        email = Email(
            gmail_message_id=email_data["gmail_message_id"],
            sender=email_data["sender"],
            subject=email_data["subject"],
            body_html=email_data["body_html"],
            received_at=email_data["received_at"],
            status=EmailStatus.PARSED,
        )
        db.add(email)
        db.flush()

        for result in results:
            account = _resolve_account(db, result)

            # Auto-assign rule
            category_id = None
            budget_period_id = None
            should_auto_confirm = False
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
                should_auto_confirm = rule.auto_confirm

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
            db.flush()  # Asegurar que tx tenga id antes de confirmar

            # Auto-confirmación: solo si la regla lo pide Y tenemos todo lo
            # necesario. Si falta budget en un EXPENSE, queda PENDING (no es
            # un error — el usuario lo maneja manualmente).
            if should_auto_confirm:
                can_confirm = (
                    tx.type != TxType.EXPENSE or tx.budget_period_id is not None
                )
                if can_confirm:
                    # No envolvemos en try/except: si confirm_transaction falla,
                    # la sesión queda poisoned y no podemos recuperar este email
                    # mid-stream. Dejamos que la excepción escale al try/except
                    # de process_email, que hace rollback limpio + marca el
                    # email como PENDING.
                    confirm_transaction(db, tx)

        return email

    except Exception:
        # Rollback completo para salir del estado 'InFailedSqlTransaction'.
        # Después, en una transacción limpia, guardamos el email como PENDING
        # para que aparezca en /errors.
        db.rollback()
        return _record_email_as_pending(db, email_data)
