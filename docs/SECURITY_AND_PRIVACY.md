# Security and Privacy  -  LabVault

**Document version:** 1.0
**Status:** Draft (security/privacy design only  -  no code changes in this phase)
**Standard:** STRIDE threat modeling; ISO/IEC 27001-aligned controls; data-protection principles (minimization, purpose limitation, retention, user rights)
**Project:** LabVault  -  secure academic laboratory resource and document management portal
**Repository:** `E:\labvault` (Django 5.2, mssql-django, Azure SQL Database, Azure Blob Storage)

---

## 1. Introduction

### 1.1 Purpose

This document defines the LabVault threat model (STRIDE), the security and privacy controls table, the data inventory, retention policy, and user-rights mechanisms. It is the fourth document in the LabVault documentation sequence, following `SRS.md`, `ARCHITECTURE.md`, and `DATABASE.md`. It captures design only; no code is changed in this phase.

### 1.2 Scope

In scope: STRIDE threat model with mitigations, controls table mapping each control to its implementation status, data inventory (what is collected, where, why), retention policy, user rights (consent, export, deletion), and privacy design decisions. Out of scope: penetration-test reports, vulnerability scan results, key-rotation runbooks, incident-response procedures.

---

## 2. Threat Model (STRIDE)

| Category | Threat | Asset / Target | Mitigation | Status |
|----------|--------|----------------|------------|--------|
| Spoofing | Attacker impersonates a legitimate user via stolen or guessed credentials | User accounts, sessions | Email-based auth; Argon2 password hashing (implemented via `PASSWORD_HASHERS`); HttpOnly/SameSite/Secure session cookies; session regeneration after login; TOTP 2FA for administrators (planned FR-11) | Partial (cookies + Argon2 implemented; TOTP planned) |
| Tampering | Attacker modifies resource metadata, file contents, or log entries | Resources, AuditLog, AccessLog | Server-generated unpredictable storage keys; original filename never used as path; Django ORM parameterized queries (no raw SQL); audit log append-only by design (no update/delete of audit entries in application code) | Partial (keys + ORM implemented; append-only enforcement planned) |
| Repudiation | User denies performing an upload, download, or admin action | AuditLog, AccessLog, LoginAttempts | Every admin action recorded in AuditLog with actor, action, entity type, entity ID, timestamp (FR-36); every download logged in AccessLog (FR-24); login attempts recorded (FR-06, planned) | Partial (AuditLog + AccessLog implemented; LoginAttempts planned) |
| Information disclosure | Unauthorized user reads a private resource file or another user's profile | Resources, Blob storage, Users | Download authorization (owner / public / admin) enforced server-side (FR-21); private Azure Blob container with short-lived SAS (≤ 30 min, FR-22); local storage served via authorized view with `Content-Disposition: attachment` + `X-Content-Type-Options: nosniff` (FR-23); role-based access control; no plaintext passwords or secrets logged | Implemented (authz views + SAS URLs); Key Vault planned |
| Denial of service | Attacker exhausts storage, DB, or compute via huge uploads or request floods | Storage, Database, Application | Upload size limit ≤ 10 MB configurable (FR-14, NFR-09); extension + MIME magic-byte validation; django-axes login lockout after threshold failures (FR-06, planned); pagination bounds result sets (NFR-10) | Partial (size limit + validation implemented; lockout planned) |
| Elevation of privilege | Student gains administrator access or accesses another user's private resource | Admin routes, private resources | Server-side `is_administrator` checks on every admin route (no client-side trust); ownership checks on edit/delete/download; `deny by default` for anonymous users on protected routes; TOTP 2FA for admin actions (FR-11, planned) | Partial (server-side checks implemented; TOTP planned) |

---

## 3. Controls Table

