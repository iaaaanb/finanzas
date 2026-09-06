"""Stub de la API de Gmail para el modo demo.

Implementa el subconjunto exacto que usa `gmail_sync._fetch_emails_after`:

    service.users().messages().list(userId=, q=, maxResults=, pageToken=).execute()
    service.users().messages().get(userId=, id=, format=).execute()

Devuelve mensajes con la misma forma que la API real (headers, internalDate en
milisegundos, body en base64url), así que el código de sync no sabe ni le
importa que del otro lado no haya Google.
"""
import base64
from datetime import datetime, timezone

from app.demo.inbox import build_inbox


def _to_gmail_message(email: dict) -> dict:
    body = base64.urlsafe_b64encode(email["body_html"].encode("utf-8")).decode()
    return {
        "id": email["gmail_message_id"],
        "internalDate": str(int(email["received_at"].timestamp() * 1000)),
        "payload": {
            "mimeType": "text/html",
            "headers": [
                {"name": "From", "value": email["sender"]},
                {"name": "Subject", "value": email["subject"]},
                {"name": "Date", "value": email["received_at"].isoformat()},
            ],
            "body": {"data": body},
        },
    }


def _parse_after(query: str) -> datetime | None:
    """Lee el timestamp de una query estilo Gmail (`after:1717171717`)."""
    for token in (query or "").split():
        if token.startswith("after:"):
            try:
                return datetime.fromtimestamp(int(token[6:]), tz=timezone.utc)
            except ValueError:
                return None
    return None


class _Request:
    """Imita el patrón request/execute del cliente de Google."""

    def __init__(self, payload):
        self._payload = payload

    def execute(self):
        return self._payload


class _Messages:
    def __init__(self, messages: list[dict]):
        self._messages = {m["id"]: m for m in messages}
        self._order = [m["id"] for m in messages]

    def list(self, userId=None, q="", maxResults=None, pageToken=None, **_):
        after = _parse_after(q)
        ids = self._order
        if after is not None:
            cutoff_ms = int(after.timestamp() * 1000)
            ids = [
                mid for mid in ids
                if int(self._messages[mid]["internalDate"]) >= cutoff_ms
            ]
        # Sin paginación: la casilla demo son unos pocos mensajes.
        return _Request({"messages": [{"id": mid} for mid in ids]})

    def get(self, userId=None, id=None, format=None, **_):
        return _Request(self._messages[id])


class _Users:
    def __init__(self, messages: list[dict]):
        self._messages = _Messages(messages)

    def messages(self):
        return self._messages


class FakeGmailService:
    def __init__(self, emails: list[dict] | None = None):
        emails = emails if emails is not None else build_inbox()
        self._users = _Users([_to_gmail_message(e) for e in emails])

    def users(self):
        return self._users
