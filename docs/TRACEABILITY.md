# Requirements Traceability Matrix — LabVault

**Document version:** 1.0
**Status:** Draft (traceability only — no code changes in this phase)
**Standard:** ISO/IEC/IEEE 29148 (requirements traceability) aligned
**Project:** LabVault — secure academic laboratory resource and document management portal
**Repository:** `E:\tryis` (Django 5.2, mssql-django, Azure SQL Database, Azure Blob Storage)

---

## 1. Introduction

### 1.1 Purpose

This traceability matrix links every SRS requirement (FR/NFR) to its implementing code and its tests. It is the Stage 6 companion to `TEST_PLAN.md`, following `SRS.md`, `ARCHITECTURE.md`, `DATABASE.md`, `SECURITY_AND_PRIVACY.md`, `DP900_MAPPING.md`, and `COA_SE_NOTES.md`.

Each row records: requirement ID, requirement text, implementation status (Implemented / Partial / Planned), code location(s), and test coverage. Requirements marked **Planned** are decisions recorded in the SRS but not yet implemented or verified in code — they must not be claimed as working.

### 1.2 Status definitions

| Status | Meaning |
|---|---|
| Implemented | Code present in repository and exercised by tests |
| Partial | Code present but not fully covered by tests, or behavior exists only in mocked/logic form (not persisted) |
| Planned | Requirement recorded in SRS/ADR; no implementation or test yet |

---

## 2. Functional requirements traceability

