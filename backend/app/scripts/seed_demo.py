"""Puebla la base con datos de ejemplo para el modo demo.

Uso:
    python -m app.scripts.seed_demo --reset      # borra todo y siembra de nuevo
    python -m app.scripts.seed_demo --if-empty   # siembra solo si no hay nada

Genera un historial plausible de ~4 semanas: cuentas, categorías, presupuestos
con períodos cerrados y uno abierto, transacciones confirmadas, un par
pendientes, reglas de auto-asignación, historial de sync y un email que ningún
parser supo leer (para que /errors tenga contenido).

Las transacciones se confirman llamando a `confirm_transaction`, el mismo
servicio que usa la API, así que los saldos de cuentas y presupuestos quedan
consistentes por construcción en vez de hardcodeados.
"""
import argparse
import random
import sys
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    Account,
    AutoAssignRule,
    Budget,
    BudgetPeriod,
    BudgetType,
    Category,
    Email,
    EmailStatus,
    SyncRun,
    SyncStatus,
    SyncTrigger,
    Transaction,
    TxStatus,
    TxType,
)
from app.services.budget_periods import calculate_period_dates
from app.services.transactions import confirm_transaction

TABLES = [
    "transactions",
    "budget_periods",
    "auto_assign_rules",
    "emails",
    "sync_runs",
    "budgets",
    "categories",
    "accounts",
]

# (nombre, banco, color, últimos 4 dígitos, saldo inicial)
ACCOUNTS = [
    ("CuentaRUT", "BancoEstado CuentaRUT", "#f97316", "4820", 620_000),
    ("Ahorro", "BancoEstado Ahorro", "#06b6d4", "7315", 1_450_000),
    ("Cuenta Vista Chile", "Banco de Chile", "#3b82f6", "9064", 380_000),
    ("Efectivo", "Efectivo", "#22c55e", None, 150_000),
]

CATEGORIES = [
    ("Supermercado", "#22c55e"),
    ("Comida", "#ef4444"),
    ("Transporte", "#3b82f6"),
    ("Salidas", "#a855f7"),
    ("Suscripciones", "#06b6d4"),
    ("Salud", "#f97316"),
    ("Universidad", "#eab308"),
    ("Ahorro", "#64748b"),
    ("Ingresos", "#10b981"),
]

# (nombre, tipo, color, monto por período)
BUDGETS = [
    ("Semana L-V", BudgetType.L_V, "#3b82f6", 70_000),
    ("Finde", BudgetType.V_D, "#a855f7", 50_000),
    ("Fijos del mes", BudgetType.MONTHLY, "#f59e0b", 420_000),
]

# Gastos típicos por presupuesto: (contraparte, categoría, monto, cuenta, día
# relativo al inicio del período).
EXPENSES = {
    "Semana L-V": [
        ("UBER RIDES", "Transporte", 4_290, "CuentaRUT", 0),
        ("CASINO CENTRAL U", "Comida", 3_500, "Efectivo", 1),
        ("METRO BIP CARGA", "Transporte", 5_000, "CuentaRUT", 1),
        ("STARBUCKS PROVIDENCIA", "Comida", 5_490, "Cuenta Vista Chile", 2),
        ("EMPANADAS DONA JUANA", "Comida", 4_800, "Efectivo", 3),
        ("UBER RIDES", "Transporte", 5_120, "CuentaRUT", 4),
    ],
    "Finde": [
        ("SUSHI TOKYO", "Comida", 14_500, "CuentaRUT", 0),
        ("CINEHOYTS PARQUE ARAUCO", "Salidas", 9_800, "Cuenta Vista Chile", 1),
        ("BAR LA PIOJERA", "Salidas", 12_900, "Efectivo", 1),
    ],
    "Fijos del mes": [
        ("JUMBO KENNEDY", "Supermercado", 48_990, "CuentaRUT", 2),
        ("SPOTIFY", "Suscripciones", 5_990, "Cuenta Vista Chile", 3),
        ("NETFLIX", "Suscripciones", 8_990, "Cuenta Vista Chile", 4),
        ("ENTEL PLAN MOVIL", "Suscripciones", 17_990, "CuentaRUT", 5),
        ("LIDER EXPRESS", "Supermercado", 22_400, "CuentaRUT", 9),
        ("FARMACIAS AHUMADA", "Salud", 12_300, "CuentaRUT", 12),
        ("JUMBO KENNEDY", "Supermercado", 39_500, "CuentaRUT", 17),
        ("Transferencia a BancoEstado Ahorro", "Ahorro", 150_000, "CuentaRUT", 6),
    ],
}

