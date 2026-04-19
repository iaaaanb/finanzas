import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.parsers.base import BankParser, ParseResult, extract_email_address
from app.parsers.registry import register
from app.parsers.senders import TRANSACTIONAL_SENDERS

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Filtrar del registro central solo las direcciones de Banco de Chile / Edwards
_MINE = frozenset({
    addr for addr in TRANSACTIONAL_SENDERS
    if "bancochile" in addr or "bancoedwards" in addr
})


class BancoChileParser(BankParser):
    def matches(self, sender: str) -> bool:
        return extract_email_address(sender) in _MINE

    def parse(self, email_html: str, sender: str = "") -> ParseResult:
        soup = BeautifulSoup(email_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text_lower = text.lower()

        if "comprobante de transferencia" in text_lower:
            return self._parse_tef(soup, text)
        return self._parse_notification(soup, text)

    # ------------------------------------------------------------------
    # TEF: comprobante de transferencia (enviada o recibida)
    # ------------------------------------------------------------------
    def _parse_tef(self, soup: BeautifulSoup, text: str) -> ParseResult:
        kv = self._extract_kv(soup)

        raw_amount = kv.get("Monto", "")
        if not raw_amount:
            m = re.search(r"\$\s?([\d.]+)", text)
            if not m:
                raise ValueError("No se encontró monto en TEF de Banco de Chile")
            raw_amount = m.group(1)
        amount = int(raw_amount.replace("$", "").replace(".", "").strip())

        text_lower = text.lower()
        if "a tu cuenta" in text_lower or "fondos a tu" in text_lower:
            tx_type = "INCOME"
            counterpart = self._extract_sender_name(soup)
        else:
            tx_type = "EXPENSE"
            counterpart = kv.get("Nombre y Apellido", kv.get("Nombre", "Desconocido"))

        raw_date = kv.get("Fecha", "")
        if raw_date:
            try:
                tx_date = datetime.strptime(raw_date.strip(), "%d/%m/%Y").date()
            except ValueError:
                tx_date = self._parse_fecha_texto(text)
        else:
            tx_date = self._parse_fecha_texto(text)

        return ParseResult(
            amount=amount,
            tx_type=tx_type,
            counterpart=counterpart,
            date=tx_date,
            account_bank="Banco de Chile",
        )

    @staticmethod
    def _extract_sender_name(soup: BeautifulSoup) -> str:
        for td in soup.find_all("td"):
            td_text = td.get_text(strip=True).lower()
            if "cliente" in td_text and "a tu cuenta" in td_text:
                b_tag = td.find("b")
                if b_tag:
                    return b_tag.get_text(strip=True)
        return "Desconocido"

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
    def _parse_fecha_texto(text: str) -> date:
        m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", text.lower())
        if m:
            day = int(m.group(1))
            month = MESES.get(m.group(2))
            year = int(m.group(3))
            if month:
                return date(year, month, day)

        m2 = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        if m2:
            return datetime.strptime(m2.group(1), "%d/%m/%Y").date()

        return date.today()

    # ------------------------------------------------------------------
    # Notificación de compra / cargo
    # ------------------------------------------------------------------
    def _parse_notification(self, soup: BeautifulSoup, text: str) -> ParseResult:
        text_lower = text.lower()

        # Buscar específicamente "compra/cargo/pago/transferencia por $X" para
        # evitar capturar números de teléfono u otros montos espurios
        amount_match = re.search(
            r"(?:compra|cargo|pago|transferencia)\s+por\s+\$\s?([\d.]+)",
            text_lower,
        )
        if not amount_match:
            amount_match = re.search(r"\$\s?([\d.]+)", text)
        if not amount_match:
            raise ValueError("No se encontró monto en notificación de Banco de Chile")
        amount = int(amount_match.group(1).replace(".", ""))

        if "compra" in text_lower or "cargo" in text_lower or "pago" in text_lower:
            tx_type = "EXPENSE"
        elif "abono" in text_lower or "transferencia recibida" in text_lower:
            tx_type = "INCOME"
        else:
            tx_type = "EXPENSE"

        counterpart = "Desconocido"
        # Formato Edwards/BCH: "...en COMERCIO el DD/MM/YYYY [HH:MM]"
        cp_match = re.search(r"\ben\s+(.+?)\s+el\s+\d{2}/\d{2}/\d{4}", text)
        if cp_match:
            counterpart = cp_match.group(1).strip()

        tx_date = self._parse_fecha_texto(text)

        # Edwards y BCH comparten cuenta en la app post-fusión
        return ParseResult(
            amount=amount,
            tx_type=tx_type,
            counterpart=counterpart,
            date=tx_date,
            account_bank="Banco de Chile",
        )


register(BancoChileParser())
