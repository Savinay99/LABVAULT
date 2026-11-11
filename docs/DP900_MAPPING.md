# Azure Data Platform Mapping  -  LabVault

**Document version:** 1.0
**Status:** Draft (design only  -  no code changes in this phase)
**Standard:** Microsoft Azure Data Fundamentals (DP900) domains  -  relational data, non-relational/object data, key management  -  mapped to LabVault controls
**Project:** LabVault  -  secure academic laboratory resource and document management portal
**Repository:** `E:\labvault` (Django 5.2, mssql-django, Azure SQL Database, Azure Blob Storage)

---

## 1. Introduction

### 1.1 Purpose

This document maps LabVault's data storage, encryption, and access controls to the Azure data platform services that host them. It is the fifth document in the LabVault documentation sequence, following `SRS.md`, `ARCHITECTURE.md`, `DATABASE.md`, and `SECURITY_AND_PRIVACY.md`. It captures mapping only; no code is changed in this phase.

### 1.2 Scope

In scope: Azure SQL Database (relational), Azure Blob Storage (non-relational/object), Azure Key Vault (secrets/key management), Microsoft Entra ID managed identity (workload authentication), and how each LabVault control from `SECURITY_AND_PRIVACY.md` (C-01…C-26) is realized on the platform. Out of scope: application code internals already covered in other docs, CI/CD pipelines, IaC templates, penetration testing, key-rotation runbooks.

---

## 2. Azure data services inventory

| Service | Role in LabVault | Data stored | LabVault access path |
|---|---|---|---|
| Azure SQL Database | Relational system of record | Users, Categories, Subjects, Resources, ResourceSubjects, AuditLog; planned: Roles, Courses, ResourceFiles, LoginAttempts, AccessLog, Favorites, Notifications | Django ORM via `mssql-django` + `pyodbc` over TDS/TLS (`labvault_project/settings.py` DATABASES) |
| Azure Blob Storage | Object/file store | Uploaded resource files (storage objects) in a private container | `resources.storage.AzureBlobStorage` (`save`, `delete`, `download_url`); dev fallback `LocalProtectedStorage` |
| Azure Key Vault | Secrets & key management | DB credentials, storage connection string, signing/encryption keys | Planned: managed identity (C-20); currently env vars via `.env` |
| Microsoft Entra ID (managed identity) | Workload identity | N/A (identity, not data) | Planned: DB + Key Vault auth without secrets (C-20) |

---

## 3. Control-to-service mapping (from SECURITY_AND_PRIVACY.md)

| Control | Requirement | Azure service / feature | Realization | Status |
|---|---|---|---|---|
| C-06 | Parameterized queries | Azure SQL Database | Django ORM + `mssql-django` + `pyodbc`; no string-concatenated SQL | Implemented |
| C-19 | Encryption at rest (DB) | Azure SQL Database TDE | Platform-managed TDE; optional customer-managed key in Key Vault | Platform config (not app code) |
| C-19 | Encryption at rest (files) | Azure Blob Storage SSE | Storage Service Encryption enabled on the storage account | Platform config |
| C-20 | Secrets via Key Vault + managed identity | Azure Key Vault + Entra ID managed identity | Connection string/Key Vault references; no secret literals in code | Planned (infrastructure) |
| C-12 | Short-lived SAS URLs | Azure Blob Storage SAS | `generate_blob_sas`, 30-min default expiry, read-only permission | Implemented (`download_url`) |
| C-08 | Unpredictable storage keys | Azure Blob Storage blob names | `uuid4().hex + secrets.token_hex(8) + ext` | Implemented (`generate_storage_key`) |
| C-07 | File validation | App layer (Azure not involved) | Extension allowlist + MIME magic-byte + size ≤ 10 MB | Implemented (`validate_file`) |
| C-11 / C-13 | Download authorization | Azure SQL (authz) + Blob (SAS) / local stream | `_user_can_view_resource` gate before SAS or `FileResponse` | Implemented |
| C-14 / C-15 | Access & audit logging | Azure SQL Database (AccessLog, AuditLog tables) | `AuditLog` model implemented; `AccessLog` planned | Partial |
| C-21 | Orphan cleanup | Azure Blob Storage + Azure SQL | Planned scheduled job: delete blobs without matching metadata | Planned |

