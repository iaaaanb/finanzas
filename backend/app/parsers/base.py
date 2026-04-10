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
    def parse(self, email_html: str) -> ParseResult | list[ParseResult]:
        """Parsea el HTML del email y retorna los datos extraídos.
        Puede retornar un solo resultado o una lista (ej: transferencia entre cuentas propias).
        Lanza ValueError si falla.
        """
        ...
