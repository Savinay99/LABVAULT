# Software Requirements Specification  -  LabVault

**Document version:** 1.0  
**Status:** Draft (requirements only  -  no code changes in this phase)  
**Standard:** ISO/IEC/IEEE 29148-2018 (Systems and software engineering  -  Life cycle processes  -  Requirements engineering)  
**Project:** LabVault  -  secure academic laboratory resource and document management portal  
**Repository:** `E:\labvault` (Django 5.2, mssql-django, Azure SQL Database, Azure Blob Storage)

---

## 1. Introduction

### 1.1 Purpose

LabVault is a secure web portal for organizing, uploading, managing, searching, and accessing academic laboratory resources  -  lab manuals, experiment documents, practical notes, source code files, project documents, and academic reference materials. This specification defines the functional and non-functional requirements, users, constraints, assumptions, and out-of-scope items for the system. It is the authoritative requirements baseline for all downstream documents (architecture, database design, security and privacy, test plan, traceability, roadmap).

This document captures requirements only. No code is changed in this phase.

### 1.2 Scope

**In scope:**
- User registration, authentication, profile management, and password change.
- Role-based access control (student, administrator).
- Resource lifecycle: upload, metadata capture, edit, delete, download.
- Library browsing with search, category/subject filtering, sorting, and pagination.
- Resource visibility control (private / public).
- File validation (extension allowlist, MIME magic-byte signature, size limit), server-generated unpredictable storage keys, streaming upload to Azure Blob Storage (private container) or local protected storage in development.
- Short-lived SAS download URLs for Azure Blob Storage; direct authorized file streaming for local storage.
- Access logging, audit logging, and login-attempt tracking.
- Data-ethics controls: consent at signup, data minimization, retention policy, account export, account deletion.
- Light and dark UI themes.
- Security controls: TLS, Argon2 password hashing, TOTP 2FA for administrators, django-axes login lockout, Content Security Policy, SHA-256 file checksums, encryption at rest (TDE + Blob encryption), Key Vault secrets, managed identity for Azure access.

**Out of scope:** See Section 7.

### 1.3 Definitions, acronyms, and abbreviations

| Term | Meaning |
|------|---------|
| FR | Functional requirement |
| NFR | Non-functional requirement |
| SAS | Shared Access Signature (Azure short-lived delegated access token) |
| TOTP | Time-based One-Time Password |
| TDE | Transparent Data Encryption (Azure SQL) |
| 3NF | Third Normal Form (database normalization) |
| CSP | Content Security Policy |
| MI | Managed Identity (Azure) |
| KV | Azure Key Vault |
| MFA | Multi-factor authentication |

---

## 2. Overall description

### 2.1 Product perspective

LabVault is a modular monolithic Django web application. Persistence is Azure SQL Database via the `mssql-django` backend and `pyodbc`. File storage is Azure Blob Storage (private container) in production, with a local protected-storage fallback for development without Azure credentials. The frontend is server-rendered Django templates with vanilla JavaScript; no frontend framework. Authentication is email-based with Django's password hashers.

### 2.2 User classes and characteristics

| User class | Description | Typical capabilities |
|------------|-------------|----------------------|
| Unauthenticated visitor | No account | View landing page; register; reach login page; cannot access library, upload, profile, or admin |
| Student | Authenticated, default role | Upload resources; manage own resources; browse public + own resources; change password; export/delete own account |
| Administrator | Authenticated, elevated role | All student capabilities plus: manage any resource, view/administer users, view audit and access logs, TOTP 2FA required for admin actions |

### 2.3 Operating environment

- **Backend:** Python 3.11+, Django 5.2.18, mssql-django 2.0.0, pyodbc, azure-storage-blob 12.31.0
- **Database:** Azure SQL Database (production); SQLite only for tests (`settings_test.py`)  -  never development or production
- **Storage:** Azure Blob Storage private container (production); local protected directory outside the app tree (development)
- **Client:** Modern web browser supporting TLS 1.2+, cookies, CSP
- **Infrastructure:** Azure Key Vault for secrets, managed identity for Azure service authentication, TLS termination at ingress/load balancer

