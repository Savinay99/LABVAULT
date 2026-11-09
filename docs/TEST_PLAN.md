# Test Plan — LabVault

**Document version:** 1.0
**Status:** Draft (test plan only — no code changes in this phase)
**Standard:** ISO/IEC/IEEE 29119 (software testing) aligned; maps to `SRS.md` FR/NFR IDs
**Project:** LabVault — secure academic laboratory resource and document management portal
**Repository:** `E:\tryis` (Django 5.2, mssql-django, Azure SQL Database, Azure Blob Storage)

---

## 1. Introduction

### 1.1 Purpose

This test plan defines the LabVault test strategy, scope, levels, environment, execution procedure, and pass/fail criteria. It is the Stage 6 document following `SRS.md`, `ARCHITECTURE.md`, `DATABASE.md`, `SECURITY_AND_PRIVACY.md`, `DP900_MAPPING.md`, and `COA_SE_NOTES.md`. Test planning only; no code is changed in this phase.

Test IDs here map to requirement IDs in `TRACEABILITY.md`.

---

## 2. Test strategy

### 2.1 Approach

- **Unit tests** for pure functions (validation, storage-key generation, MIME detection) — no database, no framework app context where avoidable.
- **Route/integration tests** through the Django test client against a SQLite test database (`settings_test.py`) — exercises views, forms, auth, CSRF, authorization redirects, security headers.
- **Mocked repository/service tests** for data-access behavior (parameterized queries, transaction commit/rollback) using fake `pyodbc` connections — no Azure SQL required.
- **No tests require live Azure infrastructure** (SQL Database, Blob Storage, Key Vault). Tests depending on Azure are documented as requiring that infrastructure and are not executed here.

### 2.2 Test levels

| Level | Target | Tooling | Environment |
|---|---|---|---|
| Unit | `app.security.validation`, `app.services.storage_service`, `resources.storage` pure functions | pytest | local, no DB |
| Route / integration | Django views, forms, auth, CSRF, security headers | Django test client + pytest-django | SQLite (`settings_test.py`) |
| Repository / data access | Parameterized query construction, transaction behavior | Mocked pyodbc connections | local, no DB |

### 2.3 Test environment

- Python 3.11+ (tested on 3.14)
- Django 5.2.18, pytest 8.3.3, pytest-django 4.8.0
- `DJANGO_SETTINGS_MODULE=labvault_project.settings_test` for test runs (SQLite, MD5 password hasher for speed, CSRF relaxed)
- No network, no Azure credentials required

---

## 3. Test inventory (current suite)

55 tests across 6 test files plus `conftest.py`:

| File | Count | What it covers |
|---|---|---|
| `tests/test_routes.py` | 13 | Route availability, anonymous-access denial (302 to login), CSRF token in forms, open-redirect protection on `next` param (external, protocol-relative), relative-path redirect honored, 404 page |
| `tests/test_auth.py` | 13 | Registration success + duplicate email (409), authenticate success/wrong password/inactive/not-found, password change success/wrong current, login lockout after max failed attempts (400→429), unknown-account failure recording, successful login clears failures | mocked DB layer |
| `tests/test_repositories.py` | 5 | Parameterized queries (`?` placeholders) for `get_by_email`, `email_exists`, `create_resource`, `delete_resource`; `execute_scalar` returns first column | fake connections |
| `tests/test_security.py` | 5 | SQL injection payloads rejected by email validator, XSS output escaping neutralizes tags, path-traversal/dangerous extensions rejected, executable uploads (.exe/.bat/.com/.sh) rejected, visibility values constrained | app context |
| `tests/test_storage.py` | 6 | Extension allowlist true/false, unsupported/empty file rejection, PDF magic-byte MIME detection, storage-key unpredictability and extension preservation | app context |
| `tests/conftest.py` | — | Django setup, `DJANGO_SETTINGS_MODULE=labvault_project.settings`, `Client` fixture | — |

**Total: 55 passed.** Last run: `55 passed in 9.65s` (Python 3.14, local, no Azure).

---

## 4. Requirement coverage map

Each SRS requirement (FR/NFR) is mapped to its implementation status and test coverage. Requirements marked **planned** are *not* claimed as tested or working.

### 4.1 Authentication & account management (FR-01…FR-12)

