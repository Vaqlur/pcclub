# PC Club

Management system for PC clubs in Kazakhstan: backend API, customer mobile app, admin panel and
(later) a Windows client for club PCs. See [CLAUDE.md](CLAUDE.md) for architecture, conventions
and the roadmap. The backend and a first version of the mobile app exist so far.

## Mobile app quick start

With the backend running (see below) and demo data seeded (`python -m app.cli seed-demo`):

```bash
cd mobile
npm install
npm run web      # browser preview at http://localhost:8081
npm start        # QR code for Expo Go on a phone
```

On a phone, copy `mobile/.env.example` to `mobile/.env`, set `EXPO_PUBLIC_API_URL` to this PC's
LAN address, and start the API with `--host 0.0.0.0`. In dev the login code is `OTP_FIXED_CODE`
from `backend/.env`, and payments go through the mock provider.

## Backend quick start (Windows)

1. Install PostgreSQL 17 (once):

   ```bash
   winget install PostgreSQL.PostgreSQL.17
   ```

2. Create the databases (psql is in `C:\Program Files\PostgreSQL\17\bin`):

   ```bash
   psql -U postgres -c "CREATE DATABASE pcclub" -c "CREATE DATABASE pcclub_test"
   ```

3. Configure and install, from `backend/`:

   ```bash
   cp .env.example .env        # then set DATABASE_URL and TEST_DATABASE_URL
   python -m venv .venv
   .venv/Scripts/python -m pip install -e ".[dev]"
   .venv/Scripts/alembic upgrade head
   ```

4. Run:

   ```bash
   .venv/Scripts/python -m app.cli seed-demo
   .venv/Scripts/python -m uvicorn app.main:app --reload
   ```

   Open http://127.0.0.1:8000/docs. With the mock providers, the SMS login code is the value of
   `OTP_FIXED_CODE` (`000000` in `.env.example`) and payments are completed with
   `POST /v1/payments/mock/{payment_id}/complete`.

5. Test:

   ```bash
   .venv/Scripts/python -m pytest -rs
   ```

   Without `TEST_DATABASE_URL` the integration tests can fall back to an embedded PostgreSQL
   (`pip install -e ".[dev,embedded-pg]"`), but the double-booking tests are skipped there
   because that server has no `btree_gist` extension.

Alternatively, `docker compose up -d db` starts PostgreSQL 17 with both databases
(user/password `pcclub`/`pcclub`, port 5432).
