# Finanzas — Dev README

Personal finance webapp that scrapes Chilean bank notification emails from Gmail and creates pending transactions. FastAPI + React + Postgres in Docker. Spanish UI/comments.

## Stack & deploy

- **Backend**: FastAPI, SQLAlchemy 2.x, Alembic, psycopg3, Python 3.12
- **Frontend**: React 19 + Vite, plain CSS (no Tailwind)
- **DB**: Postgres 16
- **Local dev**: `docker-compose.yml` — volume-mounts `./backend:/app` with `--reload`, Postgres on host port 5433
- **Prod**: droplet at `finanzas.ian1.cl`, `docker-compose.prod.yml` + Caddy reverse proxy (TLS + SPA fallback), built frontend served from `./frontend/dist`
- **Repo location on droplet**: `/opt/finanzas` (real git checkout)
- **Cron**: systemd timer `finanzas-sync.timer` triggers hourly incremental sync (see `deploy/`)

## Architecture in one paragraph

Gmail API pulls emails → `email_processor.process_email` stores them and gates them through `TRANSACTIONAL_SENDERS` → if sender is registered, the matching parser runs → parsed emails produce one or more `Transaction` rows in `PENDING` status → user confirms via UI, which adjusts account balance and budget period balance. Non-registered senders go straight to `SKIPPED`. Parse failures land in `PENDING` email status and show up in `/errors` for manual resolution. Gmail fetching runs automatically via the `sync_runs` infrastructure (hourly cron + on-demand from UI).

## Sync system (Gmail fetching)

Three ways to trigger a sync, all converging on `services/gmail_sync.run_sync`:

1. **Cron** — systemd timer fires hourly, runs `app.scripts.run_sync` on the droplet
2. **UI "Sincronizar ahora"** — `POST /api/sync/incremental`, blocks the UI until done
3. **UI backfill** — `POST /api/sync/backfill` with `since_date`, pulls from that date to now

Every run writes a row to `sync_runs` with `status`, `trigger`, timing, counts, and error message. The UI's `/sync` page shows history and last-run status; the sidebar shows a colored dot (gray/yellow/red) for at-a-glance state.

**Concurrency guard**: before starting, `run_sync` checks for a `RUNNING` row started in the last 30 min. If one exists, raises `SyncAlreadyRunningError` (API returns 409). This prevents cron+UI double-fetches without trapping forever on crashed runs (30min stale threshold).

**Incremental boundary**: `max(emails.received_at) - 1 minute` to survive clock skew. If emails is empty, falls back to 30 days ago.

**Authentication**: Gmail OAuth refresh token in `credentials/gmail_token.json`. If it gets the dreaded `invalid_grant: Bad Request` (refresh token expired/revoked), re-run `app.scripts.get_gmail_token` from HOST (not Docker), then rsync the fresh file to prod. See "Known issues" below for the OAuth-testing-mode gotcha.

## Parser system (the part you'll touch most)

All parser behavior centralizes around two files:

- **`backend/app/parsers/senders.py`** — `TRANSACTIONAL_SENDERS: frozenset[str]`. This is the ONLY gate. Any address not listed here is SKIPPED, period. Adding a new bank or sender starts here.
- **`backend/app/parsers/base.py`** — `BankParser` ABC, `ParseResult` dataclass, `last4()` helper.

Each bank has its own parser file (`banco_chile.py`, `banco_estado.py`, `banco_falabella.py`, `bci.py`). They:

1. Define `_MINE` by filtering `TRANSACTIONAL_SENDERS` by domain substring
2. Implement `matches(sender)` → returns True if address in `_MINE`
3. Implement `parse(email_html, sender, subject)` → returns `ParseResult` or `list[ParseResult]`
4. Register themselves via `register(...)` at module load

**Dispatch convention**: parsers dispatch by **subject**, not by body text. This is critical. Subject strings are stable; body text varies and causes mis-routing. See `banco_chile.py` for the canonical example — three subjects, three handlers:

| Sender | Subject | Type |
|---|---|---|
| `serviciodetransferencias@bancochile.cl` | Aviso de transferencia de fondos | INCOME TEF |
| `serviciodetransferencias@bancochile.cl` | Transferencia a Terceros | EXPENSE TEF |
| `enviodigital@bancoedwards.cl` | Cargo en Cuenta | EXPENSE débito |
| `enviodigital@bancochile.cl` | Cargo en Cuenta | EXPENSE débito |

Banco Edwards = Banco de Chile (post-merger). Same parser handles both domains.

**Note**: `banco_estado.py` STILL does body-text dispatch — known tech debt, should be migrated to subject dispatch eventually.

## Account routing

