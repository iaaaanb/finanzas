"""Parser para Banco de Chile / Banco Edwards (post-merger, mismo banco).

Los emails transaccionales se distinguen por la combinación remitente + asunto:

| Remitente                                  | Asunto                          | Tipo                       |
|--------------------------------------------|---------------------------------|----------------------------|
| serviciodetransferencias@bancochile.cl     | Aviso de transferencia de fondos| INCOME (TEF recibida)      |
| serviciodetransferencias@bancochile.cl     | Transferencia a Terceros        | EXPENSE (TEF enviada)      |
| enviodigital@bancoedwards.cl               | Cargo en Cuenta                 | EXPENSE (compra con débito)|
| enviodigital@bancochile.cl                 | Cargo en Cuenta                 | EXPENSE (compra con débito)|
"""
import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.parsers.base import BankParser, ParseResult, extract_email_address, last4
from app.parsers.registry import register
from app.parsers.senders import TRANSACTIONAL_SENDERS

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

# Filtrar el registro central por dominio: BCh y Edwards son el mismo banco.
_MINE = frozenset({
    addr for addr in TRANSACTIONAL_SENDERS
    if "bancochile" in addr or "bancoedwards" in addr
})

# Mapeo asunto → handler. Lo hacemos case-insensitive y por substring porque
# Gmail a veces agrega prefijos como "Re:" o sufijos.
SUBJECT_INCOME_TEF = "aviso de transferencia de fondos"
SUBJECT_EXPENSE_TEF = "transferencia a terceros"
SUBJECT_DEBIT_CARGO = "cargo en cuenta"