| FR | Requirement | Implemented in code | Covered by tests | Notes |
|---|---|---|---|---|
| FR-01 | Register with name, email, password (min 8) | Yes (`accounts` app) | test_routes, test_auth | |
| FR-02 | Email normalized/lowercased/trimmed | Yes (`normalize_email`) | test_validation | |
| FR-03 | Duplicate email rejected, generic message | Yes (`User.email` unique + form) | test_auth (duplicate → 409) | |
| FR-04 | Passwords hashed with Argon2 | Yes (config — `Argon2PasswordHasher` first, `argon2-cffi==23.1.0` in requirements.txt) | test_validation (`test_password_hashers_led_by_argon2` checks production settings) | Runtime takes effect once `argon2-cffi` is installed; settings_test.py overrides with MD5 for speed |
| FR-05 | Sign in with email/password; generic failure | Yes | test_auth | |
| FR-06 | LoginAttempts table + lockout threshold | No — table not in models | test_auth tests lockout *behavior* via mocked `_login_attempts`, not the DB table | Planned via django-axes |
| FR-07 | Successful sign-in clears failures | No — in mocked logic only | test_auth (`test_successful_login_clears_failures`) | Not persisted to DB |
| FR-08 | Session security (HttpOnly/SameSite/Secure/age) | Yes (`settings.py`) | Indirect via settings; no dedicated test | |
| FR-09 | Password change with current password | Yes (`PasswordChangeForm`) | test_auth | |
| FR-10 | View/edit own profile | Yes (`profile_view`, `settings_view`) | Route tests confirm login required | |
| FR-11 | TOTP 2FA for administrators | No — not implemented | None | Planned |
| FR-12 | Consent at signup (checkbox + timestamp + version) | No — no consent fields | None | Planned |

### 4.2 Resource management (FR-13…FR-23)

| FR | Requirement | Implemented | Covered by tests | Notes |
|---|---|---|---|---|
| FR-13 | Upload with title, description, category, subjects, visibility | Yes | test_routes (upload page + anon redirect) | File upload end-to-end not in test suite |
| FR-14 | Extension allowlist + MIME magic + size ≤ 10 MB | Yes (`validate_file`) | test_storage | |
| FR-15 | Stream to Azure Blob or local storage; unpredictable key | Yes (`AzureBlobStorage`/`LocalProtectedStorage`, `generate_storage_key`) | test_storage (key unpredictability) | |
| FR-16 | Transactional metadata insert; delete blob/file on DB failure | Yes (`resources/views.py` upload) | Not directly tested | Cleanup path exercised only in code review |
| FR-17 | SHA-256 checksum stored with metadata | Yes (`ResourceFiles` model + `compute_sha256` in upload) | test_storage (`compute_sha256` deterministic/chunk/stream-position tests), test_routes (upload creates ResourceFiles with checksum) | End-to-end via test client with mocked storage backend |
| FR-18 | View details (owner/public/admin) | Yes (`_user_can_view_resource`) | test_routes (details via auth) | No dedicated authorized-download test |
| FR-19 | Edit metadata (owner/admin) | Yes (`edit` view) | Route tests confirm login required | |
| FR-20 | Delete own resource + file cleanup | Yes (`delete` view, best-effort storage delete) | Route tests confirm login required | |
| FR-21 | Download authorization (owner/public/admin) | Yes (`_user_can_view_resource` in download) | None directly | |
| FR-22 | Azure short-lived SAS URL (default 30 min) | Yes (`download_url`) | Not tested (requires Azure) | |
| FR-23 | Local download with `attachment` + `nosniff` | Yes (`download` view) | None directly | |
| FR-24 | Every download logged in AccessLog | Yes (`AccessLog` model + `download` view writes it) | test_routes (download logs AccessLog; non-owner rejected; public download logs) | |

### 4.3 Library, search, discovery (FR-25…FR-28)

| FR | Requirement | Implemented | Covered by tests | Notes |
|---|---|---|---|---|
| FR-25 | Paginated library (default 20) | Yes (`library` view) | test_routes (library page + anon redirect) | Pagination math not directly asserted |
| FR-26 | Search on title/description | Yes (`__icontains`) | None directly | |
| FR-27 | Filter by category/subject/course; sort | Yes (category/subject; course planned) | None directly | |
| FR-28 | Students see public + own; admins see all | Yes (`library` queryset filter) | None directly | |

### 4.4 Favorites & notifications (FR-30…FR-32)

| FR | Requirement | Implemented | Covered by tests | Notes |
|---|---|---|---|---|
| FR-30 | Favorites (Favorites table) | No | None | Planned |
| FR-31 | Notifications (Notifications table) | Yes | None | Implemented (`resources/migrations/0004_notification.py`; views + templates) |
| FR-32 | View/mark-read notifications | Yes | None | Implemented (`notification_mark_read`, `notification_mark_all_read` views) |

### 4.5 Administration & audit (FR-33…FR-36)

| FR | Requirement | Implemented | Covered by tests | Notes |
|---|---|---|---|---|
| FR-33 | Admin view/manage users | Partially (Django admin registered; no admin views beyond admin site) | test_routes (admin index anon redirect) | |
| FR-34 | View AuditLog | Yes (`AuditLog` model + admin) | None directly | AuditLog write usage not standardized/tested |
| FR-35 | View AccessLog | Yes (`AccessLog` model + `AccessLogAdmin`) | test_routes (AccessLog created via download) | |
| FR-36 | All admin actions recorded in AuditLog | Partially (model exists; usage not standardized) | None | Planned standardization |

### 4.6 Data ethics & user rights (FR-37…FR-41)

