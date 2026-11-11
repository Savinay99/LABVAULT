# Cloud Operations Architecture — Security Engineering Notes — LabVault

**Document version:** 1.0
**Status:** Draft (operations/security engineering notes — no code changes in this phase)
**Standard:** Cloud operations / security engineering practice (Azure Well-Architected-aligned: security, reliability, operational excellence pillars)
**Project:** LabVault — secure academic laboratory resource and document management portal
**Repository:** `E:\tryis` (Django 5.2, mssql-django, Azure SQL Database, Azure Blob Storage)

---

## 1. Introduction

### 1.1 Purpose

These notes capture how LabVault is operated and secured on Azure: deployment topology, secret management, identity, encryption, networking, observability, and operational procedures. It is the second half of Stage 5, following `DP900_MAPPING.md`. Operations notes only; no code is changed in this phase.

### 1.2 Scope

In scope: deployment topology, Key Vault + managed identity integration, encryption-at-rest configuration (TDE, Blob SSE), network controls, logging/audit aggregation, backup verification, retention enforcement, orphan cleanup, and the gap between current code and planned production state. Out of scope: CI/CD pipelines, IaC templates, incident-response runbooks, penetration tests.

---

## 2. Deployment topology

```mermaid
graph TD
    subgraph Client [Client Tier]
        Browser[Web Browser / TLS 1.2+]
    end

    subgraph Edge [Edge / Ingress]
        LB[Load Balancer / Ingress<br/>TLS termination, WAF]
    end

    subgraph AppTier [Application Tier — Azure VM / App Service]
        Django[Django Application<br/>Gunicorn / uWSGI workers]
        KVRef[App config reads Key Vault refs<br/>via managed identity (planned)]
    end

    subgraph DataTier [Data Tier — Azure]
        SQL[(Azure SQL Database<br/>TDE, geo-backup, firewall)]
        Blob[(Azure Blob Storage<br/>private container, SSE)]
        KV[(Azure Key Vault<br/>secrets, certificates, keys)]
    end

    Browser <-->|HTTPS| LB
    LB <-->|HTTPS| Django
    Django -->|TDS (TLS)| SQL
    Django -->|HTTPS / SAS| Blob
    Django -->|Managed Identity| KV
```

---

## 3. Secret management & Key Vault

### Current state (development)

Secrets live in `.env` (`DJANGO_SECRET_KEY`, `DB_USER`, `DB_PASSWORD`, optionally `AZURE_STORAGE_CONNECTION_STRING`); `settings.py` reads them via `os.environ`. `.env` is gitignored (`.gitignore`) and never committed. No secrets are stored in `settings.py` itself.

### Planned production state (C-20)

Connection strings and keys stored in Azure Key Vault. The app retrieves them at runtime via a system-assigned managed identity on the App Service / VM. No secret literals in code; `.env` removed from production.

Key Vault access (access policy or RBAC): the managed identity gets `Get` and `List` on secrets, and optionally `Get` on keys when customer-managed keys protect TDE or Blob SSE.

---

## 4. Encryption at rest — configuration notes

### Azure SQL Database — TDE

Enable TDE on the database (platform-managed key by default). For customer-managed keys: create a key in Key Vault, grant the SQL server's managed identity access to the Key Vault, and set the server key as the TDE protector.

Set `DB_ENCRYPT=yes` so `settings.py` adds `Encrypt=yes;TrustServerCertificate=no` for certificate validation on the TDS connection in production.

### Azure Blob Storage — SSE

SSE is enabled by default on the storage account (Microsoft-managed keys). For customer-managed keys, configure encryption with a Key Vault key and grant the storage account's managed identity access to that Key Vault.

---

## 5. Identity & access control

### Workload identity

System-assigned managed identity on the compute resource; grant Key Vault `secrets` read and (optionally) `keys` read. This is how the app authenticates to Key Vault and, optionally, to Azure SQL without embedded credentials.

### SQL authentication

Two modes supported by `settings.py`:

- SQL login: `DB_USER`/`DB_PASSWORD` (dev default; planned to move into Key Vault)
- Windows trusted connection: `DB_TRUSTED_CONNECTION=yes`

Production should prefer Key Vault-stored credentials or Microsoft Entra ID authentication.

### End-user authorization

