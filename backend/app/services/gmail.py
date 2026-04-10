import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.config import settings

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    token_path = Path(settings.gmail_token_path)
    creds_path = Path(settings.gmail_credentials_path)

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def fetch_new_emails(service, after_timestamp: int | None = None, max_results: int = 50):
    """Obtiene emails nuevos del inbox. Retorna lista de dicts con id, sender, subject, body_html, received_at."""
    import base64
    from datetime import datetime, timezone
    from email.utils import parseaddr

    query = ""
    if after_timestamp:
        query = f"after:{after_timestamp}"

    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg_meta in messages:
        msg = service.users().messages().get(
            userId="me", id=msg_meta["id"], format="full"
        ).execute()

        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
        sender = headers.get("from", "")
        subject = headers.get("subject", "")
        internal_date = int(msg.get("internalDate", 0))
        received_at = datetime.fromtimestamp(internal_date / 1000, tz=timezone.utc)

        # Extraer HTML del body
        body_html = _extract_html(msg["payload"])

        emails.append({
            "gmail_message_id": msg["id"],
            "sender": sender,
            "subject": subject,
            "body_html": body_html or "",
            "received_at": received_at,
        })

    return emails


def _extract_html(payload):
    """Extrae el cuerpo HTML de un mensaje de Gmail."""
    import base64

    if payload.get("mimeType") == "text/html":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    parts = payload.get("parts", [])
    for part in parts:
        result = _extract_html(part)
        if result:
            return result

    return None