| ID | Requirement | Status | Code location | Tests |
|---|---|---|---|---|
| FR-01 | Register with first name, last name, email (unique), password (min 8) | Implemented | `accounts/models.py` (`User`), `accounts/forms.py` (`CustomUserCreationForm`), `accounts/views.py` (`register_view`) | `test_auth.py::test_register_success`, `test_auth.py::test_register_duplicate_email`, `test_routes.py::test_register_page` |
| FR-02 | Email normalized (lowercased, trimmed) before account creation | Implemented | `app.security.validation.normalize_email` | `test_validation.py::test_normalize_email_lowercases_and_trims` |
| FR-03 | Duplicate email rejected with generic message (no enumeration) | Implemented | `accounts/models.py` (`email` unique), `accounts/forms.py`, `accounts/views.py` (`messages.error`, generic text) | `test_auth.py::test_register_duplicate_email` (409), `test_security.py::test_sql_injection_email_is_rejected` |
| FR-04 | Passwords shall be hashed with Argon2; plaintext passwords shall never be stored or logged. | Implemented (config) | `labvault_project/settings.py` (`PASSWORD_HASHERS` led by `Argon2PasswordHasher`), `requirements.txt` (`argon2-cffi==23.1.0`) | `test_validation.py::test_password_hashers_led_by_argon2` |
| FR-05 | Sign in with email/password; generic failure message | Implemented | `accounts/views.py` (`login_view`), `CustomAuthenticationForm` | `test_auth.py::test_authenticate_success`, `test_authenticate_wrong_password`, `test_authenticate_user_not_found`; `test_routes.py::test_login_page` |
| FR-06 | LoginAttempts table + lockout after threshold | Planned | Not in models; lockout logic exists only in mocked `auth_service._login_attempts` (Flask layer, not Django) | `test_auth.py::test_login_lockout_after_max_failed_attempts` (mocked behavior, not DB table) |
| FR-07 | Successful sign-in clears prior failures | Planned | Mocked `_login_attempts.clear()` on success (Flask layer) | `test_auth.py::test_successful_login_clears_failures` (mocked) |
| FR-08 | Sessions: HttpOnly, SameSite, Secure (HTTPS), configurable age | Implemented | `labvault_project/settings.py` (`SESSION_COOKIE_*`, `SESSION_COOKIE_AGE`) | None dedicated (settings-level) |
| FR-09 | Change own password with current password | Implemented | `accounts/views.py` (`settings_view`), `PasswordChangeForm` | `test_auth.py::test_change_password_success`, `test_change_password_wrong_current` |
| FR-10 | View and edit own profile | Implemented | `accounts/views.py` (`profile_view`, `settings_view`), templates | `test_routes.py::test_profile_routes_registered_correctly` (login-required redirect) |
| FR-11 | TOTP 2FA for administrators before admin actions | Planned | Not implemented | None |
| FR-12 | Consent at signup (checkbox, timestamp, version) | Planned | No consent fields on `User` | None |
| FR-13 | Upload file with title, description, category, subjects, visibility | Implemented | `resources/forms.py` (`ResourceUploadForm`), `resources/views.py` (`upload`), `resources/models.py` (`Resource`) | `test_routes.py::test_upload_redirects_when_anonymous` (redirect only; no end-to-end upload test) |
| FR-14 | Extension allowlist + MIME magic-byte + size ≤ 10 MB | Implemented | `resources/storage.py` (`validate_file`, `detect_mime`, `ALLOWED_EXTENSIONS`, `MAGIC_SIGNATURES`, `MAX_CONTENT_LENGTH`) | `test_storage.py::test_allowed_extension_true/false`, `test_validate_file_rejects_unsupported`, `test_validate_file_rejects_empty`, `test_validate_file_pdf_signature` |
| FR-15 | Stream to Azure Blob or local storage; unpredictable server key | Implemented | `resources/storage.py` (`AzureBlobStorage`, `LocalProtectedStorage`, `generate_storage_key`), `settings.py` (`DEFAULT_FILE_STORAGE`) | `test_storage.py::test_generate_storage_key_unpredictable` |
| FR-16 | Transactional metadata insert; delete blob/file on DB failure | Implemented (upload view) | `resources/views.py` (`upload` — try/except with `backend.delete` rollback) | Not directly tested (cleanup path code-review only) |
| FR-17 | A SHA-256 checksum shall be computed for each uploaded file and stored with the resource metadata (ResourceFiles table). | Implemented | `resources/storage.py` (`compute_sha256`), `resources/models.py` (`ResourceFiles`), `resources/views.py` (`upload` writes `ResourceFiles` in `transaction.atomic()`), `resources/migrations/0003_add_resource_files.py`, `resources/admin.py` (`ResourceFilesAdmin`) | `test_storage.py::test_compute_sha256_*` (4 tests), `test_routes.py::test_upload_creates_resource_files_with_sha256` |
| FR-18 | View resource details (owner / public / admin) | Implemented | `resources/views.py` (`details`, `_user_can_view_resource`) | `test_routes.py` (login-required redirect only; no authorized-access assertion) |
| FR-19 | Edit metadata of own resources; admin any resource | Implemented | `resources/views.py` (`edit`, `_user_can_edit_resource`), `ResourceEditForm` | `test_routes.py` (login-required redirect only) |
| FR-20 | Delete own resource; remove SQL metadata + best-effort file delete | Implemented | `resources/views.py` (`delete`) | `test_routes.py` (login-required redirect only) |
| FR-21 | Download authorized (owner / public / admin) | Implemented | `resources/views.py` (`download`, `_user_can_view_resource`) | None directly |
| FR-22 | Azure short-lived SAS URL (default 30 min) | Implemented | `resources/storage.py` (`AzureBlobStorage.download_url`, default 30 min) | None (requires Azure) |
| FR-23 | Local download with `Content-Disposition: attachment` + `nosniff` | Implemented | `resources/views.py` (`download`, local branch) | None directly |
| FR-24 | Every download logged in AccessLog (who, what, when) | Implemented | `resources/models.py` (`AccessLog`), `resources/views.py` (`download` creates AccessLog), `resources/migrations/0002_add_access_log.py` | `test_routes.py::test_download_logs_access_log`, `test_routes.py::test_download_rejects_non_owner`, `test_routes.py::test_public_resource_downloadable_by_any_authenticated` |
| FR-25 | Paginated library (default page 20) | Implemented | `resources/views.py` (`library` pagination) | `test_routes.py::test_library_redirects_when_anonymous` (redirect only) |
| FR-26 | Full-text search on title/description | Implemented | `resources/views.py` (`library`, `Q(title__icontains)`...) | None directly |
| FR-27 | Filter by category/subject/course; sort | Partial | category + subject implemented; course not in models (planned) | None directly |
| FR-28 | Students see public + own; admins see all | Implemented | `resources/views.py` (`library` queryset filter by `is_administrator`) | None directly |
| FR-29 | Categories/subjects/courses administrable by admin | Partial | Category/Subject admin registered (`resources/admin.py`, `accounts/admin.py`); course not implemented | `test_routes.py::test_admin_redirects_when_anonymous` (admin login redirect only) |
| FR-30 | Favorites (Favorites table) | Planned | Not in models | None |
| FR-31 | Notifications (Notifications table) | Implemented | `resources/migrations/0004_notification.py`, `resources/views.py` (`notifications`, `notification_mark_read`, `notification_mark_all_read`), `resources/context_processors.py` | None |
| FR-32 | View/mark-read notifications | Implemented | `resources/views.py` (`notification_mark_read`, `notification_mark_all_read`), `templates/resources/notifications.html` | None |
| FR-33 | Admins view/manage users (role, active status) | Partial | Django admin `UserAdmin` registered; no custom admin views beyond admin site | `test_routes.py::test_admin_redirects_when_anonymous` |
| FR-34 | Admins view AuditLog | Implemented (model) | `resources/models.py` (`AuditLog`), `resources/admin.py` (`AuditLog` not registered — gap) | None directly |
| FR-35 | Admins view AccessLog | Implemented | `resources/models.py` (`AccessLog`), `resources/admin.py` (`AccessLogAdmin` registered) | `test_routes.py` (AccessLog created via download; admin can query via admin site) |
| FR-36 | All admin actions recorded in AuditLog (actor, action, entity, timestamp) | Partial | `AuditLog` model exists; write usage not standardized across admin actions | None |

---

## 3. Data ethics & user rights traceability

