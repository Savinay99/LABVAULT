# Database Design  -  LabVault

**Document version:** 1.0
**Status:** Draft (database design only  -  no code changes in this phase)
**Standard:** ISO/IEC/IEEE 29148 (requirements traceability) / relational database design practice
**Project:** LabVault  -  secure academic laboratory resource and document management portal
**Repository:** `E:\labvault` (Django 5.2, mssql-django, Azure SQL Database)

---

## 1. Introduction

### 1.1 Purpose

This document defines the logical and physical database design for LabVault: every table with columns, data types, keys, constraints, and indexes; the Entity-Relationship diagram; the pagination and search strategy; and the migration approach. It is the third document in the LabVault documentation sequence, following `SRS.md` and `ARCHITECTURE.md`. It captures design only; no code is changed in this phase.

### 1.2 Scope

In scope: all tables in the decisions list (Users, Roles, Courses, Subjects, Categories, Resources, ResourceFiles, ResourceSubjects, Favorites, Notifications, AccessLog, AuditLog, LoginAttempts), their columns/types/keys/constraints/indexes, the Mermaid ER diagram, pagination strategy, full-text search strategy, and migration approach. Out of scope: stored procedures, triggers, partitioning, replication, and backup procedures (Azure platform handles backup).

---

## 2. Normalization Target (3NF)

1. **1NF**: Atomic column values; no repeating groups; each table has a primary key.
2. **2NF**: All non-key attributes depend on the whole primary key (single-column surrogate PKs on all tables).
3. **3NF**: No transitive dependencies  -  non-key attributes depend only on the key, the whole key, and nothing but the key.

`ResourceSubjects` resolves the many-to-many relationship between `Resources` and `Subjects`. `ResourceFiles` separates file/blob metadata (checksum, storage key, size) from resource descriptive metadata. `Roles`, `Courses` are separate dimension tables per the project decisions list (currently `role` is a field on `User`  -  see Section 9 honesty baseline).

---

## 3. Entity-Relationship Diagram (Mermaid)

```mermaid
erDiagram
    Users ||--o{ Resources : "uploads"
    Users ||--o{ Favorites : "favorites"
    Users ||--o{ Notifications : "receives"
    Users ||--o{ AccessLog : "downloads"
    Users ||--o{ AuditLog : "performs"
    Users }o--|| Roles : "has"
    Roles ||--o{ Users : "includes"
    Courses ||--o{ Subjects : "contains"
    Categories ||--o{ Resources : "classifies"
    Subjects ||--o{ ResourceSubjects : "covers"
    Resources ||--o{ ResourceSubjects : "tagged"
    Resources ||--o{ ResourceFiles : "has_file"
    Resources ||--o{ Favorites : "favorited"
    Resources ||--o{ AccessLog : "accessed"

    Users {
        int UserId PK
        string Email UK
        string PasswordHash
        string FirstName
        string LastName
        int RoleId FK
        bit IsActive
        datetime ConsentTimestamp
        string ConsentVersion
        datetime CreatedAt
        datetime UpdatedAt
    }
    Roles {
        int RoleId PK
        string Name UK
        string Description
    }
    Courses {
        int CourseId PK
        string CourseCode UK
        string CourseName
    }
    Subjects {
        int SubjectId PK
        string SubjectCode UK
        string SubjectName
        int CourseId FK
    }
    Categories {
        int CategoryId PK
        string Name UK
        string Description
    }
    Resources {
        int ResourceId PK
        string Title
        string Description NVARCHAR(MAX)
        int CategoryId FK
        int UploadedBy FK
        string Visibility
        datetime CreatedAt
        datetime UpdatedAt
    }
    ResourceFiles {
        int FileId PK
        int ResourceId FK UK1
        string StorageKey UK2
        string OriginalFileName
        string ContentType
        bigint FileSizeBytes
        string Sha256Checksum
        datetime UploadedAt
    }
    ResourceSubjects {
        int ResourceId FK
        int SubjectId FK
        pk (ResourceId, SubjectId)
    }
    Favorites {
        int FavoriteId PK
        int UserId FK
        int ResourceId FK
        datetime CreatedAt
        uq (UserId, ResourceId)
    }
    Notifications {
        int NotificationId PK
        int UserId FK
        string Title
        string Message
        bit IsRead
        datetime CreatedAt
    }
    AccessLog {
        int AccessId PK
        int UserId FK
        int ResourceId FK
        datetime AccessedAt
        string IpAddress
    }
    AuditLog {
        int AuditId PK
        int ActorUserId FK
        string Action
        string EntityType
        int EntityId
        datetime CreatedAt
    }
    LoginAttempts {
        int AttemptId PK
        string Email
        bit Success
        datetime AttemptedAt
    }
```

