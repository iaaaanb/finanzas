import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from app.parsers.base import BankParser, ParseResult, extract_email_address, last4
from app.parsers.registry import register
from app.parsers.senders import TRANSACTIONAL_SENDERS

_PRODUCT_MAP = {
    "cuentarut": "BancoEstado CuentaRUT",
    "cuenta de ahorro": "BancoEstado Ahorro",
    "cuenta ahorro": "BancoEstado Ahorro",
    "vista pension alimenticia": "BancoEstado Ahorro",
}

_MINE = frozenset({
    addr for addr in TRANSACTIONAL_SENDERS if "bancoestado" in addr
})


class BancoEstadoParser(BankParser):
    def matches(self, sender: str) -> bool:
        return extract_email_address(sender) in _MINE

    def parse(
        self, email_html: str, sender: str = "", subject: str = ""
    ) -> ParseResult | list[ParseResult]:
        soup = BeautifulSoup(email_html, "html.parser")
        text = soup.get_text(separator=" ", strip=True)
        text_lower = text.lower()

        if "el pago se ha realizado" in text_lower:
            return self._parse_self_transfer(soup, text)
        if "transferencia electronica" in text_lower:
            return self._parse_tef(soup, text)
        return self._parse_notification(soup, text)

    # ------------------------------------------------------------------
    # Transferencia entre cuentas propias (1 email = 2 transacciones)
    # ------------------------------------------------------------------
    def _parse_self_transfer(
        self, soup: BeautifulSoup, text: str,
    ) -> list[ParseResult]:
        kv = self._extract_kv_th(soup)

        raw_amount = kv.get("Monto Total", "")
        if not raw_amount:
            m = re.search(r"\$\s?([\d.]+)", text)
            if not m:
                raise ValueError("No se encontró monto en pago BancoEstado")
            raw_amount = m.group(1)
        amount = int(raw_amount.replace("$", "").replace(".", "").strip())

        origin = self._resolve_account(kv.get("origen_product", ""))
        dest = self._resolve_account(kv.get("destino_product", ""))

        # Números de cuenta para cada lado
        origin_number = last4(kv.get("origen_account_number", ""))
        dest_number = last4(kv.get("destino_account_number", ""))

        raw_date = kv.get("Fecha y hora", "")
        if raw_date:
            try:
                tx_date = datetime.strptime(raw_date.split()[0], "%d/%m/%Y").date()
            except (ValueError, IndexError):
                tx_date = date.today()
        else:
            tx_date = date.today()

        return [
            ParseResult(
                amount=amount,
                tx_type="EXPENSE",
                counterpart=f"Transferencia a {dest}",
                date=tx_date,
                account_bank=origin,
                account_number=origin_number,
            ),
            ParseResult(
                amount=amount,
                tx_type="INCOME",
                counterpart=f"Transferencia desde {origin}",
                date=tx_date,
                account_bank=dest,
                account_number=dest_number,
            ),
        ]

    @staticmethod
    def _extract_kv_th(soup: BeautifulSoup) -> dict[str, str]:
        """Extrae kv del formato self-transfer.
        Identifica también secciones Origen/Destino y prefija sus campos.
        """
        kv: dict[str, str] = {}
        section = ""
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td", recursive=False)
            ths = tr.find_all("th", recursive=False)

            # Detectar sección
            if len(tds) == 1 and not ths:
                label = tds[0].get_text(strip=True).rstrip(":")
                if label.lower() in ("origen", "destino"):
                    section = label.lower()
                    continue

            if len(tds) == 1 and len(ths) == 1:
                key = tds[0].get_text(strip=True)
                val = ths[0].get_text(strip=True)
                if key and val:
                    kv[key] = val
                    key_lower = key.lower().rstrip(":")
                    if section:
                        if key_lower == "producto":
                            kv[f"{section}_product"] = val
                        elif key_lower == "n° de cuenta" or key_lower == "no de cuenta" or "cuenta" in key_lower:
                            kv[f"{section}_account_number"] = val
        return kv

    # ------------------------------------------------------------------
    # TEF: comprobante de transferencia
    # ------------------------------------------------------------------
    def _parse_tef(self, soup: BeautifulSoup, text: str) -> ParseResult:
        amount_match = re.search(r"Monto\s+transferido\s*:\s*\$\s?([\d.]+)", text)
        if not amount_match:
            raise ValueError("No se encontró monto en TEF de BancoEstado")
        amount = int(amount_match.group(1).replace(".", ""))

        kv = self._extract_kv_colon(soup)

        counterpart = kv.get("Nombre", "Desconocido")

        raw_date = kv.get("Fecha y Hora de TEF", "")
        if raw_date:
            try:
                tx_date = datetime.strptime(raw_date.split()[0], "%d/%m/%Y").date()
            except (ValueError, IndexError):
                tx_date = date.today()
        else:
            tx_date = date.today()

        account_bank = self._resolve_account(kv.get("Producto", ""))
        # En TEF el "N° de Cuenta" es la nuestra (la cuenta origen del cargo)
        account_number = last4(kv.get("N° de Cuenta", "")) or last4(kv.get("No de Cuenta", ""))

        return ParseResult(
            amount=amount,
            tx_type="EXPENSE",
            counterpart=counterpart,
            date=tx_date,
            account_bank=account_bank,
            account_number=account_number,
        )

    @staticmethod
    def _extract_kv_colon(soup: BeautifulSoup) -> dict[str, str]:
        kv: dict[str, str] = {}
        for tr in soup.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) == 3:
                mid = tds[1].get_text(strip=True)
                if mid == ":":
                    key = tds[0].get_text(strip=True)
                    val = tds[2].get_text(strip=True)
                    if key and val:
                        kv[key] = val
        return kv

    @staticmethod
    def _resolve_account(product: str) -> str:
        product_lower = product.lower().strip()
        for key, value in _PRODUCT_MAP.items():
            if key in product_lower:
                return value
        return "BancoEstado CuentaRUT"

    # ------------------------------------------------------------------
    # Notificación simple ("cuenta terminada en ****9395")
    # ------------------------------------------------------------------
    def _parse_notification(self, soup: BeautifulSoup, text: str) -> ParseResult:
        amount_match = re.search(r"\$\s?([\d.]+)", text)
        if not amount_match:
            raise ValueError("No se encontró monto en email de BancoEstado")
        amount = int(amount_match.group(1).replace(".", ""))

        text_lower = text.lower()
        if "transferencia recibida" in text_lower or "abono" in text_lower:
            tx_type = "INCOME"
        else:
            tx_type = "EXPENSE"

        counterpart = "Desconocido"
        cp_match = re.search(
            r"(?:de|para|a)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)",
            text,
        )
        if cp_match:
            counterpart = cp_match.group(1).strip()

        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        if date_match:
            tx_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date()
        else:
            tx_date = date.today()

        # "cuenta terminada en ****9395"
        account_number = None
        acc_match = re.search(
            r"cuenta\s+terminada\s+en\s+\*+(\d{4})",
            text, re.IGNORECASE,
        )
        if acc_match:
            account_number = acc_match.group(1)

        return ParseResult(
            amount=amount,
            tx_type=tx_type,
            counterpart=counterpart,
            date=tx_date,
            account_bank="BancoEstado CuentaRUT",
            account_number=account_number,
        )


register(BancoEstadoParser())
