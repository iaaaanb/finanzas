from dataclasses import dataclass
from datetime import date
from abc import ABC, abstractmethod


@dataclass
class ParseResult:
    amount: int           # Monto en CLP, siempre positivo
    tx_type: str          # "INCOME" o "EXPENSE"
    counterpart: str
    date: date
    account_bank: str     # Nombre del banco para asociar a cuenta


class BankParser(ABC):
    @abstractmethod
    def matches(self, sender: str) -> bool:
        """Retorna True si este parser maneja este remitente."""
        ...

    @abstractmethod
    def parse(self, email_html: str, sender: str = "") -> ParseResult | list[ParseResult]:
        """Parsea el HTML del email y retorna los datos extraídos.
        Puede retornar un solo resultado o una lista (ej: transferencia entre cuentas propias).
        `sender` es opcional y permite al parser distinguir sub-casos basados en la dirección.
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