---

## 4. Tables, Columns, Types, Keys, Constraints

### 4.1 Users

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| UserId | INT | NO | PK | IDENTITY(1,1) |
| Email | NVARCHAR(254) | NO | UK | UNIQUE, normalized lowercased |
| PasswordHash | NVARCHAR(500) | NO | | Argon2 (planned); currently pbkdf2 via Django |
| FirstName | NVARCHAR(100) | NO | | |
| LastName | NVARCHAR(100) | NO | | |
| RoleId | INT | NO | FK | FK → Roles.RoleId, DEFAULT student role |
| IsActive | BIT | NO | | DEFAULT 1 |
| ConsentTimestamp | DATETIME2 | YES | | Recorded at signup (FR-12, planned) |
| ConsentVersion | NVARCHAR(50) | YES | | Versioned consent text (FR-12, planned) |
| CreatedAt | DATETIME2 | NO | | DEFAULT SYSDATETIME() |
| UpdatedAt | DATETIME2 | NO | | DEFAULT SYSDATETIME() |

**Constraints:** `CHECK` on role via Roles table FK; email uniqueness enforced by UK + application pre-check returning generic message (FR-03).
**Indexes:** `IX_Users_Email` (auth lookups), `IX_Users_Role` (admin dashboard filtering).

> **Honesty baseline:** Current `accounts` migration (`0001_initial.py`) uses `role` as a `CharField` on `User` (no separate `Roles` table), no `ConsentTimestamp`/`ConsentVersion`. Django `AbstractUser` provides `username`, `password`, `first_name`, `last_name`, `email`, `is_active`, `date_joined`. Table `db_table = "Users"`.

### 4.2 Roles

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| RoleId | INT | NO | PK | IDENTITY(1,1) |
| Name | NVARCHAR(20) | NO | UK | 'student' | 'administrator' |
| Description | NVARCHAR(200) | YES | | |

**Status:** Planned per decisions list; not in current migrations.

### 4.3 Courses

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| CourseId | INT | NO | PK | IDENTITY(1,1) |
| CourseCode | NVARCHAR(20) | NO | UK | e.g. 'CS101' |
| CourseName | NVARCHAR(200) | NO | | |

**Status:** Planned per decisions list; not in current migrations.

### 4.4 Subjects

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| SubjectId | INT | NO | PK | IDENTITY(1,1) |
| SubjectCode | NVARCHAR(20) | NO | UK | e.g. 'CS101' |
| SubjectName | NVARCHAR(100) | NO | | |
| CourseId | INT | YES | FK | FK → Courses.CourseId (optional course grouping) |

**Current:** `Subjects` exists with `SubjectCode`, `SubjectName`; no `CourseId`. `db_table = "Subjects"`.

### 4.5 Categories

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| CategoryId | INT | NO | PK | IDENTITY(1,1) |
| Name | NVARCHAR(100) | NO | UK | |
| Description | NVARCHAR(500) | YES | | |

**Current:** exists. `db_table = "Categories"`.

### 4.6 Resources

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| ResourceId | INT | NO | PK | IDENTITY(1,1) |
| Title | NVARCHAR(200) | NO | | |
| Description | NVARCHAR(2000) | YES | | |
| CategoryId | INT | YES | FK | FK → Categories.CategoryId ON DELETE SET NULL |
| UploadedBy | INT | NO | FK | FK → Users.UserId ON DELETE CASCADE |
| Visibility | NVARCHAR(20) | NO | | DEFAULT 'private', CHECK ('private','public') |
| CreatedAt | DATETIME2 | NO | | DEFAULT SYSDATETIME() |
| UpdatedAt | DATETIME2 | NO | | DEFAULT SYSDATETIME() |

**Current:** exists, plus `storage_key`, `original_filename`, `content_type`, `file_size_bytes` (file metadata inlined  -  will move to `ResourceFiles` per FR-17). `db_table = "Resources"`.
**Indexes:** `IX_Resources_CreatedAt`, `IX_Resources_UploadedBy`, `IX_Resources_Category`, `IX_Resources_Visibility`, `IX_Resources_Title`, `IX_ResUpBy_CreatedAt`.

