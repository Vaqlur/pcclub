# Graph Report - pcclub  (2026-11-12)

## Corpus Check
- 119 files · ~42,540 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 2, .example 2, .ini 1)

## Summary
- 1232 nodes · 3583 edges · 75 communities (53 shown, 22 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 282 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `30f99455`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Catalog & Admin Clubs
- services/payment.py
- uuid
- Booking Service & Slots
- test_iin.py
- Double-booking prevention by PostgreSQL exclusion constraints (btree_gist)
- Booking Integration Tests
- Age Rule (Minor Night Restriction)
- Bookings API Router
- Security: JWT, Hashing, IIN Crypto
- deps.py
- Payment Integration Tests
- Auth Integration Tests
- Auth API & Schemas
- payments/base.py
- services/booking.py
- _issue_tokens
- conftest.py
- Docker Compose
- Error Handling
- Admin Integration Tests
- identity.py
- Identity Integration Tests
- Booking Age-Rule Tests
- Catalog Tests & Helpers
- Alembic Migration Env
- Auth Dependencies
- components.tsx
- Booking Concurrency Tests
- verify_otp
- Staff Login Endpoint
- Backend pyproject
- [bookingId].tsx
- [pcId].tsx
- AuthContext.tsx
- expo
- models/__init__.py
- cli.py
- payments.py
- Clock
- login.tsx
- dependencies
- package.json
- Backend API (FastAPI, PostgreSQL 17, SQLAlchemy 2 async, Alembic) - phase 1 done
- registry.py
- Integrations behind typing.Protocols with mocks
- scripts
- compilerOptions
- Roadmap (four phases)
- Booking lifecycle (pending_payment -> confirmed -> completed / cancelled / expired)
- Pure domain layer (no I/O: iin, age_rule, slots, pricing, phone)
- 0001_initial_schema.py
- phone.py
- eslint.config.js
- test_migrations.py
- AGENTS.md
- schema.d.ts
- Backend quick start (Windows)
- expo@~58.0.24
- expo-constants@~58.0.16
- expo-crypto
- @expo/metro-runtime@~58.0.17
- react-dom@19.3.0

## God Nodes (most connected - your core abstractions)
1. `code()` - 60 edges
2. `register()` - 57 edges
3. `at()` - 51 edges
4. `book()` - 46 edges
5. `Settings` - 43 edges
6. `AppError` - 33 edges
7. `violates_night_restriction()` - 28 edges
8. `BookPcScreen()` - 28 edges
9. `StaffUser` - 24 edges
10. `book_and_pay()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `Money rule: whole tenge as int, _kzt suffix` --conceptually_related_to--> `booking_price_kzt()`  [INFERRED]
  CLAUDE.md → backend/app/domain/pricing.py
- `Slot rules (future, 30-min aligned, 1-12 h, max 14 days ahead, inside opening hours)` --references--> `validate_slot()`  [INFERRED]
  CLAUDE.md → backend/app/domain/slots.py
- `Idempotency-Key header for payments (replays return original payment)` --references--> `create_payment()`  [INFERRED]
  CLAUDE.md → backend/app/services/payment.py
- `POST /v1/payments/mock/{payment_id}/complete` --references--> `mock_complete()`  [INFERRED]
  README.md → backend/app/api/v1/payments.py
- `Mock providers in local development` --references--> `MockPaymentProvider`  [INFERRED]
  README.md → backend/app/integrations/payments/mock.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Booking and payment integrity guarantees** — claude_exclusion_constraints, claude_lazy_hold_expiry, claude_webhook_confirmation, claude_automatic_refunds, claude_idempotency_key, claude_row_lock_order [INFERRED 0.85]
- **Deterministic testing strategy (pure domain, injected clock, real PostgreSQL, migration drift check)** — claude_pure_domain_layer, claude_injected_clock, claude_fixedclock, claude_real_postgresql_testing, claude_requires_overlap_constraints, claude_migration_drift_test [INFERRED 0.85]
- **Minor night-restriction enforcement chain (IIN -> verified identity -> age rule -> booking rejection)** — claude_iin_rule, claude_identityverifier, claude_identity_verification_required, claude_age_rule, claude_adult_from, claude_minor_night_restriction [INFERRED 0.85]

## Communities (75 total, 22 thin omitted)

### Community 0 - "Catalog & Admin Clubs"
Cohesion: 0.07
Nodes (55): create_club(), create_pc(), create_zone(), get_club(), list_club_bookings(), list_clubs(), list_pcs(), list_zones() (+47 more)

### Community 1 - "services/payment.py"
Cohesion: 0.14
Nodes (11): PaymentMethod, PaymentProvider, build_payment_providers(), get_payment_providers(), PaymentProviders, apply_event(), create_payment(), get_payment() (+3 more)

### Community 3 - "Booking Service & Slots"
Cohesion: 0.12
Nodes (19): booking_price_kzt(), InvalidSlot, _is_aligned(), OutsideOpeningHours, SlotRules, validate_slot(), within_opening_hours(), at() (+11 more)

### Community 4 - "test_iin.py"
Cohesion: 0.12
Nodes (19): build_iin(), check_digit(), IINInfo, InvalidIIN, is_valid_iin(), parse_iin(), IdentityResult, IdentityVerifierUnavailable (+11 more)

### Community 5 - "Double-booking prevention by PostgreSQL exclusion constraints (btree_gist)"
Cohesion: 0.18
Nodes (4): _violated_constraint(), MINOR_NIGHT_RESTRICTION error (403), SLOT_TAKEN error, USER_BOOKING_OVERLAP error

### Community 6 - "Booking Integration Tests"
Cohesion: 0.16
Nodes (32): at(), book(), register(), test_back_to_back_and_other_pcs_are_fine(), test_booking_requires_authentication(), test_booking_requires_verified_identity(), test_bookings_are_private(), test_cancel_paid_booking_refunds() (+24 more)

### Community 7 - "Age Rule (Minor Night Restriction)"
Cohesion: 0.11
Nodes (28): adult_from(), can_play_at(), is_minor_at(), _local(), _require_aware(), violates_night_restriction(), local(), test_adult_from_leap_day_in_leap_year() (+20 more)

### Community 8 - "Bookings API Router"
Cohesion: 0.13
Nodes (5): cancel_booking(), create_booking(), create_payment(), get_booking(), list_bookings()

### Community 9 - "Security: JWT, Hashing, IIN Crypto"
Cohesion: 0.11
Nodes (13): create_access_token(), decode_access_token(), decrypt_iin(), encrypt_iin(), _fernet(), generate_otp_code(), hash_iin(), hash_password() (+5 more)

### Community 10 - "deps.py"
Cohesion: 0.10
Nodes (5): get_session(), IdentityVerifier, build_identity_verifier(), get_identity_verifier(), SmsDeliveryError

### Community 11 - "Payment Integration Tests"
Cohesion: 0.22
Nodes (21): ProviderPaymentStatus, pay(), _booking_status(), test_cannot_pay_after_the_hold_expired(), test_duplicate_webhook_is_idempotent(), test_failed_payment_can_be_retried(), test_idempotency_key_is_required(), test_idempotency_key_replay_returns_the_same_payment() (+13 more)

### Community 12 - "Auth Integration Tests"
Cohesion: 0.26
Nodes (20): code(), _request(), test_access_token_expires(), test_blocked_user(), test_code_expires(), test_code_is_locked_after_too_many_attempts(), test_code_is_single_use(), test_first_login_creates_unverified_user() (+12 more)

### Community 13 - "Auth API & Schemas"
Cohesion: 0.20
Nodes (9): logout(), refresh(), request_otp(), verify_otp(), OtpRequest, OtpVerify, RefreshRequest, StaffLogin (+1 more)

### Community 14 - "payments/base.py"
Cohesion: 0.17
Nodes (5): CreatedPayment, InvalidWebhook, PaymentProviderError, WebhookEvent, MockPaymentProvider

### Community 15 - "services/booking.py"
Cohesion: 0.15
Nodes (8): get_clock(), BookingStatus, PcStatus, PaymentStatus, BookingCreate, BookingOut, BookingPage, PaymentCreate

### Community 16 - "_issue_tokens"
Cohesion: 0.24
Nodes (8): hash_token(), verify_password(), _issue_tokens(), logout(), refresh_tokens(), _revoke_all(), staff_login(), _subject_may_login()

### Community 17 - "conftest.py"
Cohesion: 0.05
Nodes (40): FixedClock, SystemClock, Settings, MockSmsSender, SentSms, _cors_origin_regex(), create_app(), _lifespan() (+32 more)

### Community 18 - "Docker Compose"
Cohesion: 0.12
Nodes (16): environment, healthcheck, image, ports, volumes, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER (+8 more)

### Community 19 - "Error Handling"
Cohesion: 0.17
Nodes (5): _envelope(), register_error_handlers(), _app_error(), _http_error(), _validation_error()

### Community 20 - "Admin Integration Tests"
Cohesion: 0.16
Nodes (9): staff(), staff_login(), test_club_bookings_for_a_day(), ids(), test_customer_and_staff_tokens_are_not_interchangeable(), test_duplicates_and_foreign_zones(), test_organizations_are_isolated(), test_staff_login() (+1 more)

### Community 21 - "identity.py"
Cohesion: 0.16
Nodes (11): get_me(), submit_identity(), update_me(), IdentityCheckStatus, IdentitySubmit, UserOut, UserUpdate, _mark_rejected() (+3 more)

### Community 22 - "Identity Integration Tests"
Cohesion: 0.33
Nodes (12): iin_for(), login(), _submit(), test_cannot_verify_twice(), test_identity_requires_authentication(), test_identity_verification(), test_iin_cannot_be_used_by_two_accounts(), test_iin_not_found_then_retry() (+4 more)

### Community 23 - "Booking Age-Rule Tests"
Cohesion: 0.16
Nodes (8): test_adult_can_book_at_night(), test_age_comes_from_the_verified_iin(), test_around_the_18th_birthday(), test_minor_can_book_daytime(), test_minor_cannot_book_at_night(), test_night_is_judged_in_the_club_timezone(), test_night_window_is_configurable(), test_unverified_user_cannot_bypass_the_rule()

### Community 24 - "Catalog Tests & Helpers"
Cohesion: 0.12
Nodes (12): book_and_pay(), parse_dt(), test_availability_flag_for_a_window(), test_list_and_get_clubs(), test_pc_busy_intervals_for_a_local_day(), busy(), test_unknown_or_inactive_club_is_404(), test_unpaid_hold_stops_blocking_after_expiry() (+4 more)

### Community 25 - "Alembic Migration Env"
Cohesion: 0.25
Nodes (5): _database_url(), _do_run_migrations(), _run_async_migrations(), run_migrations_offline(), run_migrations_online()

### Community 26 - "Auth Dependencies"
Cohesion: 0.31
Nodes (3): _claims(), get_current_staff(), get_current_user()

### Community 27 - "components.tsx"
Cohesion: 0.12
Nodes (38): listBookings(), listClubs(), submitIdentity(), BookingsScreen(), loadMore(), styles, IdentityScreen(), submit() (+30 more)

### Community 28 - "Booking Concurrency Tests"
Cohesion: 0.43
Nodes (3): test_many_users_racing_for_overlapping_slots(), test_one_user_double_submitting(), test_two_users_racing_for_one_slot()

### Community 29 - "verify_otp"
Cohesion: 0.22
Nodes (6): constant_time_equals(), hash_otp(), _get_or_create_user(), _otp_invalid(), request_otp(), verify_otp()

### Community 44 - "[bookingId].tsx"
Cohesion: 0.10
Nodes (37): Booking, BookingPage, cancelBooking(), Club, createPayment(), getBooking(), getClub(), listPcs() (+29 more)

### Community 45 - "[pcId].tsx"
Cohesion: 0.15
Nodes (34): createBooking(), getPcAvailability(), BookPcScreen(), submit(), styles, formatDay(), formatDuration(), formatInstantDay() (+26 more)

### Community 46 - "AuthContext.tsx"
Cohesion: 0.10
Nodes (34): api(), API_URL, ApiError, buildUrl(), currentRefreshToken(), endSession(), parse(), Query (+26 more)

### Community 47 - "expo"
Cohesion: 0.08
Nodes (24): backgroundColor, backgroundImage, foregroundImage, monochromeImage, adaptiveIcon, predictiveBackGestureEnabled, typedRoutes, expo (+16 more)

### Community 48 - "models/__init__.py"
Cohesion: 0.12
Nodes (11): Base, OtpCode, RefreshToken, Booking, Club, Pc, Zone, Organization (+3 more)

### Community 49 - "cli.py"
Cohesion: 0.19
Nodes (9): create_owner(), main(), _run(), seed_demo(), get_settings(), get_engine(), get_sessionmaker(), StaffRole (+1 more)

### Community 50 - "payments.py"
Cohesion: 0.25
Nodes (6): get_payment(), mock_complete(), mock_fail(), provider_webhook(), _simulate(), PaymentOut

### Community 51 - "Clock"
Cohesion: 0.24
Nodes (6): Clock, cancel_booking(), create_booking(), expire_stale_holds(), get_booking(), list_bookings()

### Community 52 - "login.tsx"
Cohesion: 0.23
Nodes (10): requestOtp(), verifyOtp(), LoginScreen(), resend(), run(), sendCode(), submitCode(), VALID (+2 more)

### Community 53 - "dependencies"
Cohesion: 0.13
Nodes (15): dependencies, expo-linking@~58.0.17, expo-router@~58.0.31, expo-secure-store@~58.0.3, expo-status-bar@~58.0.5, react@19.3.0, react-native@0.88.1, react-native-safe-area-context@~5.11.1 (+7 more)

### Community 54 - "package.json"
Cohesion: 0.21
Nodes (11): devDependencies, @types/node@^26.6.6, @types/react@~19.3.0, typescript@~6.0.3, main, name, private, version (+3 more)

### Community 55 - "Backend API (FastAPI, PostgreSQL 17, SQLAlchemy 2 async, Alembic) - phase 1 done"
Cohesion: 0.20
Nodes (3): Backend API (FastAPI, PostgreSQL 17, SQLAlchemy 2 async, Alembic) - phase 1 done, Services layer (use-cases own the transaction, commit here), Thin routers (api/v1, api/v1/admin)

### Community 56 - "registry.py"
Cohesion: 0.33
Nodes (5): build(), build_sms_sender(), get_sms_sender(), UnknownProvider, SmsSender

### Community 57 - "Integrations behind typing.Protocols with mocks"
Cohesion: 0.28
Nodes (7): Customer auth: phone + SMS code, account created on first login, Customer mobile app (React Native + Expo) - phase 2, IdentityVerifier (eGov IIN lookup, authoritative birth date), integrations/registry.py (provider selection by settings), SMS provider, Mock providers in local development, OTP_FIXED_CODE (fixed SMS login code with mock SMS)

### Community 58 - "scripts"
Cohesion: 0.22
Nodes (9): scripts, android, gen:api, ios, lint, start, test, typecheck (+1 more)

### Community 59 - "compilerOptions"
Cohesion: 0.22
Nodes (8): compilerOptions, allowImportingTsExtensions, paths, strict, types, extends, include, expo/tsconfig.base

### Community 60 - "Roadmap (four phases)"
Cohesion: 0.39
Nodes (7): Admin panel for club owners (React + Vite) - phase 3, Forced logout of minors at 22:00 (planned Windows client), graphify knowledge graph usage rules, PC Club management system (project overview), Roadmap (four phases), Windows client for club PCs - phase 4, PC Club README

### Community 61 - "Booking lifecycle (pending_payment -> confirmed -> completed / cancelled / expired)"
Cohesion: 0.36
Nodes (6): Automatic refunds for late, duplicate or cancelled-booking payments, Booking lifecycle (pending_payment -> confirmed -> completed / cancelled / expired), Hold-expiry and refund-retry worker (planned, phase 3), Idempotency-Key header for payments (replays return original payment), Known gaps (rate limiting, failed refunds, completed/no_show, tariffs), Slot rules (future, 30-min aligned, 1-12 h, max 14 days ahead, inside opening hours)

### Community 62 - "Pure domain layer (no I/O: iin, age_rule, slots, pricing, phone)"
Cohesion: 0.29
Nodes (3): FixedClock in integration tests (starts 2026-06-01 12:00 Almaty), Staff auth: email + password, Testing rules

### Community 63 - "0001_initial_schema.py"
Cohesion: 0.29
Nodes (3): upgrade(), test_models_match_migrated_schema(), Alembic migration drift check (test_migrations.py)

### Community 65 - "eslint.config.js"
Cohesion: 0.29
Nodes (6): { defineConfig }, expoConfig, eslint@^9.0.0, eslint-config-expo@~58.0.4, eslint, eslint-config-expo

### Community 67 - "AGENTS.md"
Cohesion: 0.33
Nodes (5): Building with EAS, Commands, Expo has changed — do not trust your training data, Navigation & Routing, Rules

### Community 68 - "schema.d.ts"
Cohesion: 0.33
Nodes (5): components, $defs, operations, paths, webhooks

### Community 69 - "Backend quick start (Windows)"
Cohesion: 1.00
Nodes (3): Backend quick start (Windows), docker compose db service (PostgreSQL 17 with both databases), PostgreSQL 17 install and databases (pcclub, pcclub_test)

## Knowledge Gaps
- **3 isolated node(s):** `pcclub-backend`, `expo/tsconfig.base`, `graphify knowledge graph usage rules`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 326 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **22 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppError` connect `Catalog & Admin Clubs` to `services/payment.py`, `Double-booking prevention by PostgreSQL exclusion constraints (btree_gist)`, `deps.py`, `services/booking.py`, `_issue_tokens`, `payments.py`, `Error Handling`, `Clock`, `identity.py`, `Auth Dependencies`, `verify_otp`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `Settings` (e.g. with `_claims()` and `create_access_token()`) actually correct?**
  _`Settings` has 28 INFERRED edges - model-reasoned connections that need verification._
- **What connects `pcclub-backend`, `expo/tsconfig.base`, `graphify knowledge graph usage rules` to the rest of the system?**
  _3 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Catalog & Admin Clubs` be split into smaller, more focused modules?**
  _Cohesion score 0.07122060470324748 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `conftest.py` to `services/payment.py`, `Security: JWT, Hashing, IIN Crypto`, `deps.py`, `services/booking.py`, `_issue_tokens`, `cli.py`, `Clock`, `identity.py`, `Backend API (FastAPI, PostgreSQL 17, SQLAlchemy 2 async, Alembic) - phase 1 done`, `registry.py`, `Auth Dependencies`, `verify_otp`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **Should `services/payment.py` be split into smaller, more focused modules?**
  _Cohesion score 0.135632183908046 - nodes in this community are weakly interconnected._
- **Why does `violates_night_restriction()` connect `Age Rule (Minor Night Restriction)` to `Clock`, `services/booking.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._