Django `is_administrator` and `_user_can_view_resource` / `_user_can_edit_resource` enforce server-side; no client-side trust. Admin actions are additionally planned to require TOTP 2FA (SRS FR-11).

---

## 6. Network security

- TLS termination at the load balancer / ingress; backend connections to Azure services over TLS (TDS for SQL, HTTPS for Blob and Key Vault).
- Azure SQL firewall: allow only the application's outbound IP, or use VNet integration / private endpoint.
- Azure Blob Storage container: private (no public access); access via SAS, account key, or managed identity.
- Security headers configured in `settings.py`: CSP (`SECURE_CONTENT_TYPE_NOSNIFF=True`), `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, plus HSTS and `SECURE_SSL_REDIRECT` when `SESSION_COOKIE_SECURE=true`.
- `SESSION_COOKIE_SECURE=true` and `CSRF_TRUSTED_ORIGINS` configured behind HTTPS.

---

## 7. Observability & auditing

### Application logs

`LOGGING` in `settings.py` streams to console, captured by Azure App Service / container logs. Log level controlled by `DJANGO_LOG_LEVEL`.

### Audit trail (application layer)

- `AuditLog` (`resources.models.AuditLog`, `db_table="AuditLogs"`): records actor, action, entity type, entity ID, timestamp for admin/security actions. Model implemented; usage to be standardized across all admin actions.
- `AccessLog`: implemented (migration `0002_add_access_log.py`); download view writes an entry per authorized download (SRS FR-24).
- `LoginAttempts`: planned for django-axes threshold lockout (SRS FR-06/FR-07). Not yet in models.

### Platform layer

Enable Azure Monitor / diagnostic settings on Azure SQL Database and Blob Storage for platform-level metrics and activity logs; route to Log Analytics or a storage account with its own retention.

---

## 8. Operational procedures

### Backup verification

Azure SQL automated backups + geo-backup; test point-in-time restore on a cadence. Enable Blob soft-delete / versioning as an additional guard against accidental deletion.

### Retention enforcement (SRS FR-39)

Scheduled jobs to purge `AccessLog` entries older than 12 months (default), `AuditLog` older than 24 months (default), `LoginAttempts` after the lockout window, and anonymize/delete personal data on account deletion (SRS FR-41 / NFR-14). None of these jobs exist yet.

### Orphan cleanup (C-21)

Scheduled job comparing Blob container contents against `Resource.storage_key` rows; delete blobs without matching database metadata.

### Secret rotation

Rotate Key Vault secrets and SQL passwords on a schedule; update any cached connection strings. When rotating customer-managed keys, create a new key version in Key Vault, re-encrypt data, then deprecate the old version after backups are confirmed.

---

## 9. Gap summary: current code vs planned production state

| Area | Current (code) | Planned production | Status |
|---|---|---|---|
| Secret storage | `.env` + `settings.py` `os.environ` | Azure Key Vault + managed identity | Planned (C-20) |
| DB encryption | None in code (platform TDE) | TDE + optional customer-managed key | Platform config |
| Blob encryption | None in code (platform SSE) | SSE + optional customer-managed key | Platform config |
| `AccessLog` table | Implemented | Implemented (FR-24) | Implemented |
| `LoginAttempts` lockout | Not in models | Planned via django-axes (FR-06/FR-07) | Planned |
| Orphan cleanup job | None | Planned scheduled job (C-21) | Planned |
| TOTP 2FA for admins | Not implemented | Planned (FR-11) | Planned |
| Retention enforcement jobs | None | Scheduled purge jobs (FR-39, FR-41) | Planned |

---

## 10. Cross-references

- `SECURITY_AND_PRIVACY.md` — controls C-01…C-26, STRIDE threat model, retention policy, data inventory
- `DP900_MAPPING.md` — Azure data platform service mapping for C-19 / C-20
- `ARCHITECTURE.md` — deployment diagram (Section 4), ADR-02 / ADR-03 / ADR-07, module boundaries, security boundaries & trust zones (Section 8)
- `DATABASE.md` — table definitions, indexes, migration approach
- `SRS.md` — FR-06, FR-11, FR-14…FR-17 (storage), FR-24 (access logging), FR-39…FR-41 (retention, export, deletion); NFR-05…NFR-07

*End of COA_SE_NOTES.md — Stage 5 complete. Awaiting "continue" before proceeding to Stage 6.*