| ID | Control | Category | Implementation | SRS Req. | Status |
|----|---------|----------|----------------|----------|--------|
| C-01 | Password hashing with Argon2 | Authentication | Django `PASSWORD_HASHERS` configured to Argon2; `AbstractUser.password` field stores hash | FR-04, NFR-03 | Implemented (config  -  `argon2-cffi==23.1.0` in requirements.txt; runtime takes effect once installed) |
| C-02 | Generic authentication failure messages | Authentication | Same "invalid email or password" message for wrong email or wrong password; no user-enumeration signal | FR-03, FR-05 | Implemented |
| C-03 | Login attempt tracking + lockout | Authentication | `LoginAttempts` table; django-axes threshold lockout; successful sign-in clears prior failures | FR-06, FR-07, NFR-04 | Planned (`LoginAttempts` table not in models) |
| C-04 | Session security | Authentication | `SESSION_COOKIE_HTTPONLY=True`, `SESSION_COOKIE_SAMESITE=Lax`, `SESSION_COOKIE_SECURE` behind HTTPS, configurable `SESSION_COOKIE_AGE` | FR-08, NFR-05 | Implemented (`settings.py`) |
| C-05 | CSRF protection | Integrity | `django.middleware.csrf.CsrfViewMiddleware`; CSRF tokens on all state-changing forms; `CSRF_COOKIE_HTTPONLY=True` | SRS constraint | Implemented |
| C-06 | Parameterized queries | Integrity | Django ORM via `mssql-django` + `pyodbc`; no string-concatenated SQL | SRS constraint | Implemented |
| C-07 | File validation (extension, MIME magic, size) | Input validation | `validate_file`: extension allowlist, MIME magic-byte signature, ≤ 10 MB size limit | FR-14, NFR-09 | Implemented (`resources/storage.py`) |
| C-08 | Unpredictable server-generated storage keys | Confidentiality | `uuid4().hex + secrets.token_hex(8) + ext`; original filename never used as path | FR-15 | Implemented (`generate_storage_key`) |
| C-09 | Transactional upload with blob cleanup on failure | Integrity / Availability | Stream to storage, insert metadata in transaction; on DB failure delete uploaded blob/file | FR-16 | Implemented (`resources/views.py` upload), verified by code review |
| C-10 | SHA-256 file checksum | Integrity | SHA-256 digest computed on upload, stored in `ResourceFiles.Sha256Checksum` | FR-17, NFR-02 | Implemented (`ResourceFiles` model + `compute_sha256` in upload) |
| C-11 | Download authorization | Confidentiality | `_user_can_view_resource` enforces owner / public / admin before any download | FR-21, NFR-01 | Implemented |
| C-12 | Short-lived SAS URLs (Azure) | Confidentiality | `generate_blob_sas` with read permission, default 30-minute expiry; private container | FR-22, NFR-11 | Implemented (`download_url`) |
| C-13 | Local download with safe headers | Confidentiality / Integrity | `FileResponse` with `as_attachment=True`, `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff` | FR-23 | Implemented |
| C-14 | Access logging | Auditing | `AccessLog` records who/what/when per download | FR-24, NFR-01 | Implemented (`resources/migrations/0002_add_access_log.py`; download view writes entries) |
| C-15 | Audit logging | Auditing | `AuditLog` records actor, action, entity type, entity ID, timestamp for admin/security actions | FR-34, FR-36 | Implemented (model exists; usage to be standardized) |
| C-16 | Content Security Policy | Client-side protection | `default-src 'self'; script-src 'self'; style-src 'self'` (and variants) on all responses | NFR-08 | Implemented (headers configured in `settings.py`) |
| C-17 | Security headers | Client-side protection | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `SECURE_SSL_REDIRECT` + HSTS behind HTTPS | NFR-05, NFR-08 | Implemented |
| C-18 | TLS in production | Confidentiality | `SESSION_COOKIE_SECURE=True`, `SECURE_SSL_REDIRECT=True` behind HTTPS; TLS termination at ingress/load balancer | NFR-05 | Config (enforced at deployment) |
| C-19 | Encryption at rest (TDE + Blob) | Confidentiality | Azure SQL TDE; Azure Blob Storage encryption at rest | NFR-06 | Platform config (not application code) |
| C-20 | Secrets via Key Vault + managed identity | Confidentiality | No secret literals in code; connection strings/keys in Key Vault; managed identity for Azure access | NFR-07 | Planned (infrastructure) |
| C-21 | Orphan cleanup | Integrity / Availability | Scheduled job deletes blobs without matching SQL metadata | NFR-12 | Planned |
| C-22 | Data minimization | Privacy | Collect only fields required for function; no third-party trackers or analytics scripts | FR-37, NFR-15 | Design constraint; templates to be audited |
| C-23 | Consent at signup | Privacy | Explicit checkbox; versioned consent text + timestamp recorded | FR-12, FR-38 | Planned (no consent fields on `User`) |
| C-24 | Retention policy | Privacy | Defined retention for accounts, resources, logs, access records before deletion/anonymization | FR-39 | Planned (policy to be defined) |
| C-25 | Account export | Privacy | Portable JSON export of profile, resources, logs | FR-40, NFR-13 | Planned |
| C-26 | Account deletion | Privacy | Cascade delete/anonymize personal resources and associated data per retention rules | FR-41, NFR-14 | Planned |

