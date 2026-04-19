"""Muestra el HTML y el texto plano de un email para inspección manual.

Uso:
    # Ver el email más reciente de Banco Edwards
    docker compose exec api python -m app.scripts.dump_email --sender bancoedwards

    # Ver un email específico por ID de la DB
    docker compose exec api python -m app.scripts.dump_email --id 42

    # Mostrar solo texto (sin HTML crudo) — útil para regex testing
    docker compose exec api python -m app.scripts.dump_email --sender bancoedwards --text-only
"""
import argparse

from bs4 import BeautifulSoup
from sqlalchemy import select

from app.database import SessionLocal
from app.models.email import Email


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sender", help="Substring a buscar en el remitente (case-insensitive)")
    parser.add_argument("--id", type=int, help="ID del email en la DB")
    parser.add_argument("--text-only", action="store_true", help="Omitir HTML crudo")
    parser.add_argument("--n", type=int, default=1, help="Cuántos emails mostrar (default 1)")
    args = parser.parse_args()

    if not args.sender and not args.id:
        print("Especifica --sender o --id")
        return

    with SessionLocal() as db:
        query = select(Email).order_by(Email.received_at.desc())
        if args.id:
            query = query.where(Email.id == args.id)
        elif args.sender:
            query = query.where(Email.sender.ilike(f"%{args.sender}%"))
        query = query.limit(args.n)

        emails = db.scalars(query).all()

        if not emails:
            print("No se encontró ningún email.")
            return

        for i, email in enumerate(emails):
            if i > 0:
                print("\n" + "=" * 80 + "\n")

            print(f"ID: {email.id}")
            print(f"Gmail ID: {email.gmail_message_id}")
            print(f"De: {email.sender}")
            print(f"Asunto: {email.subject}")
            print(f"Fecha: {email.received_at}")
            print(f"Status: {email.status.value}")
            print()

            soup = BeautifulSoup(email.body_html, "html.parser")
            text = soup.get_text(separator=" ", strip=True)

            print("--- TEXTO PLANO ---")
            print(text[:3000])
            if len(text) > 3000:
                print(f"... [truncado, total {len(text)} chars]")
            print()

            if not args.text_only:
                print("--- HTML CRUDO ---")
                # Solo los primeros 3000 chars del HTML para no ahogar la terminal
                print(email.body_html[:3000])
                if len(email.body_html) > 3000:
                    print(f"... [truncado, total {len(email.body_html)} chars]")


if __name__ == "__main__":
    main()