---

## 4. Encryption at rest

### 4.1 Azure SQL Database  -  TDE

Transparent Data Encryption encrypts the database at rest (data files, log files, backups). LabVault relies on platform-managed TDE by default. An upgrade path uses a customer-managed key stored in Azure Key Vault (this is where C-20 meets C-19 for DB encryption keys). The application connects over TDS with TLS; `DB_ENCRYPT=yes` sets `Encrypt=yes;TrustServerCertificate=no` in `settings.py`.

### 4.2 Azure Blob Storage  -  SSE

Storage Service Encryption encrypts blob data at rest using Microsoft-managed keys by default. Customer-managed keys via Key Vault are the upgrade path. The container is private (no public access); files are served only through short-lived SAS URLs or through the authorized local view.

---

## 5. Network & connectivity

- Browser → Django: HTTPS/TLS 1.2+ (terminated at load balancer/ingress; HSTS when `SECURE_SSL_REDIRECT=true`)
- Django → Azure SQL: TDS over TLS (port 1433); SQL login or Microsoft Entra ID / managed identity
- Django → Azure Blob: HTTPS; private container, SAS for delegated read
- Django → Key Vault: HTTPS; managed identity (planned)

---

## 6. Identity & access

- Application identity: planned managed identity assigned to the Azure VM/App Service, granted Key Vault Get/List and (optionally) SQL access.
- Database credentials: currently `DB_USER`/`DB_PASSWORD` from `.env`; planned move to Key Vault.
- End users: Django `accounts.User` (email-based), stored in Azure SQL; role-based authorization (`student`/`administrator`) enforced in application code (`is_administrator`, `_user_can_edit_resource`, `_user_can_view_resource`).

---

## 7. Backup, retention & disaster recovery

- Azure SQL Database: automated backups + geo-backup; point-in-time restore. Backup is a platform capability, not application code.
- Retention: FR-39 defines application-level retention (AccessLog 12 months default, AuditLog 24 months default, LoginAttempts per lockout window). Purging is application responsibility (planned).
- Orphan cleanup (C-21): planned job to remove blobs lacking matching `Resource` metadata.

---

## 8. Honesty baseline: implemented vs planned

| Item | Status | Evidence |
|---|---|---|
| `mssql-django` → Azure SQL over TDS/TLS | Implemented | `settings.py` DATABASES (mssql engine) |
| Azure Blob Storage backend + SAS | Implemented | `resources/storage.py` `AzureBlobStorage`, `download_url` (default 30 min) |
| Local protected-storage fallback | Implemented | `LocalProtectedStorage` under `MEDIA_ROOT` |
| Unpredictable storage keys | Implemented | `generate_storage_key` (`uuid4().hex + secrets.token_hex(8) + ext`) |
| File validation (ext / MIME / size) | Implemented | `validate_file` (`resources/storage.py`) |
| TDE on Azure SQL | Platform config | Enabled on the Azure resource, not in app code |
| Blob SSE | Platform config | Enabled on the storage account, not in app code |
| Key Vault + managed identity (C-20) | Planned | `.env` still holds `DB_USER`/`DB_PASSWORD`; Key Vault referenced only in docs |
| `AccessLog` table (C-14) | Implemented | `resources/migrations/0002_add_access_log.py`; download view writes entries |
| Orphan cleanup job (C-21) | Planned | No scheduled job exists |

---

## 9. Cross-references

- `SECURITY_AND_PRIVACY.md`  -  controls C-01…C-26, STRIDE threat model, data inventory, retention policy
- `ARCHITECTURE.md`  -  deployment diagram (Section 4), ADR-02 (`mssql-django`), ADR-03 (Azure/local storage), ADR-07 (SAS), Section 8 security boundaries
- `DATABASE.md`  -  table definitions, indexes, migration approach, honesty baseline (implemented vs planned tables)
- `SRS.md`  -  NFR-05, NFR-06, NFR-07 (security targets), FR-14…FR-17 (storage), FR-24 (access logging)

*End of DP900_MAPPING.md  -  Stage 5 document 1 of 2. COA_SE_NOTES.md follows.*