`ParseResult.account_number` carries the last 4 digits extracted from the email body (when available). `email_processor._resolve_account` matches in this order:

1. Exact match on `Account.account_number`
2. Match by `Account.bank` name (exact string)
3. Fallback to first `Account` (typically "Efectivo")

**CRITICAL — `Account.bank` must match parser-emitted strings exactly.** These are the strings parsers produce, and therefore the only valid values for the `bank` field of each account:

| Account | Required `bank` value | `account_number` |
|---|---|---|
| Efectivo | `Efectivo` | (blank) |
| Banco de Chile (FAN) | `Banco de Chile` | `5092` |
| BancoEstado CuentaRUT | `BancoEstado CuentaRUT` | `4300` |
| BancoEstado Ahorro | `BancoEstado Ahorro` | `5387` |

NOT `"Banco Estado"` (two words), NOT `"BancoEstado"` alone. Exact strings. The parsers break if these drift.

### BCh routing edge case (business rule, Apr 2026)

**Ian has only ONE Banco de Chile account (FAN).** Therefore:

- **EXPENSE from BCh** — parser returns `account_number=None` and just `account_bank="Banco de Chile"`. Matches by bank name unambiguously (only one BCh row).
- **INCOME from BCh** — parser DOES extract `account_number` (from `Cuenta destino` in `Aviso de transferencia de fondos`) because Ian can receive money to any account (including BancoEstado, in the weird case where another BCh customer sends money to his BancoEstado account and the notification still comes from bancochile.cl).

**If you ever add a second BCh account**, the EXPENSE simplification breaks and you'll need to re-add `account_number` extraction for the Origen section in `banco_chile._parse_tef_expense` / `_parse_cargo_debito`.

BCI notifications don't include an account number — that parser hardcodes `account_number=None` and relies on bank-name fallback.

Ian can only SEND from Banco de Chile and BancoEstado CuentaRUT. He RECEIVES from all four banks.

## Email → transaction mapping quirks

- **One email, one transaction**: normal case.
- **One email, TWO transactions**: BancoEstado self-transfers (between CuentaRUT and Ahorro). One email produces EXPENSE on origin account + INCOME on destination account. Handled by `BancoEstadoParser._parse_self_transfer` returning a list. This is why `transactions.email_id` does NOT have a UNIQUE constraint (migration `a1b2c3d4e5f6_drop_unique_email_id` dropped it).
- **Section-aware kv extraction**: BCH "Transferencia a Terceros" has Origen/Destino sections both containing `Nº de Cuenta`. `BancoChileParser._extract_kv_sectioned` tracks section context via single-`<td>` header rows and prefixes keys like `origen_Nº de Cuenta` / `destino_Nº de Cuenta`. Important for picking Ian's account (Origen) vs counterpart's (Destino). Currently used only in INCOME flow — EXPENSE ignores Origen because of the business rule above.
- **Counterpart for INCOME TEF** comes from prose regex `nuestro\(a\)\s+cliente\s+(.+?)\s+ha\s+efectuado`, NOT from the kv table. The kv table's `Nombre y Apellido` field is Ian's name (destinatario), not the sender's.

## Auto-assign rules & auto-confirm

`auto_assign_rules` remembers per-counterpart defaults: category + budget. Applied automatically when a parsed email's counterpart matches.

**New (Apr 2026)**: the `auto_confirm` boolean on each rule. When a parser creates a transaction whose counterpart has `auto_confirm=true` AND all confirmation requirements are met (budget_period set for EXPENSE, account exists), the transaction is confirmed at parse time instead of sitting in PENDING. Activated from the UI via "Aceptar automáticamente" on `TransactionDetail` (button appears only when category + budget are both set).

The enable endpoint (`POST /api/auto-assign-rules/enable-auto-confirm/{counterpart}`) also sweeps existing PENDING txs with that counterpart and confirms whichever qualify. Response includes `retroactive_confirmed` and `retroactive_skipped` counts so the UI can show a useful banner.

**Important**: `process_email` does NOT swallow `confirm_transaction` exceptions. If auto-confirm fails (e.g. stale budget, missing account), the whole parse rolls back and the email lands in `/errors` with `status=PENDING`. This is intentional — silent half-confirmation caused hours of debugging before.

## Schema highlights

- `accounts.account_number` — nullable string, last 4 digits for email→account matching (migration `b2c3d4e5f6a7`)
- `transactions.email_id` — nullable, NOT unique (self-transfers make 2 txs per email)
- `transactions.status` — `PENDING` (parser output, not yet applied to balance) or `CONFIRMED` (applied). Only CONFIRMED moves account balance and budget period balance.
- `emails.status` — `PARSED` (parser succeeded), `PENDING` (parser failed, shows in /errors), `SKIPPED` (non-transactional sender)
- `auto_assign_rules.auto_confirm` — boolean, default false (migration `d4e5f6a7b8c9`)
- `sync_runs` — one row per sync attempt with timing, counts, error message (migration `c3d4e5f6a7b8`)
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

