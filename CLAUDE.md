# PC Club — management system for PC clubs in Kazakhstan

A Senet/Langame-style product. Four parts in one monorepo:

| Part | Folder | Stack | Status |
|---|---|---|---|
| Backend API | `backend/` | FastAPI, PostgreSQL 17, SQLAlchemy 2 (async, asyncpg), Alembic | **phase 1 done** |
| Customer mobile app | `mobile/` | React Native + Expo (TypeScript) | phase 2, not started |
| Admin panel for club owners | `admin/` | React + Vite (TypeScript) | phase 3, not started |
| Windows client for club PCs | `client/` | TBD | phase 4, not started |

Customers register with phone + IIN, browse PCs by club/zone, book a PC for a time slot, pay by
card or Kaspi, and see their booking history.

## Commands (run from `backend/`)

Windows, Git Bash syntax. In PowerShell use `.venv\Scripts\python`.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"            # add ,embedded-pg for a throwaway test DB
.venv/Scripts/alembic upgrade head                          # apply migrations (DATABASE_URL)
.venv/Scripts/python -m uvicorn app.main:app --reload       # API at http://127.0.0.1:8000/docs
.venv/Scripts/python -m pytest                              # all tests
.venv/Scripts/python -m pytest tests/unit                   # pure domain tests, no database
.venv/Scripts/python -m pytest tests/integration -rs        # API tests, shows skip reasons
.venv/Scripts/ruff check . && .venv/Scripts/ruff format .   # lint + format
.venv/Scripts/alembic revision --autogenerate -m "..."      # new migration (review it by hand)
.venv/Scripts/python -m app.cli create-owner --org "..." --email ...   # first admin account
.venv/Scripts/python -m app.cli seed-demo                   # demo clubs/zones/PCs (dev only)
```

Config comes from environment variables or `backend/.env` (gitignored; see `.env.example`).
`ENVIRONMENT=prod` refuses to start with dev secrets or a fixed OTP code.

## Backend layout

```
backend/app/
  main.py            app factory, router wiring
  cli.py             operator commands
  core/              config, db session, security (JWT, hashing, IIN crypto), errors, clock
  domain/            PURE business rules: iin, age_rule, slots, pricing, phone
  models/            SQLAlchemy models (import new ones in models/__init__.py)
  schemas/           Pydantic request/response models
  integrations/      external services behind Protocols + mocks, wired in registry.py
    identity/  payments/  sms/
  services/          use-cases; own the transaction (commit here)
  api/deps.py        FastAPI dependencies (session, clock, current user/staff, providers)
  api/v1/            thin routers; api/v1/admin/ for staff endpoints
backend/alembic/versions/   0001 schema, 0002 booking overlap constraints
backend/tests/unit/         domain tests
backend/tests/integration/  API tests against real PostgreSQL (see conftest.py docstring)
```

## Architecture rules

- **Layering:** router → service → domain. Routers only parse input and shape output. Services
  hold the use-case and call `session.commit()`. `domain/` has no I/O at all — no database, no
  HTTP, no `datetime.now()`; everything it needs is passed in.
- **Time:** store `timestamptz` (UTC). Every club has an IANA `timezone` (default `Asia/Almaty`,
  UTC+5); anything about "time of day" is evaluated in club-local time. Never call
  `datetime.now()` in application code — take the time from the injected `Clock`
  (`app/core/clock.py`), so tests can control it. Naive datetimes are rejected at the API.
- **Money:** whole tenge as `int`, column/field suffix `_kzt`. No floats, no Decimal.
- **IDs:** UUIDv7 (`uuid.uuid7()`), generated in the app. They are time-ordered and double as
  pagination cursors.
- **Enums:** `StrEnum` in code, `VARCHAR` + `CHECK` constraint in the database (no PG enum types).
- **Errors:** raise `AppError(code, message, status)`. Every error response is
  `{"error": {"code", "message", "details"}}`. Clients localize by `code` (ru/kk/en), so codes are
  API contract: add new ones freely, never rename existing ones.
- **Integrations:** external systems (eGov IIN lookup, card acquirer, Kaspi, SMS) are
  `typing.Protocol`s in `integrations/<kind>/base.py` with a mock next to them. Only mocks exist
  so far. A real adapter = new file implementing the Protocol + one line in
  `integrations/registry.py`; services must not change. Selection is by settings
  (`IDENTITY_PROVIDER`, `PAYMENT_PROVIDER_CARD`, `PAYMENT_PROVIDER_KASPI`, `SMS_PROVIDER`).
- **Multi-tenancy:** `organizations` → `clubs` → `zones` → `pcs`. Staff are scoped to one
  organization; every admin query filters by `staff.organization_id` and answers 404 (not 403)
  for other organizations' data. Customers are global.
- **PII:** the IIN is stored encrypted (Fernet) plus an HMAC for uniqueness, returned only
  masked, and never logged. Kazakhstan law requires storing citizens' personal data on servers
  inside Kazakhstan — relevant for production hosting.

## Domain rules

**IIN** (`domain/iin.py`): 12 digits — `YYMMDD`, century/sex digit (1–2 → 18xx, 3–4 → 19xx,
5–6 → 20xx; odd = male), 4-digit serial, check digit (weights 1..11 mod 11; if 10, second pass
with weights 3..11,1,2; if 10 again the IIN is invalid). Local parsing is only a filter; the
birth date returned by the `IdentityVerifier` is authoritative and must match the IIN.

**Age rule** (`domain/age_rule.py`): users under 18 cannot book or play during
`[22:00, 06:00)` club-local time.
- Half-open window: ending at exactly 22:00 is allowed, starting at exactly 06:00 is allowed.
- A booking is rejected if *any* instant of it is both at night and before adulthood.
- Adulthood starts at 00:00 club-local on the 18th birthday (`adult_from()`; 29 Feb → 1 Mar).
  This is the only place that encodes that interpretation.
- Age is known only for identity-verified users, so unverified users cannot book at all.
- Enforced in `services/booking.create_booking` → `MINOR_NIGHT_RESTRICTION` (403).
  `can_play_at()` is the single-instant form for the future PC client (session start, forced
  logout at 22:00).

**Booking lifecycle** (`services/booking.py`, `services/payment.py`):

```
pending_payment ──payment within hold──▶ confirmed ──▶ completed
      │                                      └─cancel before start─▶ cancelled (refund)
      └─hold (10 min) runs out─▶ expired
