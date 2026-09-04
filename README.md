# Finanzas

Personal finance webapp that reads Chilean bank transaction emails from Gmail,
parses them per-bank, and turns them into pending transactions to confirm and
assign to a budget. Built for real personal use, not a demo — it's been
running in production tracking my own accounts.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.x, Alembic, psycopg3, Python 3.12
- **Frontend**: React 19 + Vite, plain CSS (no framework)
- **DB**: Postgres 16
- **Deploy**: Docker Compose + Caddy, systemd timer for hourly Gmail sync

## Quickstart

```bash
docker compose up -d          # api + postgres, api on :8000
cd frontend && npm run dev    # dev server, proxies /api to :8000
```

Backend needs Gmail OAuth credentials in `credentials/gmail_token.json` to
actually fetch emails (see `docs/DESARROLLO.md` for how to generate one) —
without it, everything except the sync feature works against an empty DB.

## More

Architecture, the parser system (how a bank email becomes a transaction),
account routing rules, the deploy runbook, and a debugging playbook live in
[`docs/DESARROLLO.md`](docs/DESARROLLO.md).