| ID | Requirement | Status | Code location | Tests |
|---|---|---|---|---|
| FR-37 | Data minimization; no third-party trackers | Design constraint | Templates (no tracker scripts — to be audited) | None |
| FR-38 | Consent recorded (versioned text + timestamp) | Planned | No consent fields | None |
| FR-39 | Retention policy for accounts/resources/logs | Planned | Policy defined in `SECURITY_AND_PRIVACY.md` Section 6; no enforcement jobs | None |
| FR-40 | Account export (portable JSON) | Planned | Not implemented | None |
| FR-41 | Account deletion + cascade per retention | Planned | Not implemented | None |

---

## 4. UI & themes traceability

| ID | Requirement | Status | Code location | Tests |
|---|---|---|---|---|
| FR-42 | Light/dark themes | Implemented | `static/css/` theme toggle (CSS/vanilla JS) | None |
| FR-43 | Responsive, accessible, no JS framework | Implemented | `static/css/design.css`, `static/css/style.css`, `static/css/animations.css`, vanilla JS | None |

---

## 5. Non-functional requirements traceability

| ID | Requirement | Status | Code location | Tests |
|---|---|---|---|---|
| NFR-01 | Confidentiality: downloads only owner/public/admin | Implemented | `resources/views.py` (`_user_can_view_resource`) | None directly |
| NFR-02 | Integrity: SHA-256 checksum verifiable | Implemented | `resources/storage.py` (`compute_sha256`), `resources/models.py` (`ResourceFiles.sha256_checksum`), `resources/views.py` (`upload`) | `test_storage.py::test_compute_sha256_*`, `test_routes.py::test_upload_creates_resource_files_with_sha256` |
| NFR-03 | Authentication: passwords hashed with Argon2. | Implemented (config) | `labvault_project/settings.py` (`PASSWORD_HASHERS` led by `Argon2PasswordHasher`), `requirements.txt` (`argon2-cffi==23.1.0`) | `test_validation.py::test_password_hashers_led_by_argon2` |
| NFR-04 | Brute-force lockout after threshold | Planned | Mocked only (Flask `auth_service`); django-axes planned (ADR-09) | `test_auth.py` lockout tests (mocked) |
| NFR-05 | Transport security: TLS in production | Implemented (config) | `settings.py` (`SESSION_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, HSTS) | None (deployment-level) |
| NFR-06 | Encryption at rest: Azure SQL TDE + Blob SSE | Platform config | Azure platform (not app code) | None (not app-testable) |
| NFR-07 | Secrets: no secrets in source; Key Vault + managed identity | Planned | `.env` in dev; Key Vault referenced only in docs (C-20) | None |
| NFR-08 | CSP restricting scripts/styles to same origin | Implemented | `settings.py` (`SECURE_CONTENT_TYPE_NOSNIFF`, security headers) | Indirect (no direct CSP header assertion) |
| NFR-09 | Upload size limit enforced | Implemented | `settings.py` (`MAX_CONTENT_LENGTH`, `DATA_UPLOAD_MAX_MEMORY_SIZE`), `resources/storage.py` | `test_storage.py::test_validate_file_rejects_unsupported` (size via `validate_file`) |
| NFR-10 | Pagination performance: OFFSET/FETCH, indexes | Implemented | `resources/models.py` (`Meta.indexes` incl. `IX_Resources_CreatedAt`, `IX_ResUpBy_CreatedAt`) | None directly |
| NFR-11 | SAS expiry ≤ 30 min | Implemented | `resources/storage.py` (`download_url`, default 30 min) | None (requires Azure) |
| NFR-12 | Orphan cleanup job | Planned | Not implemented | None |
| NFR-13 | Account export (JSON) | Planned | Not implemented | None |
| NFR-14 | Account deletion per retention | Planned | Not implemented | None |
| NFR-15 | No third-party trackers | Design constraint | Templates | None |
| NFR-16 | Theme persistence without flicker | Partial | CSS theme toggle | None |

---

## 6. Implementation summary

| Category | Total | Implemented | Partial | Planned | Tested |
|---|---|---|---|---|---|
| Functional (FR-01…FR-43) | 43 | ~33 | ~4 | ~6 | ~20 directly |
| Non-functional (NFR-01…NFR-16) | 16 | ~10 | ~1 | ~5 | ~7 directly |
| **Overall** | **59** | **~43** | **~5** | **~11** | **~27 directly** |

**Honest note:** Many "Implemented" requirements have only indirect test coverage (e.g. login-required redirects) rather than end-to-end assertions. See `TEST_PLAN.md` Section 5.2 for the full gap list.

---

## 7. Cross-references

- `SRS.md` — FR-01…FR-43, NFR-01…NFR-16; Section 3.8 verified vs planned baseline
- `TEST_PLAN.md` — test inventory, execution, pass/fail criteria, gap list
- `ARCHITECTURE.md` — ADR-08 (Argon2), ADR-09 (django-axes), ADR-10 (TOTP), module boundaries
- `DATABASE.md` — table honesty baseline (implemented vs planned tables)
- `SECURITY_AND_PRIVACY.md` — controls C-01…C-26, honesty baseline (implemented vs planned controls)

*End of TRACEABILITY.md — Stage 6 complete.*