# Ingresos: no llevan presupuesto. (contraparte, monto, cuenta, días atrás)
INCOMES = [
    ("Sueldo practica", 380_000, "CuentaRUT", 4),
    ("MARIA SOTO ROJAS", 85_000, "Cuenta Vista Chile", 9),
    ("Devolucion arriendo", 45_000, "CuentaRUT", 18),
    ("Sueldo practica", 380_000, "CuentaRUT", 34),
    ("Transferencia desde BancoEstado CuentaRUT", 150_000, "Ahorro", 6),
    ("Transferencia desde BancoEstado CuentaRUT", 150_000, "Ahorro", 36),
]

# Transacciones que quedan sin confirmar, para que la portada muestre la
# bandeja de pendientes apenas se abre la app.
PENDING = [
    ("LIDER EXPRESS", 15_990, "CuentaRUT", "Supermercado", "Fijos del mes", 1),
    ("UBER EATS", 12_400, "Cuenta Vista Chile", None, None, 2),
]

# (contraparte, categoría, presupuesto, auto_confirm)
RULES = [
    ("UBER RIDES", "Transporte", "Semana L-V", True),
    ("SPOTIFY", "Suscripciones", "Fijos del mes", True),
    ("JUMBO KENNEDY", "Supermercado", "Fijos del mes", False),
    ("NETFLIX", "Suscripciones", "Fijos del mes", True),
]

PAST_PERIODS = 3  # además del período abierto


def _previous_period(budget_type: BudgetType, start: date) -> tuple[date, date]:
    """Período inmediatamente anterior al que arranca en `start`."""
    return calculate_period_dates(budget_type, start - timedelta(days=1))


def reset(db: Session) -> None:
    db.execute(
        text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE")
    )
    db.commit()


def is_empty(db: Session) -> bool:
    return db.scalar(select(func.count()).select_from(Budget)) == 0


