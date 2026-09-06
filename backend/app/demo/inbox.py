"""Casilla de correo falsa para el modo demo.

Cada entrada imita el HTML real que manda cada banco, de modo que los parsers
de `app.parsers` corren sin ninguna adaptación: lo que ves en la demo es
exactamente el mismo camino email → parser → transacción que en producción.

La tanda está armada para que un solo sync muestre todos los caminos posibles:

  1. Cargo en cuenta (Banco de Chile)   → EXPENSE, queda PENDING
  2. Cargo en cuenta (Banco de Chile)   → EXPENSE, auto-confirmada por regla
  3. Pago entre cuentas propias (Estado)→ 1 email = 2 transacciones
  4. Transferencia recibida (BCI)       → INCOME
  5. Transferencia recibida (Falabella) → INCOME
  6. Formato desconocido (Banco Chile)  → error de parseo, va a /errors
  7. Newsletter (remitente no listado)  → SKIPPED por el registro de senders

Las fechas se calculan relativas a "ahora" para que las transacciones caigan
siempre dentro de los períodos de presupuesto abiertos.
"""
from datetime import datetime, timedelta, timezone

# Chile es UTC-3 (sin horario de verano en la mayor parte del país).
SANTIAGO_TZ = timezone(timedelta(hours=-3))


def _fecha_cl(now: datetime) -> str:
    return now.astimezone(SANTIAGO_TZ).strftime("%d/%m/%Y")


def _fecha_cl_guiones(now: datetime) -> str:
    return now.astimezone(SANTIAGO_TZ).strftime("%d-%m-%Y")


# Aviso al pie de cada correo: son ejemplos generados por el modo demo, no
# comunicaciones reales de ninguna institución.
DISCLAIMER = (
    "Correo de ejemplo generado por el modo demo de Finanzas. "
    "No es una comunicaci&oacute;n real de ninguna institucion financiera."
)


def _wrap(inner: str, banco: str, color: str) -> str:
    """Envuelve el cuerpo en un HTML con la pinta de un mail bancario."""
    return (
        '<html><body style="margin:0;background:#eef0f4;'
        'font-family:Arial,Helvetica,sans-serif;color:#1f2937">'
        '<table width="100%" cellpadding="0" cellspacing="0" '
        'style="max-width:560px;margin:0 auto;background:#ffffff">'
        f'<tr><td style="background:{color};color:#ffffff;padding:14px 18px;'
        f'font-size:17px;font-weight:bold">{banco}</td></tr>'
        '<tr><td style="padding:18px;font-size:13.5px;line-height:1.6">'
        f"{inner}"
        "</td></tr>"
        '<tr><td style="padding:12px 18px;background:#f6f7f9;color:#6b7280;'
        f'font-size:10.5px">{DISCLAIMER}</td></tr>'
        "</table></body></html>"
    )


# ---------------------------------------------------------------------------
# 1 y 2 — Banco de Chile / Edwards: "Cargo en Cuenta" (compra con débito)
# ---------------------------------------------------------------------------
def _cargo_debito(now: datetime, comercio: str, monto: str, hora: str) -> str:
    return _wrap(
        "<p>Estimado(a) cliente:</p>"
        f"<p>Te informamos que se ha realizado una compra por ${monto} con tu "
        f"Tarjeta de D&eacute;bito Banco de Chile en {comercio} el "
        f"{_fecha_cl(now)} a las {hora} hrs.</p>"
        "<p>Si no reconoces esta operaci&oacute;n, comun&iacute;cate con "
        "nosotros al 600 637 3737.</p>",
        "Banco de Chile",
        "#0b3d91",
    )


# ---------------------------------------------------------------------------
# 3 — BancoEstado: pago entre cuentas propias (genera DOS transacciones)
# ---------------------------------------------------------------------------
def _pago_cuentas_propias(now: datetime) -> str:
    fecha = _fecha_cl(now)
    return _wrap(
        "<h2>Comprobante de pago</h2>"
        "<table><tr><td>Fecha y hora</td><th>" + fecha + " 09:12</th></tr>"
        "<tr><td>Monto Total</td><th>$150.000</th></tr></table>"
        "<table><tr><td>Origen</td></tr>"
        "<tr><td>Producto</td><th>CuentaRUT</th></tr>"
        "<tr><td>N&deg; de cuenta</td><th>****4820</th></tr></table>"
        "<table><tr><td>Destino</td></tr>"
        "<tr><td>Producto</td><th>Cuenta de Ahorro</th></tr>"
        "<tr><td>N&deg; de cuenta</td><th>****7315</th></tr></table>"
        "<p>Te confirmamos que el pago se ha realizado correctamente.</p>",
        "BancoEstado",
        "#ff6a13",
    )


