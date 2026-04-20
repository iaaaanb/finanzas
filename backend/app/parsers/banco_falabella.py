import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.parsers.base import BankParser, ParseResult, extract_email_address, last4
from app.parsers.registry import register
from app.parsers.senders import TRANSACTIONAL_SENDERS

_MINE = frozenset({
    addr for addr in TRANSACTIONAL_SENDERS if "bancofalabella" in addr
})


class BancoFalabellaParser(BankParser):
    def matches(self, sender: str) -> bool:
        return extract_email_address(sender) in _MINE

    def parse(
        self, email_html: str, sender: str = "", subject: str = ""
    ) -> ParseResult:
        soup = BeautifulSoup(email_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        kv = self._extract_kv(soup)

        # --- Monto ---
        raw_amount = kv.get("Monto transferencia", "")
        if not raw_amount:
            m = re.search(r"\$\s?([\d.]+)", text)
            if not m:
                raise ValueError("No se encontró monto en email de Banco Falabella")
            raw_amount = m.group(1)
        amount = int(raw_amount.replace("$", "").replace(".", "").strip())

        # --- Contraparte ---
        counterpart = "Desconocido"
        cp_match = re.search(
            r"(?:nuestro\(?a?\)?\s+)?cliente\s+(.+?)\s+ha\b",
            text, re.IGNORECASE,
        )
        if cp_match:
            counterpart = cp_match.group(1).strip()

        # --- Fecha ---
        raw_date = kv.get("Fecha", "")
        if raw_date:
            try:
                tx_date = datetime.strptime(raw_date.strip(), "%d-%m-%Y").date()
            except ValueError:
                tx_date = date.today()
        else:
            tx_date = date.today()

        # --- Cuenta destino ---
        cuenta_destino = kv.get("Cuenta de destino", "")
        account_bank = self._resolve_account(
            kv.get("Banco de destino", ""),
            cuenta_destino,
        )
        account_number = last4(cuenta_destino)

        return ParseResult(
            amount=amount,
            tx_type="INCOME",
            counterpart=counterpart,
            date=tx_date,
            account_bank=account_bank,
            account_number=account_number,
        )

    @staticmethod
    def _extract_kv(soup: BeautifulSoup) -> dict[str, str]:
        kv: dict[str, str] = {}
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) == 2:
                key = tds[0].get_text(strip=True)
                val = tds[1].get_text(strip=True)
                if key and val:
                    kv[key] = val
        return kv

    @staticmethod
    def _resolve_account(banco: str, cuenta: str) -> str:
        banco_l = banco.lower().strip()
        cuenta_l = cuenta.lower().strip()

        if "estado" in banco_l:
            if "ahorro" in cuenta_l:
                return "BancoEstado Ahorro"
            return "BancoEstado CuentaRUT"

        if "chile" in banco_l or "edwards" in banco_l:
            return "Banco de Chile"

        return banco.strip() if banco.strip() else "Desconocido"


register(BancoFalabellaParser())