### 4.7 ResourceFiles

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| FileId | INT | NO | PK | IDENTITY(1,1) |
| ResourceId | INT | NO | UK1 | FK → Resources.ResourceId ON DELETE CASCADE (one file per resource) |
| StorageKey | NVARCHAR(200) | NO | UK2 | UNIQUE, server-generated unpredictable key |
| OriginalFileName | NVARCHAR(260) | NO | | |
| ContentType | NVARCHAR(100) | NO | | MIME from magic-byte validation |
| FileSizeBytes | BIGINT | NO | | CHECK (>= 0) |
| Sha256Checksum | NVARCHAR(64) | NO | | SHA-256 hex digest (FR-17) |
| UploadedAt | DATETIME2 | NO | | DEFAULT SYSDATETIME() |

**Status:** Implemented (FR-17); file metadata split from `Resource` into `ResourceFiles`; migration `0003_add_resource_files.py`; SHA-256 checksum stored per upload.

### 4.8 ResourceSubjects

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| ResourceId | INT | NO | PK, FK | FK → Resources.ResourceId ON DELETE CASCADE |
| SubjectId | INT | NO | PK, FK | FK → Subjects.SubjectId ON DELETE CASCADE |

**Current:** exists as junction table with Django `id` surrogate PK + `UniqueConstraint(resource, subject)`; `db_table = "ResourceSubjects"`. Mermaid shows composite PK; physical Django migration uses surrogate `id` + unique constraint  -  both enforce the same business rule.

**Indexes:** `IX_ResourceSubjects_SubjectId`, `IX_ResourceSubjects_ResourceId`.

### 4.9 Favorites

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| FavoriteId | INT | NO | PK | IDENTITY(1,1) |
| UserId | INT | NO | FK | FK → Users.UserId ON DELETE CASCADE |
| ResourceId | INT | NO | FK | FK → Resources.ResourceId ON DELETE CASCADE |
| CreatedAt | DATETIME2 | NO | | DEFAULT SYSDATETIME() |

**Constraint:** `UNIQUE(UserId, ResourceId)`  -  one favorite per user per resource.
**Status:** Planned (FR-30); table not in current models.

### 4.10 Notifications

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| NotificationId | INT | NO | PK | IDENTITY(1,1) |
| UserId | INT | NO | FK | FK → Users.UserId ON DELETE CASCADE |
| Title | NVARCHAR(200) | NO | | |
| Message | NVARCHAR(1000) | NO | | |
| IsRead | BIT | NO | | DEFAULT 0 |
| CreatedAt | DATETIME2 | NO | | DEFAULT SYSDATETIME() |

**Status:** Implemented (FR-31, FR-32); migration `0004_notification.py`; views, templates, and unread-count context processor.

### 4.11 AccessLog

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| AccessId | INT | NO | PK | IDENTITY(1,1) |
| UserId | INT | NO | FK | FK → Users.UserId |
| ResourceId | INT | NO | FK | FK → Resources.ResourceId |
| AccessedAt | DATETIME2 | NO | | DEFAULT SYSDATETIME() |
| IpAddress | NVARCHAR(45) | YES | | IPv4/IPv6 storage |

**Status:** Implemented (FR-24, FR-35); migration `0002_add_access_log.py`; download view writes an `AccessLog` entry per authorized download.

### 4.12 AuditLog

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| AuditId | INT | NO | PK | IDENTITY(1,1) |
| ActorUserId | INT | YES | FK | FK → Users.UserId ON DELETE SET NULL |
| Action | NVARCHAR(100) | NO | | |
| EntityType | NVARCHAR(50) | NO | | |
| EntityId | INT | NO | | |
| CreatedAt | DATETIME2 | NO | | DEFAULT SYSDATETIME() |

**Current:** exists. `db_table = "AuditLogs"`.
**Indexes:** `IX_AuditLogs_CreatedAt`, `IX_AuditLogs_Actor`.

### 4.13 LoginAttempts

| Column | Type | Null | Key | Constraint / Default |
|--------|------|------|-----|----------------------|
| AttemptId | INT | NO | PK | IDENTITY(1,1) |
| Email | NVARCHAR(254) | NO | | Normalized email, no password |
| Success | BIT | NO | | 1 = success, 0 = failure |
| AttemptedAt | DATETIME2 | NO | | DEFAULT SYSDATETIME() |