# Backfill a few days of emails (the modern way: from /sync in the UI).
# Or via CLI:
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

# CRITICAL: rebuild the image BEFORE running migrations. Prod doesn't volume-mount
# ./backend, so new migration files aren't visible to alembic until rebuild.
docker compose -f docker-compose.prod.yml build api

# Run migrations using `run --rm` (not `exec`) so we don't need the api container
# to already be running — handy if the new code crashes on startup for any reason.
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head

docker compose -f docker-compose.prod.yml up -d api
# Caddy usually doesn't need restarting, but if SPA routing breaks:
docker compose -f docker-compose.prod.yml restart caddy
```

Private GitHub repo — droplet uses HTTPS with a personal access token stored in git credentials from first pull. SSH deploy keys not set up.

`credentials/` and `.env` are NOT in git. `.env` on droplet holds `DB_PASSWORD`. `credentials/` holds Gmail OAuth files — push manually after regenerating:

```bash
rsync -avz ~/finanzas/credentials/gmail_token.json \
  root@finanzas.ian1.cl:/opt/finanzas/credentials/gmail_token.json
```

## systemd timer (hourly sync on prod)

Service + timer units live in `deploy/`. One-time install on the droplet:

```bash
cp /opt/finanzas/deploy/finanzas-sync.service /etc/systemd/system/
cp /opt/finanzas/deploy/finanzas-sync.timer   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now finanzas-sync.timer
```

Check status / logs:
```bash
systemctl list-timers finanzas-sync.timer
journalctl -u finanzas-sync.service -n 50 --no-pager
systemctl start finanzas-sync.service   # trigger manually without waiting
```

See `deploy/README.md` for more.

## Nuking the DB (reset to empty)

If everything's screwed up and you want to start from scratch:

```bash
docker compose -f docker-compose.prod.yml down
docker volume rm finanzas_pgdata  # or -f if in use
docker compose -f docker-compose.prod.yml up -d db
sleep 5
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head
docker compose -f docker-compose.prod.yml up -d          # note: full `up` to also bring caddy back
curl -i https://finanzas.ian1.cl/api/health
```

The `seed_default_account` lifespan hook will re-create "Efectivo" on first api startup. You then re-add your other accounts via UI using the exact bank strings from the account routing table above.

## Frontend notes

- Router: `react-router-dom` v7
- No state lib — context + local state only. `RefreshContext` bumps a counter to retrigger sidebar data loads after transaction writes.
- API client: single `src/api.js` with named methods per endpoint. Uses `/api` prefix, Vite dev proxy forwards to `:8000`. The `request()` helper attaches `.status` and `.detail` to thrown errors so callers can distinguish 409 conflicts etc.
- Styling: CSS variables in `index.css`, dark theme. No component library.
- Mobile: `Layout.jsx` detects `window.innerWidth < 768` and renders a hamburger button + slide-out drawer. Sidebar auto-closes on route change.
- Pages that matter: `TransactionDetail` (main edit+confirm flow, shows email preview iframe + Gmail deeplink, houses the "Aceptar automáticamente" button), `ResolveError` (for PENDING-status emails), `Accounts` (where account_number is set), `Sync` (sync status + history + backfill).

## Known issues / gotchas

- **Gmail OAuth token expires every 7 days** if the app is in "testing" mode on Google Cloud Console. Publishing to "in production" (unverified is fine for single-user) makes refresh tokens stable. See https://console.cloud.google.com → APIs & Services → OAuth consent screen → Publishing status.
- **Don't use `docker compose exec` for heredocs / multi-line SQL** — no TTY. Use `exec -T`, or pipe the SQL into psql, or just edit via the UI.
- **After `git pull` on droplet, ALWAYS rebuild the api image before running migrations.** Prod doesn't mount the source directory, so new migration files are invisible to alembic until the image is rebuilt. Symptom: `alembic upgrade head` says "already at head" but schema is wrong.
- **`cleanup_after_parser_fix.py` preserves CONFIRMED transactions.** If confirms were created by a buggy auto-confirm rule, clean them with raw SQL (reverting balances as you go) instead of the script.

## Open items (priority order)

1. ~~**Automate email fetching**~~ — DONE (systemd timer + UI trigger + backfill).
2. **BancoEstado parser still dispatches on body text** (`"el pago se ha realizado"`, `"transferencia electronica"`). Migrate to subject-based dispatch like `banco_chile.py`. Needs real BancoEstado email samples of each type to verify subjects.
3. **Falabella + BCI parsers untested end-to-end**. Will be exercised next time Ian receives money from those banks.
4. **Budget period rollover not automated**. `close_periods.py` exists, no cron. Easy addition to systemd — new timer unit calling a new scripts module.
5. **No balance reconciliation**. App has no way to notice when its view of a balance drifts from reality (missed tx, double-confirmed tx, etc). A "enter your real balance, see delta" flow would help.
6. **Frontend dependency on laptop**. Node isn't installed on the droplet. Either `apt install nodejs npm` on droplet or move the frontend build into a Docker stage.
7. **Publish Gmail OAuth app to "production"** to stop weekly token expirations. See Known issues above.
8. **Old script consolidation**. `gmail_diagnostic.py`, `fetch_emails.py`, `backfill_emails.py` all bypass `sync_runs`. Replace their bodies with calls to `run_sync(trigger=...)` so manual CLI runs also show up in the /sync history.

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
9. **INCOME TEF counterpart fix** — DOM-walking version was grabbing the first `<b>` tag in a `<td>`, which turned out to be Ian's name from the "Estimado(a):" greeting. Switched to regex on prose text.
10. **`cleanup_non_registered.py`** — handles the case where emails from a sender that USED TO parse (but no longer does) need to be cleared out along with their stragglers.
11. **Sync infrastructure** — `sync_runs` table + `services/gmail_sync.run_sync` + `/api/sync/*` endpoints + systemd timer + `/sync` UI page. Closed open item #1.
12. **BCh EXPENSE routing simplification** — dropped account_number extraction for expenses since Ian has only one BCh account. Bank-name match is sufficient and more robust.
13. **Navigate-back-on-confirm** — `TransactionDetail` now returns to the previous page after confirming, instead of staying on the detail page. Faster workflow for processing a pending queue.
14. **Auto-confirm** — `auto_assign_rules.auto_confirm` column + "Aceptar automáticamente" button + parse-time auto-confirm path. Retroactive sweep on enable.
15. **Mobile sidebar** — hamburger + slide-out drawer below 768px. Sidebar auto-closes on route change. Main-content padding adjusts so the hamburger doesn't overlap content.
16. **Rollback hardening in `process_email`** — earlier version swallowed `confirm_transaction` errors and left SQLAlchemy sessions in `InFailedSqlTransaction` state, which then poisoned the rest of the batch. Now: any error in the parse/create/confirm critical path triggers a proper `db.rollback()` followed by a clean re-insert of the email with `status=PENDING`.

## Debugging playbook

**"This email didn't produce a transaction I expected"**:
1. `inspect_senders.py` — is the sender in PARSED bucket, PENDING (parser failure), or SKIPPED (gate said no)?
2. If SKIPPED → sender not in `TRANSACTIONAL_SENDERS`. Decide: should it be? Add if yes.
3. If PENDING → parser threw. Find the email with `dump_email --sender <substr>` and see what went wrong.
4. If PARSED → look at the transaction detail in UI to see what fields were extracted and check against email.

**"Transaction has wrong counterpart / amount / account"**:
1. `dump_email --id N` — see the raw email
2. Trace through the parser's extraction logic by hand, OR run the parser directly:
   ```bash
   docker compose exec api python -c "
   from app.database import SessionLocal
   from app.models.email import Email
   from app.parsers.registry import find_parser
   with SessionLocal() as db:
       e = db.get(Email, 511)
       print(find_parser(e.sender).parse(e.body_html, sender=e.sender, subject=e.subject))
   "
   ```
3. If the parser result is right but the tx is wrong, it's the `_resolve_account` path. Check `Account.bank` strings match what parsers emit exactly (see the routing table above).
4. After fixing: `cleanup_after_parser_fix.py` to wipe + reparse.

**"New bank sent me an email, nothing happened"**:
1. Most likely SKIPPED — sender not in registry
2. `dump_email --sender <domain>` to confirm and inspect content
3. Add to `senders.py`, create/extend a parser, test

**"Sync says FAILED, what happened"**:
1. Go to `/sync` in the UI — the history row shows `error_message`
2. If it's `invalid_grant` — OAuth token expired, re-run `get_gmail_token.py` from host, rsync to droplet
3. If it's something else — check `journalctl -u finanzas-sync.service -n 50` on the droplet
4. After fixing auth, hit "Traer emails nuevos" from the UI (it'll run just like the cron)

## People & context

User is Ian Berdichewsky. Chilean. Runs this solo. Prefers minimal Gmail API calls (they're slow). Spanish UI text and code comments. Uses Ubuntu on a Thinkpad for dev, Windows for games. Domain `ian1.cl` registered at NIC Chile, DNS via Benza Hosting.