class BancoChileParser(BankParser):
    def matches(self, sender: str) -> bool:
        return extract_email_address(sender) in _MINE

    def parse(
        self, email_html: str, sender: str = "", subject: str = ""
    ) -> ParseResult:
        soup = BeautifulSoup(email_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)

        subject_lower = subject.lower()
        if SUBJECT_INCOME_TEF in subject_lower:
            return self._parse_tef_income(soup, text)
        if SUBJECT_EXPENSE_TEF in subject_lower:
            return self._parse_tef_expense(soup, text)
        if SUBJECT_DEBIT_CARGO in subject_lower:
            return self._parse_cargo_debito(soup, text)

        raise ValueError(
            f"Asunto no reconocido para Banco de Chile/Edwards: {subject!r}"
        )

    # ------------------------------------------------------------------
    # INCOME TEF: "Aviso de transferencia de fondos"
    # Estructura: campos planos, una sola cuenta (la tuya, "Cuenta destino")
    # ------------------------------------------------------------------
    def _parse_tef_income(self, soup: BeautifulSoup, text: str) -> ParseResult:
        kv = self._extract_kv_flat(soup)

        amount = self._parse_amount(kv.get("Monto") or self._first_amount_in(text))
        counterpart = self._extract_sender_name_from_prose(text)
        tx_date = self._parse_date(kv.get("Fecha"), text)
        # En INCOME hay solo una cuenta, y es la tuya (destino).
        account_number = last4(kv.get("Cuenta destino", ""))

        return ParseResult(
            amount=amount,
            tx_type="INCOME",
            counterpart=counterpart,
            date=tx_date,
            account_bank="Banco de Chile",
            account_number=account_number,
        )

    # ------------------------------------------------------------------
    # EXPENSE TEF: "Transferencia a Terceros"
    # Estructura: secciones Origen / Destino, ambas con "Nº de Cuenta".
    # Tu cuenta es la del Origen, la contraparte está en Destino.
    # ------------------------------------------------------------------
    def _parse_tef_expense(self, soup: BeautifulSoup, text: str) -> ParseResult:
        kv = self._extract_kv_sectioned(soup)

        amount = self._parse_amount(kv.get("Monto") or self._first_amount_in(text))
        counterpart = (
            kv.get("destino_Nombre y Apellido")
            or kv.get("Nombre y Apellido")
            or "Desconocido"
        )
        tx_date = self._parse_date(None, text)
        account_number = last4(
            kv.get("origen_Nº de Cuenta") or kv.get("origen_No de Cuenta", "")
        )

        return ParseResult(
            amount=amount,
            tx_type="EXPENSE",
            counterpart=counterpart,
            date=tx_date,
            account_bank="Banco de Chile",
            account_number=account_number,
        )

    # ------------------------------------------------------------------
    # EXPENSE débito: "Cargo en Cuenta" (Edwards/BCh)
    # Compras con tarjeta de débito. La cuenta se identifica como ****XXXX.
    # ------------------------------------------------------------------
    def _parse_cargo_debito(self, soup: BeautifulSoup, text: str) -> ParseResult:
        text_lower = text.lower()

        m = re.search(
            r"(?:compra|cargo|pago|transferencia)\s+por\s+\$\s?([\d.]+)",
            text_lower,
        )
        if not m:
            m = re.search(r"\$\s?([\d.]+)", text)
        if not m:
            raise ValueError("No se encontró monto en cargo de débito Banco de Chile")
        amount = int(m.group(1).replace(".", ""))

        counterpart = "Desconocido"
        cp_match = re.search(r"\ben\s+(.+?)\s+el\s+\d{2}/\d{2}/\d{4}", text)
        if cp_match:
            counterpart = cp_match.group(1).strip()

        tx_date = self._parse_date(None, text)

        account_number = None
        acc_match = re.search(r"Cuenta\s+\*+(\d{4})", text, re.IGNORECASE)
        if acc_match:
            account_number = acc_match.group(1)

        return ParseResult(
            amount=amount,
            tx_type="EXPENSE",
            counterpart=counterpart,
            date=tx_date,
            account_bank="Banco de Chile",
            account_number=account_number,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_amount(raw: str | None) -> int:
        if not raw:
            raise ValueError("Monto vacío")
        return int(raw.replace("$", "").replace(".", "").strip())

    @staticmethod
    def _first_amount_in(text: str) -> str | None:
        m = re.search(r"\$\s?([\d.]+)", text)
        return m.group(1) if m else None

    @staticmethod
    def _parse_date(raw_iso_es: str | None, text: str) -> date:
        # 1) Si tenemos un campo "DD/MM/YYYY" explícito
        if raw_iso_es:
            try:
                return datetime.strptime(raw_iso_es.strip(), "%d/%m/%Y").date()
            except ValueError:
                pass
        # 2) Buscar "17 de abril de 2026" en prose
        m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", text.lower())
        if m:
            day = int(m.group(1))
            month = MESES.get(m.group(2))
            year = int(m.group(3))
            if month:
                return date(year, month, day)
        # 3) Buscar "DD/MM/YYYY" en prose
        m2 = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        if m2:
            return datetime.strptime(m2.group(1), "%d/%m/%Y").date()
        return date.today()

    @staticmethod
    def _extract_sender_name_from_prose(text: str) -> str:
        """Para INCOME TEF: el nombre del remitente aparece en el cuerpo del email
        como prose: 'nuestro(a) cliente <Nombre> ha efectuado una transferencia
        de fondos a tu cuenta'. Buscamos ese patrón en el texto plano.
        """
        # El paréntesis (a) es literal en el texto ("nuestro(a)"), así que lo
        # escapamos. Capturamos lo que venga entre "cliente" y "ha efectuado".
        m = re.search(
            r"nuestro\(a\)\s+cliente\s+(.+?)\s+ha\s+efectuado",
            text,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
        # Fallback más permisivo por si el formato cambia levemente
        m = re.search(
            r"cliente\s+(.+?)\s+ha\s+efectuado\s+una\s+transferencia",
            text,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).strip()
        return "Desconocido"

    @staticmethod
    def _extract_kv_flat(soup: BeautifulSoup) -> dict[str, str]:
        """Filas <tr> con dos <td>, sin secciones."""
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
    def _extract_kv_sectioned(soup: BeautifulSoup) -> dict[str, str]:
        """Detecta headers 'Origen' y 'Destino' (filas con un solo <td>) y
        prefija los campos siguientes con la sección, para resolver colisiones
        de nombres como 'Nº de Cuenta' que aparece en ambas secciones."""
        kv: dict[str, str] = {}
        section = ""
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) == 1:
                label = tds[0].get_text(strip=True).lower()
                if label in ("origen", "destino"):
                    section = label
                    continue
            if len(tds) == 2:
                key = tds[0].get_text(strip=True)
                val = tds[1].get_text(strip=True)
                if key and val:
                    kv[key] = val
                    if section:
                        kv[f"{section}_{key}"] = val
        return kv


register(BancoChileParser())
