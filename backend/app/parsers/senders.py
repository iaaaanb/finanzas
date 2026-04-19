"""Registry central de direcciones de email transaccionales.

Esta es la única fuente de verdad sobre qué remitentes producen movimientos.
Toda dirección NO listada acá será marcada SKIPPED automáticamente
(sin importar de qué banco parezca venir).

Cada parser importa este set y filtra las direcciones que le corresponden
en su propio `matches()`. Por convención usamos el dominio para decidir
a qué parser asignar cada dirección.

Cómo agregar una dirección nueva:
  1. Corre `inspect_senders` después de un backfill para ver direcciones nuevas.
  2. Inspecciona con `dump_email --sender <direccion>` para confirmar que es
     una notificación de movimiento real (no publicidad ni cambio de clave).
  3. Agrega la dirección al set acá.
  4. Si es de un banco que no tiene parser, crea uno nuevo en `parsers/`
     con su propio `matches()` filtrando este set.
  5. Reinicia API y opcionalmente corre `cleanup_after_parser_fix` + backfill.
"""

# Direcciones que SÍ generan transacciones reales.
# Toda dirección no listada acá → SKIPPED.
TRANSACTIONAL_SENDERS: frozenset[str] = frozenset({
    # Banco de Chile (incluye Edwards post-fusión)
    "serviciodetransferencias@bancochile.cl",
    "enviodigital@bancoedwards.cl",
    "enviodigital@bancochile.cl",

    # BancoEstado
    "notificaciones@correo.bancoestado.cl",
    "noreply@correo.bancoestado.cl",

    # Banco Falabella
    "notificaciones@cl.bancofalabella.com",

    # BCI
    "transferencias@bci.cl",
})


def is_transactional(email_address: str) -> bool:
    """Conveniencia: True si la dirección está en el registro."""
    return email_address.lower().strip() in TRANSACTIONAL_SENDERS