def seed(db: Session, today: date, now: datetime) -> None:
    rng = random.Random(7)

    accounts = {}
    for name, bank, color, number, balance in ACCOUNTS:
        acc = Account(
            name=name, bank=bank, color=color, account_number=number, balance=balance
        )
        db.add(acc)
        accounts[name] = acc

    categories = {}
    for name, color in CATEGORIES:
        cat = Category(name=name, color=color)
        db.add(cat)
        categories[name] = cat

    budgets = {}
    periods = {}  # nombre presupuesto -> [períodos, del más viejo al actual]
    for name, btype, color, amount in BUDGETS:
        budget = Budget(name=name, type=btype, color=color, amount=amount)
        db.add(budget)
        budgets[name] = budget

        start, end = calculate_period_dates(btype, today)
        ranges = [(start, end)]
        for _ in range(PAST_PERIODS):
            start, end = _previous_period(btype, start)
            ranges.append((start, end))
        ranges.reverse()

        periods[name] = [
            BudgetPeriod(
                budget=budget,
                period_start=s,
                period_end=e,
                starting_amount=amount,
                balance=amount,
            )
            for s, e in ranges
        ]
        db.add_all(periods[name])

    db.flush()

    # ---- Gastos confirmados, período por período ----
    for budget_name, template in EXPENSES.items():
        for period in periods[budget_name]:
            for counterpart, cat_name, base_amount, account_name, day in template:
                tx_date = period.period_start + timedelta(days=day)
                if tx_date > today or tx_date > period.period_end:
                    continue
                # Jitter para que los períodos no salgan todos idénticos.
                # Las transferencias entre cuentas propias quedan exactas:
                # tienen que calzar peso a peso con el ingreso del otro lado.
                if counterpart.startswith("Transferencia"):
                    amount = base_amount
                else:
                    amount = int(base_amount * rng.uniform(0.85, 1.15) / 10) * 10
                tx = Transaction(
                    type=TxType.EXPENSE,
                    amount=amount,
                    date=tx_date,
                    counterpart=counterpart,
                    account_id=accounts[account_name].id,
                    category_id=categories[cat_name].id,
                    budget_period_id=period.id,
                    status=TxStatus.PENDING,
                )
                db.add(tx)
                db.flush()
                confirm_transaction(db, tx)

    # ---- Ingresos confirmados ----
    for counterpart, amount, account_name, days_ago in INCOMES:
        tx = Transaction(
            type=TxType.INCOME,
            amount=amount,
            date=today - timedelta(days=days_ago),
            counterpart=counterpart,
            account_id=accounts[account_name].id,
            category_id=categories["Ingresos"].id,
            status=TxStatus.PENDING,
        )
        db.add(tx)
        db.flush()
        confirm_transaction(db, tx)

    # ---- Cerrar los períodos viejos ----
    for period_list in periods.values():
        for period in period_list[:-1]:
            period.final_balance = period.balance
            period.closed_at = datetime.combine(
                period.period_end + timedelta(days=1), datetime.min.time()
            )

    # ---- Pendientes por confirmar ----
    for counterpart, amount, account_name, cat_name, budget_name, days_ago in PENDING:
        db.add(
            Transaction(
                type=TxType.EXPENSE,
                amount=amount,
                date=today - timedelta(days=days_ago),
                counterpart=counterpart,
                account_id=accounts[account_name].id,
                category_id=categories[cat_name].id if cat_name else None,
                budget_period_id=periods[budget_name][-1].id if budget_name else None,
                status=TxStatus.PENDING,
            )
        )

    # ---- Reglas de auto-asignación ----
    for counterpart, cat_name, budget_name, auto_confirm in RULES:
        db.add(
            AutoAssignRule(
                counterpart=counterpart,
                category_id=categories[cat_name].id,
                budget_id=budgets[budget_name].id,
                auto_confirm=auto_confirm,
            )
        )

    _seed_emails_and_syncs(db, now)
    db.commit()