**Status:** Planned (FR-06, FR-07 via django-axes); table not in current models.

---

## 5. Referential Integrity Summary

| FK | Source | Target | On Delete |
|----|--------|--------|-----------|
| Users.RoleId | Users | Roles | RESTRICT (protect role definitions) |
| Subjects.CourseId | Subjects | Courses | SET NULL |
| Resources.CategoryId | Resources | Categories | SET NULL |
| Resources.UploadedBy | Resources | Users | CASCADE |
| ResourceFiles.ResourceId | ResourceFiles | Resources | CASCADE |
| ResourceSubjects.ResourceId | ResourceSubjects | Resources | CASCADE |
| ResourceSubjects.SubjectId | ResourceSubjects | Subjects | CASCADE |
| Favorites.UserId | Favorites | Users | CASCADE |
| Favorites.ResourceId | Favorites | Resources | CASCADE |
| Notifications.UserId | Notifications | Users | CASCADE |
| AccessLog.UserId | AccessLog | Users | NO ACTION (retain history) |
| AccessLog.ResourceId | AccessLog | Resources | NO ACTION (retain history) |
| AuditLog.ActorUserId | AuditLog | Users | SET NULL |

---

## 6. Indexes

| Index | Table | Columns | Purpose |
|-------|-------|---------|---------|
| IX_Users_Email | Users | Email | Authentication lookups (FR-01, FR-05) |
| IX_Users_Role | Users | Role | Admin dashboard role filtering |
| IX_Resources_CreatedAt | Resources | CreatedAt DESC | Pagination recency sort (NFR-10) |
| IX_Resources_UploadedBy | Resources | UploadedBy | Ownership queries (FR-28) |
| IX_Resources_Category | Resources | CategoryId | Category filtering (FR-27) |
| IX_Resources_Visibility | Resources | Visibility | Public/private filtering (FR-28) |
| IX_Resources_Title | Resources | Title | Search support (FR-26) |
| IX_ResUpBy_CreatedAt | Resources | UploadedBy, CreatedAt DESC | User's own resources sorted |
| IX_ResourceSubjects_SubjectId | ResourceSubjects | SubjectId | Subject filtering |
| IX_ResourceSubjects_ResourceId | ResourceSubjects | ResourceId | Resource subject lookup |
| IX_AuditLogs_CreatedAt | AuditLog | CreatedAt DESC | Recent activity (FR-34) |
| IX_AuditLogs_Actor | AuditLog | ActorUserId | Per-actor audit queries |
| PK ResourceSubjects | ResourceSubjects | (ResourceId, SubjectId) | Junction uniqueness |
| UQ Favorites | Favorites | (UserId, ResourceId) | One favorite per user/resource |

> **Note:** `Users.Email` and `Resources.StorageKey` uniqueness is enforced by column UNIQUE constraints (which SQL Server indexes automatically). `ResourceFiles.ResourceId` UK enforces one file per resource.

---

## 7. Pagination and Search Strategy

### 7.1 Pagination

- Library listing (FR-25) uses `OFFSET ... FETCH NEXT` (SQL Server equivalent of LIMIT/OFFSET), ordered by `CreatedAt DESC`.
- Default page size = 20, configurable.
- Covering index `IX_Resources_CreatedAt` supports the sort without a full-table scan.
- Keyset pagination ("seek method", `WHERE CreatedAt < @last_seen ORDER BY CreatedAt DESC OFFSET 0 FETCH NEXT @page_size`) is the preferred upgrade path for deep pages; OFFSET/FETCH is acceptable for the expected academic-portal volume.
- Ownership-filtered listing (student sees public + own resources) uses `IX_ResUpBy_CreatedAt` to avoid scanning all resources.

### 7.2 Search

- Full-text search (FR-26) on `Resources.Title` and `Resources.Description`.
- Initial implementation: `WHERE Title LIKE '%' + @term + '%' OR Description LIKE '%' + @term + '%'`, parameterized via Django ORM (`__icontains`), combined with visibility/ownership filters.
- `IX_Resources_Title` and `IX_Resources_Category` support filtered search; leading-wildcard `LIKE` cannot use b-tree indexes efficiently, so performance is bounded by page size (NFR-10) and result set is limited before ranking/display.
- Upgrade path (documented, not in scope): SQL Server Full-Text Search (`CONTAINS`/`FREETEXT`) with a full-text index on `Title, Description` if relevance ranking or scale demands it.
- No third-party search service (Elasticsearch/Algolia)  -  stays within "no external dependencies beyond Azure" constraint.