```
- Slots: in the future, aligned to 30 min, 1–12 h, at most 14 days ahead, inside opening hours.
- **Double booking is prevented by PostgreSQL exclusion constraints** (migration 0002,
  `btree_gist`): no overlapping active bookings per PC, and none per user. The service only maps
  the violation to `SLOT_TAKEN` / `USER_BOOKING_OVERLAP`. Do not replace this with a
  check-then-insert in Python.
- Unpaid holds are expired lazily (on create/list/get/pay); availability queries ignore them.
- A booking is confirmed **only** by a verified provider webhook, never by a client call.
  Payments arriving late, twice, or for a cancelled booking are refunded automatically.
- Paying requires an `Idempotency-Key` header; replays return the original payment.
- Row-lock order is always booking, then payment.

**Auth:** customers log in with phone + SMS code (account created on first login), then verify
identity with `POST /v1/me/identity`. Staff use email + password. Both get a JWT access token
(30 min) and a rotating refresh token; replaying a rotated refresh token revokes all sessions.

## Testing rules

- Every change to a rule in `domain/` needs unit tests, including boundary cases.
- Behaviour that depends on the database is tested against real PostgreSQL through the API —
  never with SQLite or a mocked session.
- Integration tests run inside a rolled-back transaction per test and use `FixedClock`
  (starts at 2026-06-01 12:00 Almaty). Advancing the clock past 30 min expires access tokens.
- Tests marked `requires_overlap_constraints` need a real PostgreSQL (`TEST_DATABASE_URL`, a
  database whose name contains `test`). The optional embedded server lacks `btree_gist`, so those
  tests are skipped there — a green run with skips does not prove overlap protection.
- Schema changes go through Alembic; `test_migrations.py` fails if models and migrations drift.

## Roadmap

1. **Backend core** — done: auth, IIN identity, catalog, booking, age rule, payments, admin CRUD.
2. **Customer mobile app** — Expo app, TS client generated from OpenAPI, ru/kk localization,
   push notifications, real SMS provider.
3. **Admin panel + real integrations** — React admin (club map, bookings, tariffs, reports,
   staff roles); real card acquirer, Kaspi and eGov adapters; fiscal receipts; hold-expiry and
   refund-retry worker; production hosting in Kazakhstan.
4. **Windows client** — kiosk client, device registration, sessions, WebSocket heartbeat and
   remote commands, forced logout of minors at 22:00, walk-ins and wallet.

Known gaps to pick up later: no rate limiting beyond the OTP cooldown; refunds that fail are only
flagged (`payments.raw.refund_required`); bookings never move to `completed`/`no_show` yet
(needs sessions from phase 4); no tariffs/packages, only an hourly zone price.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