def _seed_emails_and_syncs(db: Session, now: datetime) -> None:
    """Historial de correos procesados y de corridas de sync.

    El email más nuevo queda 6 horas atrás: el sync incremental arranca desde
    ahí, así que apretar "Traer emails nuevos" en la demo trae toda la tanda
    de `app.demo.inbox` y nada más.
    """
    emails = [
        (52, "Banco de Chile <enviodigital@bancochile.cl>", "Cargo en Cuenta", EmailStatus.PARSED),
        (48, "Banco de Chile <comunicaciones@bancochile.cl>", "Tu resumen mensual", EmailStatus.SKIPPED),
        (36, "BancoEstado <notificaciones@correo.bancoestado.cl>", "Comprobante de pago", EmailStatus.PARSED),
        (30, "Banco BCI <transferencias@bci.cl>", "Aviso de Transferencia de Fondos", EmailStatus.PARSED),
        (26, "LinkedIn <jobs@linkedin.com>", "20 empleos nuevos para ti", EmailStatus.SKIPPED),
        (20, "Banco Falabella <notificaciones@cl.bancofalabella.com>", "Transferencia recibida", EmailStatus.PARSED),
        (14, "Banco de Chile <enviodigital@bancochile.cl>", "Cargo en Cuenta", EmailStatus.PARSED),
        (6, "Banco de Chile <enviodigital@bancochile.cl>", "Cargo en Cuenta", EmailStatus.PARSED),
    ]
    for i, (hours_ago, sender, subject, status) in enumerate(emails):
        db.add(
            Email(
                gmail_message_id=f"seed-{i:04d}",
                sender=sender,
                subject=subject,
                body_html=(
                    '<html><body style="font-family:Arial,Helvetica,sans-serif">'
                    "<p>Correo del historial de la demo. Los cuerpos completos "
                    "solo se guardan para los correos que el sync trae en vivo."
                    "</p></body></html>"
                ),
                received_at=now - timedelta(hours=hours_ago),
                status=status,
            )
        )

    # Email que ningún parser supo leer: aparece en /errors esperando que el
    # usuario lo resuelva a mano.
    db.add(
        Email(
            gmail_message_id="seed-error-0001",
            sender="BancoEstado <notificaciones@correo.bancoestado.cl>",
            subject="Aviso de cargo en cuenta",
            body_html=(
                '<html><body style="margin:0;background:#eef0f4;'
                'font-family:Arial,Helvetica,sans-serif;color:#1f2937">'
                '<table width="100%" cellpadding="0" cellspacing="0" '
                'style="max-width:560px;margin:0 auto;background:#fff">'
                '<tr><td style="background:#ff6a13;color:#fff;padding:14px 18px;'
                'font-size:17px;font-weight:bold">BancoEstado</td></tr>'
                '<tr><td style="padding:18px;font-size:13.5px;line-height:1.6">'
                "<h3>Aviso de cargo</h3>"
                "<p>Se ha cursado un cargo asociado a tu convenio PAC.</p>"
                "<div>Convenio: SEGURO COMPLEMENTARIO SALUD</div>"
                "<div>Valor cursado: 21.400 CLP</div>"
                "<p>El detalle est&aacute; disponible en tu banca en "
                "l&iacute;nea.</p></td></tr>"
                '<tr><td style="padding:12px 18px;background:#f6f7f9;'
                'color:#6b7280;font-size:10.5px">Correo de ejemplo generado '
                "por el modo demo de Finanzas. No es una comunicacion real de "
                "ninguna institucion financiera.</td></tr>"
                "</table></body></html>"
            ),
            received_at=now - timedelta(hours=27),
            status=EmailStatus.PENDING,
        )
    )

    # (horas atrás, trigger, status, fetched, parsed, skipped, errors, error_msg)
    runs = [
        (54, SyncTrigger.CRON, SyncStatus.SUCCESS, 4, 2, 2, 0, None),
        (
            29, SyncTrigger.CRON, SyncStatus.FAILED, 0, 0, 0, 0,
            "RefreshError: invalid_grant: Token has been expired or revoked.",
        ),
        (27, SyncTrigger.UI_BACKFILL, SyncStatus.SUCCESS, 9, 5, 3, 1, None),
        (21, SyncTrigger.CRON, SyncStatus.SUCCESS, 3, 2, 1, 0, None),
        (14, SyncTrigger.CRON, SyncStatus.SUCCESS, 2, 1, 1, 0, None),
        (6, SyncTrigger.CRON, SyncStatus.SUCCESS, 5, 3, 2, 0, None),
    ]
    for hours_ago, trigger, status, fetched, parsed, skipped, errors, msg in runs:
        started = now - timedelta(hours=hours_ago)
        db.add(
            SyncRun(
                trigger=trigger,
                status=status,
                since_at=started - timedelta(hours=1),
                started_at=started,
                finished_at=started + timedelta(seconds=6 + fetched),
                fetched=fetched,
                parsed=parsed,
                skipped=skipped,
                parse_errors=errors,
                duplicates=0,
                error_message=msg,
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Siembra datos de demo.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--reset", action="store_true", help="Borra todas las tablas y siembra."
    )
    group.add_argument(
        "--if-empty", action="store_true", help="Siembra solo si la base está vacía."
    )
    args = parser.parse_args()

    # La base guarda datetimes naive en UTC.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.date()

    with SessionLocal() as db:
        if args.if_empty and not is_empty(db):
            print("[skip] La base ya tiene datos.")
            return
        reset(db)
        seed(db, today, now)

        balances = db.execute(select(Account.name, Account.balance)).all()
        print("[ok] Datos de demo sembrados.")
        for name, balance in balances:
            print(f"       {name:<20} ${balance:,}".replace(",", "."))


if __name__ == "__main__":
    main()