---

## 8. Migration Approach

### 8.1 Primary mechanism: Django migrations (`mssql-django`)

- Migrations live in `accounts/migrations/` and `resources/migrations/`.
- `0001_initial.py` in each app creates `Users`, `Categories`, `Subjects`, `Resources`, `ResourceSubjects`, `AuditLog` plus all indexes and the `unique_resource_subject` constraint.
- `mssql-django` maps Django fields to SQL Server types (`BigAutoField` → `INT IDENTITY`, `DateTimeField` → `DATETIME2`, etc.).
- `makemigrations` / `migrate` workflow managed via `manage.py`; never auto-drop/truncate production data.
- SQLite (`settings_test.py`) is used only for tests; schema parity is not guaranteed between SQLite and SQL Server (test against SQL Server where behavior differs).

### 8.2 Bare SQL scripts (reference / initial deploy)

- `database/schema.sql`  -  creates the `LabVault` database (IF NOT EXISTS) and all core tables in 3NF with FKs, CHECK constraints, UNIQUE constraints. Intended for initial deploy against an empty target database.
- `database/indexes.sql`  -  creates performance indexes matched to query patterns.
- `database/seed.sql`  -  non-sensitive sample categories/subjects (development only).

### 8.3 Planned migrations (not yet created)

| Planned table | Requirement | Migration needed |
|---------------|-------------|------------------|
|| Roles | Planned | Decisions list; `Users.role` CharField replaces separate table ||
|| Courses | Planned | Decisions list; `Subjects` has no `CourseId` yet ||
|| ResourceFiles | Implemented | `resources/migrations/0003_add_resource_files.py` ||
|| LoginAttempts | Planned | django-axes manages its own table if used ||
|| AccessLog | Implemented | `resources/migrations/0002_add_access_log.py` ||
|| Favorites | Planned | FR-30; not in migrations ||
|| Notifications | Implemented | `resources/migrations/0004_notification.py` ||

### 8.4 Migration rules

- Never auto drop/truncate an existing database (schema.sql header rule).
- Additive changes only in production (new tables/columns); destructive changes require explicit review.
- Test migrations against SQL Server (not SQLite) before production deploy.
- Keep `settings_test.py` SQLite for fast unit tests; integration tests target a real SQL Server instance where available.

---

## 9. Honesty Baseline: Implemented vs. Planned Tables

| Table | Status | Evidence |
|-------|--------|----------|
| Users | Implemented | `accounts/migrations/0001_initial.py`, `db_table="Users"` (role is CharField, no Roles table yet) |
| Categories | Implemented | `resources/migrations/0001_initial.py` |
| Subjects | Implemented | `resources/migrations/0001_initial.py` (no CourseId yet) |
| Resources | Implemented | `resources/migrations/0001_initial.py` (file metadata inlined; no ResourceFiles split yet) |
| ResourceSubjects | Implemented | `resources/migrations/0001_initial.py` (surrogate `id` + unique constraint) |
| AuditLog | Implemented | `resources/migrations/0001_initial.py` |
|| Roles | Planned | Decisions list; not in migrations ||
|| Courses | Planned | Decisions list; not in migrations ||
|| ResourceFiles | Implemented | `resources/migrations/0003_add_resource_files.py`, `db_table="ResourceFiles"` ||
|| LoginAttempts | Planned | FR-06/FR-07 (django-axes); not in migrations ||
|| AccessLog | Implemented | `resources/migrations/0002_add_access_log.py`, `db_table="AccessLog"` ||
|| Favorites | Planned | FR-30; not in migrations ||
|| Notifications | Implemented | `resources/migrations/0004_notification.py`, `db_table="Notifications"` ||

---

## 10. Cross-References

- `SRS.md`  -  FR-13 through FR-41 (resource, audit, access, data-ethics requirements) realized in this schema.
- `ARCHITECTURE.md`  -  ADR-02 (mssql-django), ADR-04 (unpredictable storage keys), module boundary between Django ORM and raw SQL.
- `SECURITY_AND_PRIVACY.md`  -  data inventory, retention, and access-control rules applied to these tables.

---

*End of DATABASE.md  -  Stage 3 complete. Awaiting "continue" before proceeding to Stage 4 (SECURITY_AND_PRIVACY.md).*
