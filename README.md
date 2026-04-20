# Finanzas — Dev README

Personal finance webapp that scrapes Chilean bank notification emails from Gmail and creates pending transactions. FastAPI + React + Postgres in Docker. Spanish UI/comments.

## Stack & deploy

- **Backend**: FastAPI, SQLAlchemy 2.x, Alembic, psycopg3, Python 3.12
- **Frontend**: React 19 + Vite, plain CSS (no Tailwind)
- **DB**: Postgres 16
- **Local dev**: `docker-compose.yml` — volume-mounts `./backend:/app` with `--reload`, Postgres on host port 5433
- **Prod**: droplet at `finanzas.ian1.cl`, `docker-compose.prod.yml` + Caddy reverse proxy (TLS + SPA fallback), built frontend served from `./frontend/dist`
- **Repo location on droplet**: `/opt/finanzas` (now a real git checkout, was rsync-based before)

## Architecture in one paragraph

Gmail API pulls emails → `email_processor.process_email` stores them and gates them through `TRANSACTIONAL_SENDERS` → if sender is registered, the matching parser runs → parsed emails produce one or more `Transaction` rows in `PENDING` status → user confirms via UI, which adjusts account balance and budget period balance. Non-registered senders go straight to `SKIPPED`. Parse failures land in `PENDING` email status and show up in `/errors` for manual resolution.

## Parser system (the part you'll touch most)

All parser behavior centralizes around two files:

- **`backend/app/parsers/senders.py`** — `TRANSACTIONAL_SENDERS: frozenset[str]`. This is the ONLY gate. Any address not listed here is SKIPPED, period. Adding a new bank or sender starts here.
- **`backend/app/parsers/base.py`** — `BankParser` ABC, `ParseResult` dataclass, `last4()` helper.

Each bank has its own parser file (`banco_chile.py`, `banco_estado.py`, `banco_falabella.py`, `bci.py`). They:

1. Define `_MINE` by filtering `TRANSACTIONAL_SENDERS` by domain substring
2. Implement `matches(sender)` → returns True if address in `_MINE`
3. Implement `parse(email_html, sender, subject)` → returns `ParseResult` or `list[ParseResult]`
4. Register themselves via `register(...)` at module load

**Dispatch convention**: parsers dispatch by **subject**, not by body text. This is critical and was hard-won. Subject strings are stable; body text varies and causes mis-routing. See `banco_chile.py` for the canonical example — three subjects, three handlers:

| Sender | Subject | Type |
|---|---|---|
| `serviciodetransferencias@bancochile.cl` | Aviso de transferencia de fondos | INCOME TEF |
| `serviciodetransferencias@bancochile.cl` | Transferencia a Terceros | EXPENSE TEF |
| `enviodigital@bancoedwards.cl` | Cargo en Cuenta | EXPENSE débito |
| `enviodigital@bancochile.cl` | Cargo en Cuenta | EXPENSE débito |

Banco Edwards = Banco de Chile (post-merger). Same parser handles both domains.

**Note**: `banco_estado.py` STILL does body-text dispatch — known tech debt, should be migrated to subject dispatch eventually.

## Account routing

`ParseResult.account_number` carries the last 4 digits extracted from the email body. `email_processor._resolve_account` matches in this order:

1. Exact match on `Account.account_number` (last 4 digits)
2. Match by `Account.bank` name
3. Fallback to first `Account` (typically "Efectivo")

Account numbers are set per-account in the UI at `/accounts`. Ian's:
- Banco de Chile (Cuenta Vista): `5092`
- BancoEstado CuentaRUT: `9395`
- BancoEstado Ahorro: `5387`

BCI notifications don't include an account number — that parser hardcodes `account_number=None` and relies on bank-name fallback.

Ian can only SEND from Banco de Chile and BancoEstado CuentaRUT. He RECEIVES from all four banks.

## Email → transaction mapping quirks

- **One email, one transaction**: normal case.
- **One email, TWO transactions**: BancoEstado self-transfers (between CuentaRUT and Ahorro). One email produces EXPENSE on origin account + INCOME on destination account. Handled by `BancoEstadoParser._parse_self_transfer` returning a list. This is why `transactions.email_id` does NOT have a UNIQUE constraint (migration `a1b2c3d4e5f6_drop_unique_email_id` dropped it).
- **Section-aware kv extraction**: BCH "Transferencia a Terceros" has Origen/Destino sections both containing `Nº de Cuenta`. `BancoChileParser._extract_kv_sectioned` tracks section context via single-`<td>` header rows and prefixes keys like `origen_Nº de Cuenta` / `destino_Nº de Cuenta`. Important for picking Ian's account (Origen) vs counterpart's (Destino).
- **Counterpart for INCOME TEF** comes from prose regex `nuestro\(a\)\s+cliente\s+(.+?)\s+ha\s+efectuado`, NOT from the kv table. The kv table's `Nombre y Apellido` field is Ian's name (destinatario), not the sender's.