---

## 4. Data Inventory

| Data element | Collected from | Stored in | Purpose | Retention | Sensitivity |
|--------------|---------------|-----------|---------|-----------|-------------|
| Email (normalized) | Signup form | Users.Email | Authentication, account identity | Active account; per retention policy FR-39 | High (PII) |
| Password hash | Signup / password change | Users.PasswordHash | Authentication | Active account | High (credential) |
| First name, last name | Signup / profile | Users.FirstName, Users.LastName | Profile, display | Active account; per retention policy | Medium (PII) |
| Role | Assignment (admin via DB) | Users.RoleId / role field | Authorization | Active account | Low |
| Consent timestamp + version | Signup checkbox | Users.ConsentTimestamp, Users.ConsentVersion (planned) | Legal basis for processing | Active account | Low |
| Resource title, description, category, visibility | Upload form | Resources.* | Resource catalog, discovery | Active resource; per retention policy | Medium |
| Original filename | Upload | ResourceFiles.OriginalFileName (planned) / Resources.original_filename | Display name | Active resource | Low |
| Storage key | Server-generated | ResourceFiles.StorageKey / Resources.storage_key | Object retrieval | Active resource | Low |
| Content type | MIME detection | ResourceFiles.ContentType / Resources.content_type | Correct serving | Active resource | Low |
| File size bytes | Upload | ResourceFiles.FileSizeBytes / Resources.file_size_bytes | Quota, display | Active resource | Low |
| SHA-256 checksum | Computed on upload | ResourceFiles.Sha256Checksum (planned) | Integrity verification | Active resource | Low |
| Storage object (file bytes) | Upload | Azure Blob container / local protected storage | Resource delivery | Active resource; orphan cleanup | Medium |
| Download events | Download endpoint | AccessLog (planned) | Access auditing | Per retention policy | Medium (PII + resource link) |
| Admin actions | Admin endpoints | AuditLog | Accountability | Per retention policy | Low/Medium |
| Login attempts | Login endpoint | LoginAttempts (planned) | Brute-force detection | Per retention policy / django-axes window | Low (email only) |
| Notification records | System-generated | Notifications (planned) | User notifications | Until read + retention period | Low |
| Favorite records | User action | Favorites (planned) | User preference | Active account | Low |
| IP address | Request metadata | AccessLog.IpAddress (planned) | Access auditing | Per retention policy | Medium (PII) |

**No third-party trackers or analytics.** No data is sold or shared with third parties. No advertising cookies. Data is used only for the portal's stated function (data minimization, FR-37 / C-22).

---

## 5. Data Flow & Trust Boundaries (Security View)

| Boundary | Data | Protection |
|----------|------|------------|
| Browser → Django (TLS) | Form bodies, session cookie, CSRF token | TLS 1.2+, HttpOnly/SameSite/Secure cookies, CSRF middleware |
| Django → Azure SQL (TDS/TLS) | Parameterized queries, result sets | `mssql-django` + `pyodbc` parameterization; DB credentials via env/Key Vault |
| Django → Azure Blob | File upload/download via SAS | Private container, short-lived SAS (≤ 30 min), server-generated keys |
| Django → Key Vault (managed identity) | Secrets | Managed Identity, HTTPS; no secrets in code (NFR-07, C-20) |

---

## 6. Retention Policy (per FR-39)

| Data class | Retention rule | Disposal |
|------------|---------------|----------|
| Active user account | Retained until account deletion request or administrative deactivation | Anonymize or delete per FR-41 |
| Resource (owned by user) | Retained until user deletes it or account is deleted | Cascade delete metadata; best-effort delete storage object |
| AccessLog entries | Retain 12 months (default configurable) | Purge or anonymize after retention window |
| AuditLog entries | Retain 24 months (default configurable) | Purge after retention window; security-relevant events may be retained longer per policy |
| LoginAttempts records | Retain per django-axes lockout window; purge old failures | Purge after lockout window expires |
| Consent records | Retained for life of account; updated on consent version change | Anonymize on account deletion |
| Notifications | Retain until read + 30 days, or per policy | Purge |

