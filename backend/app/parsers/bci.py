import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.parsers.base import BankParser, ParseResult, extract_email_address
from app.parsers.registry import register
from app.parsers.senders import TRANSACTIONAL_SENDERS

_MINE = frozenset({
    addr for addr in TRANSACTIONAL_SENDERS if "bci.cl" in addr
})


class BciParser(BankParser):
    def matches(self, sender: str) -> bool:
        return extract_email_address(sender) in _MINE

    def parse(
        self, email_html: str, sender: str = "", subject: str = ""
    ) -> ParseResult:
        soup = BeautifulSoup(email_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text_lower = text.lower()

        if "has recibido" not in text_lower:
            raise ValueError(
                "Formato BCI no reconocido. Solo se maneja 'Aviso de Transferencia "
                "de Fondos' (transferencia recibida)."
            )

        # --- Monto ---
        amount_match = re.search(
            r"Monto\s+recibido\s+\$\s?([\d.]+)",
            text, re.IGNORECASE,
        )
        if not amount_match:
            raise ValueError("No se encontró 'Monto recibido' en email BCI")
        amount = int(amount_match.group(1).replace(".", ""))

        # --- Contraparte ---
        cp_match = re.search(
            r"transferencia\s+de\s+fondos\s+de\s+(.+?)\s+hacia\s+tu\s+cuenta",
            text, re.IGNORECASE,
        )
        if not cp_match:
            raise ValueError("No se encontró nombre del remitente en email BCI")
        counterpart = cp_match.group(1).strip()

        # --- Fecha ---
        date_match = re.search(
            r"Fecha\s+de\s+la\s+transferencia\s+(\d{2}/\d{2}/\d{4})",
            text, re.IGNORECASE,
        )
        if date_match:
            tx_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date()
        else:
            any_date = re.search(r"(\d{2}/\d{2}/\d{4})", text)
            if any_date:
                tx_date = datetime.strptime(any_date.group(1), "%d/%m/%Y").date()
            else:
                tx_date = date.today()

        # BCI notifica que recibiste plata "hacia tu cuenta del Banco de Chile"
        # pero NO incluye el número. account_number se queda None y el matching
        # cae al fallback por nombre de banco ("Banco de Chile").
        return ParseResult(
            amount=amount,
            tx_type="INCOME",
            counterpart=counterpart,
            date=tx_date,
            account_bank="Banco de Chile",
            account_number=None,
        )


register(BciParser())