## Scripts (`backend/app/scripts/`)

Run all as `docker compose exec api python -m app.scripts.<name>`.

- `gmail_diagnostic.py` — auth test + date-range backfill. Use `--days N` for how far back. Per-email commit, catches IntegrityError on duplicates, in-memory dedup. The main tool for "pull new emails and parse them".
- `fetch_emails.py` — backfills since last email in DB. Intended for cron but NOT automated yet (see open items).
- `backfill_emails.py` — fixed-count backfill (e.g. last 100 emails). Less useful than gmail_diagnostic.
- `dump_email.py` — `--id N` or `--sender SUBSTR` to inspect email content. `--text-only` for quick regex testing. Essential debugging tool.
- `inspect_senders.py` — shows PARSED/PENDING/SKIPPED counts per sender. Use to spot new senders that might need registry entries or parsers.
- `cleanup_after_parser_fix.py` — wipes PENDING txs + their emails for REGISTERED senders, preserves CONFIRMED. Use after changing parser logic to force reparse.
- `cleanup_non_registered.py` — wipes PENDING txs + their PARSED/PENDING emails for NON-registered senders. Use when you add a sender to the skip list (remove from registry) and want to clean stragglers.
- `close_periods.py` — cron-intended. Closes budget periods whose `period_end` has passed, creates next period. Not automated yet.
- `get_gmail_token.py` — OAuth flow. Run from HOST (not Docker) the FIRST TIME only: `cd backend && python -m app.scripts.get_gmail_token`. Writes `credentials/gmail_token.json`.

## Schema highlights

- `accounts.account_number` — nullable string, last 4 digits for email→account matching (migration `b2c3d4e5f6a7`)
- `transactions.email_id` — nullable, NOT unique (self-transfers make 2 txs per email)
- `transactions.status` — `PENDING` (parser output, not yet applied to balance) or `CONFIRMED` (applied). Only CONFIRMED moves account balance and budget period balance.
- `emails.status` — `PARSED` (parser succeeded), `PENDING` (parser failed, shows in /errors), `SKIPPED` (non-transactional sender)
- `auto_assign_rules` — per-counterpart memory for category + budget. Applied automatically when a parsed email's counterpart matches.
- `budget_periods` — active period has `closed_at IS NULL`. Historical periods keep `final_balance` snapshot.

## Dev workflow

```bash
# Local start
cd ~/finanzas
docker compose up -d
# Frontend dev server with HMR (proxies /api to localhost:8000)
cd frontend && npm run dev

# After changing backend code (auto-reloads):
docker compose logs -f api

# After changing models:
docker compose exec api alembic revision --autogenerate -m "description"
# REVIEW the generated migration before running
docker compose exec api alembic upgrade head

# Backfill a few days of emails
docker compose exec api python -m app.scripts.gmail_diagnostic --days 5

# Inspect a specific email
docker compose exec api python -m app.scripts.dump_email --id 832

# See state of parser health
docker compose exec api python -m app.scripts.inspect_senders
```

## Prod deploy workflow

```bash
# On laptop: commit + push backend changes
git add -A && git commit -m "..." && git push

# On laptop: build frontend (droplet doesn't have Node)
cd frontend && npm run build && cd ..
rsync -avz --delete frontend/dist/ root@finanzas.ian1.cl:/opt/finanzas/frontend/dist/

# SSH to droplet
ssh root@finanzas.ian1.cl

# On droplet:
cd /opt/finanzas
git pull
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
docker compose -f docker-compose.prod.yml build api
docker compose -f docker-compose.prod.yml up -d api
docker compose -f docker-compose.prod.yml restart caddy
```

Private GitHub repo — droplet uses HTTPS with a personal access token stored in git credentials from first pull. SSH deploy keys not set up.

`credentials/` and `.env` are NOT in git. `.env` on droplet holds `DB_PASSWORD`. `credentials/` holds Gmail OAuth files.

## Frontend notes