# ---------------------------------------------------------------------------
# 4 — BCI: transferencia recibida
# ---------------------------------------------------------------------------
def _bci_recibida(now: datetime) -> str:
    return _wrap(
        "<p>Hola, has recibido una transferencia de fondos de MARIA SOTO ROJAS "
        "hacia tu cuenta del Banco de Chile.</p>"
        "<table><tr><td>Monto recibido</td><td>$85.000</td></tr>"
        "<tr><td>Fecha de la transferencia</td><td>" + _fecha_cl(now) + "</td></tr>"
        "</table>",
        "Banco BCI",
        "#0033a1",
    )


# ---------------------------------------------------------------------------
# 5 — Banco Falabella: transferencia recibida
# ---------------------------------------------------------------------------
def _falabella_recibida(now: datetime) -> str:
    return _wrap(
        "<p>Te informamos que nuestro cliente RODRIGO PE&Ntilde;A ha realizado "
        "una transferencia a tu cuenta.</p>"
        "<table><tr><td>Monto transferencia</td><td>$32.500</td></tr>"
        "<tr><td>Fecha</td><td>" + _fecha_cl_guiones(now) + "</td></tr>"
        "<tr><td>Banco de destino</td><td>BancoEstado</td></tr>"
        "<tr><td>Cuenta de destino</td><td>CuentaRUT ****4820</td></tr></table>",
        "Banco Falabella",
        "#0f8b4c",
    )


# ---------------------------------------------------------------------------
# 6 — Formato que ningún parser sabe leer todavía → termina en /errors
# ---------------------------------------------------------------------------
def _formato_desconocido(now: datetime) -> str:
    return _wrap(
        "<h2>Notificaci&oacute;n de movimiento</h2>"
        "<p>Hemos registrado un movimiento en tu cuenta.</p>"
        "<div>Detalle: PAGO PAC SEGURO VIDA</div>"
        "<div>Valor: 18.500 CLP</div>"
        f"<div>Registrado: {_fecha_cl(now)}</div>"
        "<p>Revisa el detalle en tu banca en l&iacute;nea.</p>",
        "Banco de Chile",
        "#0b3d91",
    )


# ---------------------------------------------------------------------------
# 7 — Newsletter: remitente fuera del registro de transaccionales → SKIPPED
# ---------------------------------------------------------------------------
def _newsletter() -> str:
    return _wrap(
        "<h2>Nuevos beneficios para ti</h2>"
        "<p>Este mes tenemos 30% de descuento en restaurantes seleccionados "
        "pagando con tu Tarjeta de D&eacute;bito.</p>"
        "<p>Revisa las condiciones en nuestro sitio.</p>",
        "Banco de Chile",
        "#0b3d91",
    )


# (minutos_atras, gmail_message_id, remitente, asunto, builder)
_SPECS = [
    (
        295, "demo-0001",
        "Banco de Chile <enviodigital@bancochile.cl>",
        "Cargo en Cuenta",
        lambda now: _cargo_debito(now, "JUMBO KENNEDY", "23.990", "19:42"),
    ),
    (
        240, "demo-0002",
        "BancoEstado <notificaciones@correo.bancoestado.cl>",
        "Comprobante de pago",
        _pago_cuentas_propias,
    ),
    (
        180, "demo-0003",
        "Banco BCI <transferencias@bci.cl>",
        "Aviso de Transferencia de Fondos",
        _bci_recibida,
    ),
    (
        120, "demo-0004",
        "Banco de Chile <comunicaciones@bancochile.cl>",
        "Nuevos beneficios en gastronomia",
        lambda now: _newsletter(),
    ),
    (
        75, "demo-0005",
        "Banco Falabella <notificaciones@cl.bancofalabella.com>",
        "Transferencia recibida",
        _falabella_recibida,
    ),
    (
        40, "demo-0006",
        "Banco de Chile <enviodigital@bancochile.cl>",
        "Notificacion de movimiento",
        _formato_desconocido,
    ),
    (
        15, "demo-0007",
        "Banco de Chile <enviodigital@bancochile.cl>",
        "Cargo en Cuenta",
        lambda now: _cargo_debito(now, "UBER RIDES", "4.290", "08:21"),
    ),
]


def build_inbox(now: datetime | None = None) -> list[dict]:
    """Devuelve los emails de la casilla falsa, del más viejo al más nuevo.

    Mismo formato de dict que produce `gmail_sync._fetch_emails_after`.
    """
    now = now or datetime.now(timezone.utc)
    emails = []
    for minutes_ago, gmid, sender, subject, builder in _SPECS:
        received_at = now - timedelta(minutes=minutes_ago)
        emails.append({
            "gmail_message_id": gmid,
            "sender": sender,
            "subject": subject,
            "body_html": builder(received_at),
            "received_at": received_at,
        })
    return sorted(emails, key=lambda e: e["received_at"])