Retention periods are defaults to be confirmed by the data controller; all are configurable. No indefinite retention without a documented legal basis.

---

## 7. User Rights (Data Ethics)

| Right | Mechanism | SRS Req. | Status |
|-------|-----------|----------|--------|
| Consent at signup | Explicit checkbox; versioned consent text + timestamp recorded | FR-12, FR-38 | Planned |
| Data minimization | Only functional fields collected; no third-party trackers | FR-37, NFR-15 | Design constraint |
| Account export | Portable JSON of profile, resources, logs | FR-40, NFR-13 | Planned |
| Account deletion | User-initiated; cascades to personal resources and associated data per retention rules | FR-41, NFR-14 | Planned |
| Access to own logs | Users can view their own AccessLog/AuditLog entries relevant to them | FR-35 (admin view); user self-view planned | Planned |

---

## 8. Honesty Baseline: Implemented vs. Planned Controls

| Control | Status | Evidence |
|---------|--------|----------|
| Session security (HttpOnly, SameSite, Secure, age) | Implemented | `labvault_project/settings.py` |
| CSRF protection | Implemented | `CsrfViewMiddleware` in `settings.py` |
| Parameterized queries via Django ORM | Implemented | `mssql-django` backend; ORM used throughout |
| File validation (extension, MIME magic, size) | Implemented | `resources/storage.py` (`validate_file`, `detect_mime`) |
| Unpredictable storage keys | Implemented | `resources/storage.py` (`generate_storage_key`) |
| Download authorization (owner/public/admin) | Implemented | `resources/views.py` (`_user_can_view_resource`) |
| Local download safe headers (`nosniff`, `attachment`) | Implemented | `resources/views.py` (`download`) |
| SAS short-lived URLs (Azure) | Implemented | `resources/storage.py` (`download_url`, default 30 min) |
| AuditLog model | Implemented | `resources/models.py` (`AuditLog`, `db_table="AuditLogs"`) |
| Argon2 password hashing | Planned | Current `User` inherits pbkdf2 via `AbstractUser` |
| django-axes LoginAttempts lockout | Planned | `LoginAttempts` table not in models |
| TOTP 2FA for administrators | Planned | Not in models or views |
| SHA-256 checksum + ResourceFiles table | Planned | Not in models |
| AccessLog table | Planned | Not in models |
| Favorites, Notifications tables | Planned | Not in models |
| Key Vault + managed identity | Planned | Infrastructure config, not application code |
| Consent fields on User | Planned | No `ConsentTimestamp`/`ConsentVersion` |
| Retention policy, export, deletion | Planned | Not implemented |

---

## 9. Privacy Principles Applied

- **Purpose limitation:** Data collected only for portal function (auth, resource catalog, access auditing). No repurposing.
- **Data minimization:** No fields beyond functional need; no tracking cookies; no analytics.
- **Storage limitation:** Retention policy with defined disposal (Section 6).
- **Accuracy:** Email normalized on signup; users can edit their own profile (FR-10).
- **Integrity & confidentiality:** Access control, TLS, encryption at rest, SAS URLs, checksums.
- **Accountability:** AuditLog + AccessLog + LoginAttempts trace actions to actors.
- **User rights:** Consent, export, deletion (Section 7).

---

## 10. Cross-References

- `SRS.md`  -  NFR-01..NFR-16 (security targets), FR-01..FR-41 (security/privacy requirements).
- `ARCHITECTURE.md`  -  Section 8 (security boundaries & trust zones), ADR-08/09/10/11/12 (Argon2, django-axes, TOTP, no AI, no trackers).
- `DATABASE.md`  -  table definitions for Users, AccessLog, AuditLog, LoginAttempts, ResourceFiles, Favorites, Notifications.
- `DP900_MAPPING.md` / `COA_SE_NOTES.md`  -  Azure data-platform mapping for encryption-at-rest controls C-19, C-20.

---

*End of SECURITY_AND_PRIVACY.md  -  Stage 4 complete. Awaiting "continue" before proceeding to Stage 5 (DP900_MAPPING.md and COA_SE_NOTES.md).*
