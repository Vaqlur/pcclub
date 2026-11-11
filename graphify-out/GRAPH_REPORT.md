# Graph Report - pcclub  (2026-11-12)

## Corpus Check
- Corpus is ~22,657 words - fits in a single context window. You may not need a graph.

## Summary
- 925 nodes · 2775 edges · 44 communities (29 shown, 15 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 275 edges (avg confidence: 0.92)
- Token cost: 117,066 input · 0 output

## Community Hubs (Navigation)
- Catalog & Admin Clubs
- Payment Service & Providers
- SQLAlchemy Models & CLI
- Booking Service & Slots
- IIN & Identity Verification
- Project Docs & Architecture Rules
- Booking Integration Tests
- Age Rule (Minor Night Restriction)
- Bookings API Router
- Security: JWT, Hashing, IIN Crypto
- Integration Registry & SMS
- Payment Integration Tests
- Auth Integration Tests
- Auth API & Schemas
- App Factory, Config & DB
- Test Database Fixtures
- Auth Service (OTP & Tokens)
- Test App & Client Fixtures
- Docker Compose
- Error Handling
- Admin Integration Tests
- Identity Verifier Integration
- Identity Integration Tests
- Booking Age-Rule Tests
- Catalog Tests & Helpers
- Alembic Migration Env
- Auth Dependencies
- Clock Implementations
- Booking Concurrency Tests
- OTP Request & SMS Delivery
- Staff Login Endpoint
- Backend pyproject

## God Nodes (most connected - your core abstractions)
1. `code()` - 60 edges
2. `register()` - 57 edges
3. `at()` - 51 edges
4. `book()` - 46 edges
5. `Settings` - 39 edges
6. `AppError` - 33 edges
7. `violates_night_restriction()` - 28 edges
8. `StaffUser` - 24 edges
9. `book_and_pay()` - 24 edges
10. `Clock` - 23 edges

## Surprising Connections (you probably didn't know these)
- `Money rule: whole tenge as int, _kzt suffix` --conceptually_related_to--> `booking_price_kzt()`  [INFERRED]
  CLAUDE.md → backend/app/domain/pricing.py
- `Slot rules (future, 30-min aligned, 1-12 h, max 14 days ahead, inside opening hours)` --references--> `validate_slot()`  [INFERRED]
  CLAUDE.md → backend/app/domain/slots.py
- `Idempotency-Key header for payments (replays return original payment)` --references--> `create_payment()`  [INFERRED]
  CLAUDE.md → backend/app/services/payment.py
- `SMS provider` --references--> `SmsSender`  [INFERRED]
  CLAUDE.md → backend/app/integrations/sms/base.py
- `Mock providers in local development` --references--> `MockSmsSender`  [INFERRED]
  README.md → backend/app/integrations/sms/mock.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Booking and payment integrity guarantees** — claude_exclusion_constraints, claude_lazy_hold_expiry, claude_webhook_confirmation, claude_automatic_refunds, claude_idempotency_key, claude_row_lock_order [INFERRED 0.85]
- **Minor night-restriction enforcement chain (IIN -> verified identity -> age rule -> booking rejection)** — claude_iin_rule, claude_identityverifier, claude_identity_verification_required, claude_age_rule, claude_adult_from, claude_minor_night_restriction [INFERRED 0.85]
- **Deterministic testing strategy (pure domain, injected clock, real PostgreSQL, migration drift check)** — claude_pure_domain_layer, claude_injected_clock, claude_fixedclock, claude_real_postgresql_testing, claude_requires_overlap_constraints, claude_migration_drift_test [INFERRED 0.85]

## Communities (44 total, 15 thin omitted)

### Community 0 - "Catalog & Admin Clubs"
Cohesion: 0.07
Nodes (60): create_club(), create_pc(), create_zone(), get_club(), list_club_bookings(), list_clubs(), list_pcs(), list_zones() (+52 more)

### Community 1 - "Payment Service & Providers"
Cohesion: 0.07
Nodes (23): get_payment(), mock_complete(), mock_fail(), provider_webhook(), _simulate(), CreatedPayment, InvalidWebhook, PaymentMethod (+15 more)

### Community 2 - "SQLAlchemy Models & CLI"
Cohesion: 0.07
Nodes (19): upgrade(), create_owner(), main(), _run(), seed_demo(), get_engine(), get_sessionmaker(), created_at_column() (+11 more)

### Community 3 - "Booking Service & Slots"
Cohesion: 0.08
Nodes (27): Clock, booking_price_kzt(), InvalidSlot, _is_aligned(), OutsideOpeningHours, SlotRules, validate_slot(), within_opening_hours() (+19 more)

### Community 4 - "IIN & Identity Verification"
Cohesion: 0.08
Nodes (28): get_me(), submit_identity(), update_me(), build_iin(), check_digit(), IINInfo, InvalidIIN, is_valid_iin() (+20 more)

### Community 5 - "Project Docs & Architecture Rules"
Cohesion: 0.05
Nodes (30): InvalidPhone, normalize_phone(), Admin panel for club owners (React + Vite) - phase 3, Automatic refunds for late, duplicate or cancelled-booking payments, Backend API (FastAPI, PostgreSQL 17, SQLAlchemy 2 async, Alembic) - phase 1 done, Booking lifecycle (pending_payment -> confirmed -> completed / cancelled / expired), Customer mobile app (React Native + Expo) - phase 2, FixedClock in integration tests (starts 2026-06-01 12:00 Almaty) (+22 more)

### Community 6 - "Booking Integration Tests"
Cohesion: 0.12
Nodes (36): at(), book(), book_and_pay(), register(), test_back_to_back_and_other_pcs_are_fine(), test_booking_requires_authentication(), test_booking_requires_verified_identity(), test_bookings_are_private() (+28 more)

### Community 7 - "Age Rule (Minor Night Restriction)"
Cohesion: 0.11
Nodes (28): adult_from(), can_play_at(), is_minor_at(), _local(), _require_aware(), violates_night_restriction(), local(), test_adult_from_leap_day_in_leap_year() (+20 more)

### Community 8 - "Bookings API Router"
Cohesion: 0.11
Nodes (9): cancel_booking(), create_booking(), create_payment(), get_booking(), list_bookings(), BookingCreate, BookingOut, BookingPage (+1 more)

### Community 9 - "Security: JWT, Hashing, IIN Crypto"
Cohesion: 0.09
Nodes (16): constant_time_equals(), create_access_token(), decode_access_token(), decrypt_iin(), encrypt_iin(), _fernet(), generate_otp_code(), hash_iin() (+8 more)

### Community 10 - "Integration Registry & SMS"
Cohesion: 0.12
Nodes (13): IdentityVerifier, build_identity_verifier(), build_payment_providers(), build(), build_sms_sender(), get_identity_verifier(), get_payment_providers(), get_sms_sender() (+5 more)

### Community 11 - "Payment Integration Tests"
Cohesion: 0.19
Nodes (22): ProviderPaymentStatus, pay(), _booking_status(), test_cannot_pay_after_the_hold_expired(), test_duplicate_webhook_is_idempotent(), test_failed_payment_can_be_retried(), test_idempotency_key_is_required(), test_idempotency_key_replay_returns_the_same_payment() (+14 more)

### Community 12 - "Auth Integration Tests"
Cohesion: 0.24
Nodes (20): code(), _request(), test_access_token_expires(), test_blocked_user(), test_code_expires(), test_code_is_locked_after_too_many_attempts(), test_code_is_single_use(), test_first_login_creates_unverified_user() (+12 more)

### Community 13 - "Auth API & Schemas"
Cohesion: 0.20
Nodes (9): logout(), refresh(), request_otp(), verify_otp(), OtpRequest, OtpVerify, RefreshRequest, StaffLogin (+1 more)

### Community 14 - "App Factory, Config & DB"
Cohesion: 0.13
Nodes (5): get_settings(), Settings, get_session(), create_app(), _lifespan()

### Community 15 - "Test Database Fixtures"
Cohesion: 0.14
Nodes (11): get_clock(), hash_password(), alembic_config(), committed_session_factory(), committed_world(), Database, database(), _reset_schema() (+3 more)

### Community 16 - "Auth Service (OTP & Tokens)"
Cohesion: 0.21
Nodes (13): AppError, RefreshToken, _get_or_create_user(), _issue_tokens(), logout(), _otp_invalid(), refresh_tokens(), _revoke_all() (+5 more)

### Community 17 - "Test App & Client Fixtures"
Cohesion: 0.18
Nodes (12): _build_app(), _session(), client(), _client(), clock(), committed_client(), connection(), db() (+4 more)

### Community 18 - "Docker Compose"
Cohesion: 0.12
Nodes (16): environment, healthcheck, image, ports, volumes, POSTGRES_DB, POSTGRES_PASSWORD, POSTGRES_USER (+8 more)

### Community 19 - "Error Handling"
Cohesion: 0.17
Nodes (5): _envelope(), register_error_handlers(), _app_error(), _http_error(), _validation_error()

### Community 20 - "Admin Integration Tests"
Cohesion: 0.16
Nodes (9): staff(), staff_login(), test_club_bookings_for_a_day(), ids(), test_customer_and_staff_tokens_are_not_interchangeable(), test_duplicates_and_foreign_zones(), test_organizations_are_isolated(), test_staff_login() (+1 more)

### Community 21 - "Identity Verifier Integration"
Cohesion: 0.23
Nodes (4): IdentityCheckStatus, IdentityResult, IdentityVerifierUnavailable, MockIdentityVerifier

### Community 22 - "Identity Integration Tests"
Cohesion: 0.37
Nodes (12): iin_for(), login(), _submit(), test_cannot_verify_twice(), test_identity_requires_authentication(), test_identity_verification(), test_iin_cannot_be_used_by_two_accounts(), test_iin_not_found_then_retry() (+4 more)

### Community 23 - "Booking Age-Rule Tests"
Cohesion: 0.16
Nodes (8): test_adult_can_book_at_night(), test_age_comes_from_the_verified_iin(), test_around_the_18th_birthday(), test_minor_can_book_daytime(), test_minor_cannot_book_at_night(), test_night_is_judged_in_the_club_timezone(), test_night_window_is_configurable(), test_unverified_user_cannot_bypass_the_rule()

### Community 24 - "Catalog Tests & Helpers"
Cohesion: 0.21
Nodes (6): parse_dt(), test_pc_busy_intervals_for_a_local_day(), busy(), test_unknown_or_inactive_club_is_404(), test_unpaid_hold_stops_blocking_after_expiry(), test_window_validation()

### Community 25 - "Alembic Migration Env"
Cohesion: 0.25
Nodes (5): _database_url(), _do_run_migrations(), _run_async_migrations(), run_migrations_offline(), run_migrations_online()

### Community 26 - "Auth Dependencies"
Cohesion: 0.36
Nodes (3): _claims(), get_current_staff(), get_current_user()

### Community 28 - "Booking Concurrency Tests"
Cohesion: 0.43
Nodes (3): test_many_users_racing_for_overlapping_slots(), test_one_user_double_submitting(), test_two_users_racing_for_one_slot()

### Community 29 - "OTP Request & SMS Delivery"
Cohesion: 0.29
Nodes (3): SmsDeliveryError, OtpCode, request_otp()

## Knowledge Gaps
- **2 isolated node(s):** `pcclub-backend`, `graphify knowledge graph usage rules`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 234 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AppError` connect `Auth Service (OTP & Tokens)` to `Catalog & Admin Clubs`, `Payment Service & Providers`, `Booking Service & Slots`, `IIN & Identity Verification`, `Project Docs & Architecture Rules`, `Integration Registry & SMS`, `Error Handling`, `Auth Dependencies`, `OTP Request & SMS Delivery`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **Are the 26 inferred relationships involving `Settings` (e.g. with `_claims()` and `create_access_token()`) actually correct?**
  _`Settings` has 26 INFERRED edges - model-reasoned connections that need verification._
- **What connects `pcclub-backend`, `graphify knowledge graph usage rules` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Catalog & Admin Clubs` be split into smaller, more focused modules?**
  _Cohesion score 0.06829896907216494 - nodes in this community are weakly interconnected._
- **Why does `Settings` connect `App Factory, Config & DB` to `Booking Service & Slots`, `IIN & Identity Verification`, `Project Docs & Architecture Rules`, `Security: JWT, Hashing, IIN Crypto`, `Integration Registry & SMS`, `Test Database Fixtures`, `Auth Service (OTP & Tokens)`, `Test App & Client Fixtures`, `Auth Dependencies`, `OTP Request & SMS Delivery`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Should `Payment Service & Providers` be split into smaller, more focused modules?**
  _Cohesion score 0.06666666666666667 - nodes in this community are weakly interconnected._
- **Why does `violates_night_restriction()` connect `Age Rule (Minor Night Restriction)` to `Booking Service & Slots`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._