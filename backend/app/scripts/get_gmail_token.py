"""
Ejecutar UNA VEZ desde tu máquina (no desde Docker) para obtener el token:
    cd backend && python -m app.scripts.get_gmail_token

Abre el navegador, autoriza, y guarda el token en credentials/gmail_token.json.
"""
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CREDENTIALS_PATH = Path(__file__).parent.parent.parent.parent / "credentials" / "gmail_credentials.json"
TOKEN_PATH = Path(__file__).parent.parent.parent.parent / "credentials" / "gmail_token.json"


def main():
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.write_text(creds.to_json())
    print(f"Token guardado en {TOKEN_PATH}")


if __name__ == "__main__":
    main()
