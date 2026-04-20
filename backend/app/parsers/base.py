from dataclasses import dataclass
from datetime import date
from abc import ABC, abstractmethod
from typing import Optional


@dataclass
class ParseResult:
    amount: int           # Monto en CLP, siempre positivo
    tx_type: str          # "INCOME" o "EXPENSE"
    counterpart: str
    date: date
    account_bank: str     # Nombre del banco para asociar a cuenta (fallback)
    account_number: Optional[str] = None  # Últimos 4 dígitos para matching preciso


class BankParser(ABC):
    @abstractmethod
    def matches(self, sender: str) -> bool:
        """Retorna True si este parser maneja este remitente."""
        ...

    @abstractmethod
    def parse(
        self, email_html: str, sender: str = "", subject: str = ""
    ) -> ParseResult | list[ParseResult]:
        """Parsea el HTML del email y retorna los datos extraídos.
        Puede retornar un solo resultado o una lista (ej: transferencia entre cuentas propias).
        `sender` y `subject` son opcionales y permiten al parser distinguir sub-casos
        (income vs expense, tipo de notificación, etc) sin tener que inferirlo del body.
        Lanza ValueError si falla el parseo (queda PENDING para resolución manual).
        """
        ...


def extract_email_address(sender: str) -> str:
    """Extrae la dirección de email de un header From.

    >>> extract_email_address('Banco de Chile <contactos@bancochile.cl>')
    'contactos@bancochile.cl'
    >>> extract_email_address('contacto@bancochile.cl')
    'contacto@bancochile.cl'
    """
    s = sender.strip()
    if "<" in s and ">" in s:
        return s.split("<")[-1].split(">")[0].strip().lower()
    return s.lower()


def last4(account_string: str) -> Optional[str]:
    """Extrae los últimos 4 dígitos de una representación de cuenta.
    Acepta tanto formato enmascarado (****5092) como completo (00-016-17250-92,
    32963285387). Devuelve None si no se puede extraer.

    >>> last4('****5092')
    '5092'
    >>> last4('00-016-17250-92')
    '5092'
    >>> last4('32963285387')
    '5387'
    >>> last4('Cuenta Vista 00-016-17250-92')
    '5092'
    >>> last4('') is None
    True
    >>> last4('abc') is None
    True
    """
    if not account_string:
        return None
    # Quedarse solo con dígitos
    digits = "".join(c for c in account_string if c.isdigit())
    if len(digits) < 4:
        return None
    return digits[-4:]