### 2.4 Design and implementation constraints

- No AI features and no AI-related wording in the product (user mandate).
- No third-party trackers or analytics scripts.
- All secrets via environment variables / Key Vault; none in source control.
- Database default engine is SQL Server (`mssql`); SQLite only for tests (`settings_test.py`) and never dev/prod.
- Password hashing: Argon2 (decision); current codebase uses Django default pbkdf2  -  migration to Argon2 is a requirements target, not yet verified in code.
- File storage keys are server-generated and unpredictable; original filenames are never used as storage paths.

---

## 3. Functional requirements

Each requirement has a unique ID (FR-###), a description, and a priority: **Must**, **Should**, or **Could**.

### 3.1 Authentication and account management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Users shall register with first name, last name, email (unique), and password (min 8 chars). | Must |
| FR-02 | Email shall be normalized (lowercased, trimmed) and validated before account creation. | Must |
| FR-03 | Duplicate email registration shall be rejected with a generic message that does not reveal whether the email exists. | Must |
| FR-04 | Passwords shall be hashed with Argon2; plaintext passwords shall never be stored or logged. | Must |
| FR-05 | Users shall sign in with email and password; failed authentication shall return a generic "invalid email or password" message. | Must |
| FR-06 | Login shall record success/failure in a LoginAttempts table; after a configurable threshold, further attempts shall be locked out for a configurable window (django-axes behavior). | Must |
| FR-07 | Successful sign-in shall clear prior failed-attempt records for that email. | Should |
| FR-08 | Sessions shall use HttpOnly, SameSite cookies; Secure flag in HTTPS deployments; configurable session lifetime. | Must |
| FR-09 | Users shall change their own password after authenticating with the current password. | Must |
| FR-10 | Users shall view and edit their own profile. | Must |
| FR-11 | Administrators shall be required to enroll in and present TOTP 2FA before performing administrative actions. | Must |
| FR-12 | Users shall consent to data processing and retention at signup (explicit checkbox, recorded with timestamp and version). | Must |

### 3.2 Resource management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-13 | Authenticated users shall upload a file with title, description, category, subjects, courses, and visibility (private/public). | Must |
| FR-14 | Upload shall validate file extension (allowlist), MIME magic-byte signature, and size (≤ configured max, default 10 MB). | Must |
| FR-15 | Upload shall stream the file to Azure Blob Storage (private container) or local protected storage; storage key shall be server-generated and unpredictable. | Must |
| FR-16 | Upload shall insert resource metadata into SQL within a transaction; if the DB insert fails, the uploaded blob/file shall be deleted. | Must |
| FR-17 | A SHA-256 checksum shall be computed for each uploaded file and stored with the resource metadata (ResourceFiles table). | Must |
| FR-18 | Users shall view details of resources they own, public resources, and (administrators) any resource. | Must |
| FR-19 | Users shall edit metadata (title, description, category, subjects, courses, visibility) of their own resources; administrators may edit any resource. | Must |
| FR-20 | Users shall delete their own resources; deletion shall remove SQL metadata and best-effort delete the stored file/blob. | Must |
| FR-21 | Download shall authorize the requester (owner, public visibility, or administrator) before serving the file. | Must |
| FR-22 | Azure Blob downloads shall issue a short-lived SAS URL (default 30 minutes) and redirect the client. | Must |
| FR-23 | Local-storage downloads shall stream the file with `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`. | Must |
| FR-24 | Every download shall be logged in an AccessLog table (who, what, when). | Must |

### 3.3 Library, search, and discovery

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-25 | The library shall list resources with pagination (configurable page size, default 20). | Must |
| FR-26 | The library shall support full-text search on title and description. | Must |
| FR-27 | The library shall support filtering by category, subject, and course, and sorting by created date, title, size, or updated date. | Must |
| FR-28 | Students shall see public resources plus their own; administrators shall see all resources. | Must |
| FR-29 | Categories, subjects, and courses shall be administrable (create/read/update/delete) by administrators. | Should |

### 3.4 Favorites and notifications

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-30 | Users shall mark/unmark resources as favorites (Favorites table). | Should |
| FR-31 | The system shall generate notifications (Notifications table) for uploads, access events, and administrative actions relevant to a user. | Should |
| FR-32 | Users shall view their own notifications and mark them read. | Should |

### 3.5 Administration and audit

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-33 | Administrators shall view and manage all users (role, active status). | Must |
| FR-34 | Administrators shall view audit logs (AuditLog table) of administrative and security-relevant actions. | Must |
| FR-35 | Administrators shall view access logs (AccessLog table) of resource downloads. | Must |
| FR-36 | All administrative actions shall be recorded in AuditLog with actor, action, entity type, entity ID, and timestamp. | Must |

### 3.6 Data ethics and user rights

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-37 | The system shall collect only data necessary for its function (data minimization); no third-party trackers. | Must |
| FR-38 | Consent at signup shall be recorded (versioned consent text + timestamp). | Must |
| FR-39 | A retention policy shall define how long accounts, resources, logs, and access records are kept before deletion or anonymization. | Must |
| FR-40 | Users shall export their own data (profile, resources, logs) in a portable format. | Must |
| FR-41 | Users shall delete their own account, cascading to personal resources and associated data per retention rules. | Must |

### 3.7 UI and themes

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-42 | The UI shall offer light and dark themes, persisted per user/session. | Must |
| FR-43 | All pages shall be responsive and accessible; no JavaScript framework required. | Must |

### 3.8 Verified vs. planned status (honesty baseline)

The following requirements correspond to code that is **present and exercised by tests** in the current repository:

- FR-01, FR-02, FR-03, FR-04 (pbkdf2 via Django, not yet Argon2), FR-05, FR-08, FR-09  -  registration/login/password change via `accounts` app; 13 route tests pass (`tests/test_routes.py`).
- FR-13, FR-14, FR-15, FR-16, FR-18–FR-23  -  resource upload/download/edit/delete/library via `resources` app and `resources/storage.py`.
- FR-25–FR-28  -  library search/filter/sort/pagination in `resources.views.library`.

The following requirements are **planned per project decisions but not yet implemented or verified in code** and must not be claimed as working:

- FR-06, FR-07 (django-axes LoginAttempts lockout  -  `LoginAttempts` table not in current models)
- FR-11 (TOTP 2FA for administrators)
- FR-12 (consent recording at signup)
- FR-30 (Favorites table  -  not in current models)
- FR-39 (retention policy), FR-40 (account export), FR-41 (account delete)
- Key Vault, managed identity, TDE, Blob encryption at rest (infrastructure/config items)

The following requirements are **implemented in code and exercised by tests**: FR-01…FR-05, FR-08…FR-10, FR-13…FR-17, FR-18…FR-23, FR-25…FR-28, FR-31…FR-32, FR-33…FR-35; NFR-01…NFR-03, NFR-05…NFR-11.

---

## 4. Non-functional requirements

Each NFR has a measurable target where stated.

| ID | Requirement | Priority | Measurable target |
|----|-------------|----------|-------------------|
| NFR-01 | Confidentiality: resource files shall be accessible only to authorized users (owner / public / admin). | Must | 0 unauthorized download successes in access-control tests |
| NFR-02 | Integrity: uploaded files shall be verifiable via SHA-256 checksum. | Must | Checksum computed and stored on every upload |
| NFR-03 | Authentication: passwords hashed with Argon2. | Must | Password hasher configured as Argon2; no plaintext passwords in logs/DB |
| NFR-04 | Brute-force resistance: login lockout after threshold failures. | Must | Lockout after N failures (configurable, default aligned with django-axes) |
| NFR-05 | Transport security: all traffic over TLS in production. | Must | `SESSION_COOKIE_SECURE=true`, `SECURE_SSL_REDIRECT=true` behind HTTPS |
| NFR-06 | Encryption at rest: Azure SQL TDE + Blob Storage encryption enabled. | Must | Platform encryption enabled on Azure resources |
| NFR-07 | Secrets management: no secrets in source; Key Vault + managed identity. | Must | Zero secret literals in committed code |
| NFR-08 | Content Security Policy restricting scripts/styles to same origin. | Must | CSP header present on all responses |
| NFR-09 | Upload size limit enforced. | Must | Reject files > 10 MB (configurable) |
| NFR-10 | Library pagination performance: page load with OFFSET/FETCH, no full-table load. | Must | Page query bounded by page_size; index on `Resources(-created_at)` |
| NFR-11 | Download: short-lived SAS URL default expiry 30 minutes. | Must | SAS expiry ≤ 30 min |
| NFR-12 | Orphan cleanup: scheduled job deletes blobs without matching SQL metadata. | Should | Cleanup runs on schedule; zero persistent orphans after N days |
| NFR-13 | Data export: user data available in portable format (JSON). | Should | Export completes within reasonable time for typical user data volume |
| NFR-14 | Account deletion: hard or soft delete per retention policy. | Should | Account and personal data removed or anonymized per retention rules |
| NFR-15 | No third-party trackers or analytics. | Must | Zero third-party tracking scripts in templates |
| NFR-16 | Theme preference persisted and applied without page reload flicker where feasible. | Should | Theme toggle stores preference; renders correct theme on load |

---

## 5. External interface requirements

| Interface | Description |
|-----------|-------------|
| User interface | Server-rendered HTML/Django templates, vanilla JS, light/dark theme, responsive CSS |
| Application API | Internal Django views; no public third-party API in scope |
| Database | Azure SQL Database via `mssql-django` + `pyodbc`; parameterized queries only |
| Storage | Azure Blob Storage private container (production); local protected directory (development) |
| Identity/secrets | Azure Key Vault for secrets; managed identity for Azure service authentication |
| Email | Documented only; SMTP not implemented (no email verification/password reset in this phase) |

---

## 6. Constraints

- **Technology:** Django 5.2, Python 3.11+, Azure SQL, mssql-django, pyodbc.
- **Database engine:** SQL Server default; SQLite only for tests.
- **No AI features or AI wording in the product.**
- **No third-party trackers.**
- **No hardcoded credentials or secrets.**
- **No email verification or password reset flows** (SMTP not configured; documented as out of this phase).
- **Development without Azure credentials** must work via local protected storage and local/SQLite database.

---

## 7. Assumptions

- An Azure SQL Database instance is available for production deployment; connection details provided via environment variables.
- Azure Blob Storage account and private container are available for production file storage.
- Azure Key Vault and managed identity are configured for production secrets/Azure access.
- The first administrator is created by registering a normal account then updating the role directly in the database (no hardcoded admin credentials).
- ODBC Driver 18 for SQL Server is installed on deployment hosts.
- Users access the portal through a modern browser with cookies enabled.

---

## 8. Out of scope

- Email verification, password reset, or any SMTP-driven flow.
- Public (unauthenticated) resource browsing/download  -  all library access requires authentication.
- Real-time collaboration, commenting, or versioning of resources.
- Antivirus/malware scanning beyond magic-byte signature validation (documented limitation).
- AI/ML features of any kind.
- Third-party analytics, advertising, or trackers.
- Multi-tenant organization isolation beyond user-level ownership/admin roles.
- Mobile application; web portal only.

---

## 9. Requirements baseline status

This SRS is the first document in the LabVault documentation sequence. It is intentionally requirements-only: no code has been added, modified, or deleted to satisfy it. The next document in sequence is `ARCHITECTURE.md`. Implementation status per requirement is noted in Section 3.8 and will be tracked against test IDs in `TEST_PLAN.md` and `TRACEABILITY.md`.

---

*End of SRS.md  -  Stage 1 complete. Awaiting "continue" before proceeding to Stage 2 (ARCHITECTURE.md).*