| FR | Requirement | Implemented | Covered by tests | Notes |
|---|---|---|---|---|
| FR-37 | Data minimization; no third-party trackers | Design constraint | None (template audit pending) | |
| FR-38 | Consent recorded | No | None | Planned |
| FR-39 | Retention policy | No | None | Planned (policy defined in SECURITY_AND_PRIVACY.md) |
| FR-40 | Account export (JSON) | No | None | Planned |
| FR-41 | Account deletion + cascade | No | None | Planned |

### 4.7 UI & themes (FR-42…FR-43)

| FR | Requirement | Implemented | Covered by tests | Notes |
|---|---|---|---|---|
| FR-42 | Light/dark themes | Yes (CSS toggle) | None | |
| FR-43 | Responsive, accessible, no JS framework | Yes (vanilla JS) | None | |

### 4.8 Non-functional requirements (NFR-01…NFR-16)

| NFR | Requirement | Implemented | Covered by tests | Notes |
|---|---|---|---|---|
| NFR-01 | Confidentiality (owner/public/admin downloads) | Yes | None directly | |
| NFR-02 | SHA-256 integrity | Yes (`ResourceFiles` model + `compute_sha256` in upload) | test_storage, test_routes (`test_upload_creates_resource_files_with_sha256`) | |
| NFR-03 | Argon2 password hashing | Yes (config — `Argon2PasswordHasher` first, `argon2-cffi==23.1.0` in requirements.txt) | test_validation (`test_password_hashers_led_by_argon2`) | Runtime takes effect once `argon2-cffi` is installed |
| NFR-04 | Brute-force lockout | No (mocked only) | test_auth (mocked lockout) | Planned via django-axes |
| NFR-05 | TLS in production | Config (`SESSION_COOKIE_SECURE`, HSTS) | None (deployment-level) | |
| NFR-06 | Encryption at rest (TDE + Blob SSE) | Platform config | None | Not app-testable |
| NFR-07 | Secrets via Key Vault + managed identity | No — `.env` in dev | None | Planned |
| NFR-08 | CSP header on all responses | Yes (`SECURE_CONTENT_TYPE_NOSNIFF`, CSP via middleware) | Indirect | CSP header not directly asserted |
| NFR-09 | Upload size limit ≤ 10 MB | Yes (`MAX_CONTENT_LENGTH`) | test_storage (size rejection) | |
| NFR-10 | Pagination performance (OFFSET/FETCH, indexes) | Yes (indexes on `-created_at`) | None directly | |
| NFR-11 | SAS expiry ≤ 30 min | Yes (`download_url` default 30 min) | None (requires Azure) | |
| NFR-12 | Orphan cleanup job | No | None | Planned |
| NFR-13 | Account export (JSON) | No | None | Planned |
| NFR-14 | Account deletion per retention | No | None | Planned |
| NFR-15 | No third-party trackers | Design constraint | None | |
| NFR-16 | Theme persistence without flicker | Partial (CSS toggle) | None | |

---

## 5. Test execution

### 5.1 How to run

```bash
# From repository root E:\tryis
DJANGO_SETTINGS_MODULE=labvault_project.settings_test python -m pytest tests/ -q
# or, with settings already discoverable via conftest:
python -m pytest tests/ -q
```

Expected result: 47 passed, 0 failed. Last verified: `47 passed in 7.06s`.

### 5.2 What is NOT tested (gap list)

- Authorized details/edit/delete flows with an authenticated client — routes tested for login-required redirect only (download is now tested end-to-end).
- Argon2 hashing, django-axes lockout, TOTP 2FA, consent recording, Favorites table, account export/delete — all planned, not implemented.
- SQL Server (mssql-django) integration — SQLite used for tests; schema parity not guaranteed.

### 5.3 Pass/fail criteria

- All 55 tests must pass with no failures or errors.
- Any new test added for a planned requirement must pass before that requirement is marked implemented.
- No test may require network or Azure credentials to run locally.

### 5.4 Maintenance

When a planned requirement is implemented (e.g. `AccessLog`, `ResourceFiles`, django-axes lockout, Argon2), add tests under the corresponding `tests/test_*.py` file, update this plan's coverage map and `TRACEABILITY.md`, then re-run the full suite.

---

## 6. Cross-references

- `SRS.md` — FR-01…FR-43, NFR-01…NFR-16; Section 3.8 verified vs planned baseline
- `ARCHITECTURE.md` — module boundaries, ADRs (ADR-08 Argon2, ADR-09 django-axes, ADR-10 TOTP)
- `DATABASE.md` — table definitions, indexes, migration approach; honesty baseline (implemented vs planned tables)
- `SECURITY_AND_PRIVACY.md` — controls C-01…C-26, STRIDE threat model
- `TRACEABILITY.md` — requirement ↔ test ↔ code mapping (this plan's companion)

*End of TEST_PLAN.md — Stage 6 document 1 of 2. TRACEABILITY.md follows.*
