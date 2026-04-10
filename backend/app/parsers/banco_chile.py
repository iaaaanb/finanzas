import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.parsers.base import BankParser, ParseResult
from app.parsers.registry import register

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


class BancoChileParser(BankParser):
    def matches(self, sender: str) -> bool:
        s = sender.lower()
        return "bancochile" in s or "banco de chile" in s

    def parse(self, email_html: str) -> ParseResult:
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

        # --- Monto ---
        raw_amount = kv.get("Monto", "")
        if not raw_amount:
            m = re.search(r"\$\s?([\d.]+)", text)
            if not m:
                raise ValueError("No se encontró monto en TEF de Banco de Chile")
            raw_amount = m.group(1)
        amount = int(raw_amount.replace("$", "").replace(".", "").strip())

        # --- Tipo y contraparte ---
        text_lower = text.lower()
        if "a tu cuenta" in text_lower or "fondos a tu" in text_lower:
            # Transferencia recibida:
            # "nuestro(a) cliente <b>Nombre</b> ha efectuado..."
            tx_type = "INCOME"
            counterpart = self._extract_sender_name(soup)
        else:
            # Transferencia enviada:
            # Contraparte en card "Destino" → "Nombre y Apellido"
            tx_type = "EXPENSE"
            counterpart = kv.get("Nombre y Apellido", kv.get("Nombre", "Desconocido"))

        # --- Fecha ---
        # Primero intentar del kv (campo "Fecha" → "22/03/2026")
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
        """Extrae el nombre del remitente desde 'nuestro(a) cliente <b>Nombre</b>'."""
        for td in soup.find_all("td"):
            td_text = td.get_text(strip=True).lower()
            if "cliente" in td_text and "a tu cuenta" in td_text:
                b_tag = td.find("b")
                if b_tag:
                    return b_tag.get_text(strip=True)
        return "Desconocido"

    @staticmethod
    def _extract_kv(soup: BeautifulSoup) -> dict[str, str]:
        """Extrae pares clave/valor de filas <tr> con 2 <td>: [Label] [Valor]."""
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
        """Parsea 'viernes 20 de marzo de 2026 12:41' o 'DD/MM/YYYY'."""
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
    # Notificación de compra / cargo (formato inline)
    # ------------------------------------------------------------------
    def _parse_notification(self, soup: BeautifulSoup, text: str) -> ParseResult:
        amount_match = re.search(r"\$\s?([\d.]+)", text)
        if not amount_match:
            raise ValueError("No se encontró monto en email de Banco de Chile")
        amount = int(amount_match.group(1).replace(".", ""))

        text_lower = text.lower()
        if "compra" in text_lower or "pago" in text_lower:
            tx_type = "EXPENSE"
        elif "transferencia recibida" in text_lower or "abono" in text_lower:
            tx_type = "INCOME"
        else:
            tx_type = "EXPENSE"

        counterpart = "Desconocido"
        cp_match = re.search(r"\ben\s+(.+?)\s+el\s+\d{2}/\d{2}/\d{4}", text)
        if cp_match:
            counterpart = cp_match.group(1).strip()

        tx_date = self._parse_fecha_texto(text)

        return ParseResult(
            amount=amount,
            tx_type=tx_type,
            counterpart=counterpart,
            date=tx_date,
            account_bank="Banco de Chile",
        )


register(BancoChileParser())