- Router: `react-router-dom` v7
- No state lib — context + local state only. `RefreshContext` bumps a counter to retrigger sidebar data loads after transaction writes.
- API client: single `src/api.js` with named methods per endpoint. Uses `/api` prefix, Vite dev proxy forwards to `:8000`.
- Styling: CSS variables in `index.css`, dark theme. No component library.
- Pages that matter: `TransactionDetail` (main edit+confirm flow, shows email preview iframe + Gmail deeplink), `ResolveError` (for PENDING-status emails), `Accounts` (where account_number is set).

## Known open items (priority order, discussed)

1. **Automate email fetching**. `fetch_emails.py` exists but nothing runs it. Today Ian runs `gmail_diagnostic --days N` manually. Add a systemd timer on the droplet or a cron entry.
2. **BancoEstado parser still dispatches on body text** (`"el pago se ha realizado"`, `"transferencia electronica"`). Migrate to subject-based dispatch like `banco_chile.py`. Needs real BancoEstado email samples of each type to verify subjects.
3. **Falabella + BCI parsers untested end-to-end**. Will be exercised next time Ian receives money from those banks.
4. **Budget period rollover not automated**. `close_periods.py` exists, no cron.
5. **No balance reconciliation**. App has no way to notice when its view of a balance drifts from reality (missed tx, double-confirmed tx, etc). A "enter your real balance, see delta" flow would help.
6. **Mobile layout unverified**. Sidebar probably breaks on narrow screens.
7. **Frontend dependency on laptop**. Node isn't installed on the droplet. Either `apt install nodejs npm` on droplet or move the frontend build into a Docker stage.

## Recent history (what changed and why)

Ordered roughly chronologically:

1. **Gmail credential recovery** — `credentials/` was gitignored and lost. Re-did OAuth via `get_gmail_token.py`.
2. **Parser architecture refactor** — introduced `TRANSACTIONAL_SENDERS` registry as single source of truth. Each parser filters by domain. Anything not in registry → SKIPPED.
3. **Self-transfer support** — dropped UNIQUE on `transactions.email_id`. BancoEstado parser now returns a list when it detects a self-transfer.
4. **Backfill hardened** — in-memory dedup, per-email commit, IntegrityError catch. Previously one bad email would abort the whole run.
5. **Email context on TransactionDetail** — shows sender, subject, iframe preview, Gmail deeplink. Uses `#all/<gmail_id>` format (not `rfc822msgid`, since we don't store RFC-822 Message-ID header).
6. **Account-number routing** — added `accounts.account_number` nullable column. `_resolve_account` matches email→account by last 4 digits.
7. **Subject-based dispatch for BCH** — replaced body-text sniffing. Fixed EXPENSE TEF that had been mis-extracting counterpart due to Origen/Destino kv collision.
8. **`_extract_kv_sectioned`** — section-aware kv extraction for emails with Origen/Destino structure.
9. **INCOME TEF counterpart fix** — DOM-walking version was grabbing the first `<b>` tag in a `<td>`, which turned out to be Ian's name from the "Estimado(a):" greeting. Switched to regex on prose text: `nuestro\(a\)\s+cliente\s+(.+?)\s+ha\s+efectuado`.
10. **`cleanup_non_registered.py`** — handles the case where emails from a sender that USED TO parse (but no longer does) need to be cleared out along with their stragglers.

## Debugging playbook

**"This email didn't produce a transaction I expected"**:
1. `inspect_senders.py` — is the sender in PARSED bucket, PENDING (parser failure), or SKIPPED (gate said no)?
2. If SKIPPED → sender not in `TRANSACTIONAL_SENDERS`. Decide: should it be? Add if yes.
3. If PENDING → parser threw. Find the email with `dump_email --sender <substr>` and see what went wrong.
4. If PARSED → look at the transaction detail in UI to see what fields were extracted and check against email.

**"Transaction has wrong counterpart / amount / account"**:
1. `dump_email --id N` — see the raw email
2. Trace through the parser's extraction logic by hand
3. Likely fix is a regex adjustment or kv field name change
4. After fixing: `cleanup_after_parser_fix.py` to wipe + reparse

**"New bank sent me an email, nothing happened"**:
1. Most likely SKIPPED — sender not in registry
2. `dump_email --sender <domain>` to confirm and inspect content
3. Add to `senders.py`, create/extend a parser, test

## People & context

User is Ian Berdichewsky. Chilean. Runs this solo. Prefers minimal Gmail API calls (they're slow). Spanish UI text and code comments. Uses Ubuntu on a Thinkpad for dev, Windows for games. Domain `ian1.cl` registered at NIC Chile, DNS via Benza Hosting.
