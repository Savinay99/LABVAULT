# Database Design — LabVault

## Normalization (3NF)

The schema targets Third Normal Form:

1. **1NF**: Atomic columns, no repeating groups.
2. **2NF**: Non-key attributes depend on the whole primary key (single-column PKs on all tables).
3. **3NF**: Non-key attributes depend only on the key, no transitive dependencies.

`ResourceSubjects` resolves the many-to-many relationship between `Resources` and `Subjects`. `AuditLogs` records actions separately from business entities.

## Tables

| Table | Purpose | Key Constraints |
|-------|---------|-----------------|
| `Users` | Accounts & authentication | `UserId` PK, `Email` UNIQUE NOT NULL, `Role` CHECK |
| `Categories` | Resource categories | `CategoryId` PK, `Name` UNIQUE |
| `Subjects` | Academic subjects/courses | `SubjectId` PK, `SubjectCode` UNIQUE |
| `Resources` | File metadata | `ResourceId` PK, `StorageKey` UNIQUE, FK to Categories/Users |
| `ResourceSubjects` | Resource↔Subject mapping | Composite PK (ResourceId, SubjectId), FKs with cascade |
| `AuditLogs` | Security/administrative events | `AuditId` PK, FK to Users (nullable actor) |

## Referential Integrity

- `Resources.CategoryId` → `Categories.CategoryId` ON DELETE SET NULL
- `Resources.UploadedBy` → `Users.UserId` ON DELETE CASCADE
- `ResourceSubjects.ResourceId` → `Resources.ResourceId` ON DELETE CASCADE
- `ResourceSubjects.SubjectId` → `Subjects.SubjectId` ON DELETE CASCADE
- `AuditLogs.ActorUserId` → `Users.UserId` ON DELETE SET NULL

## Indexes

See `database/indexes.sql`. Indexes cover:
- `Resources(CreatedAt DESC)` — dashboard recency and pagination
- `Resources(UploadedBy)` — ownership queries
- `Resources(CategoryId)` — category filtering
- `Users(Email)` — authentication lookups (also UNIQUE)
- `AuditLogs(CreatedAt DESC)` — recent activity
- `ResourceSubjects(SubjectId)` — subject filtering

## Demonstrated Concepts

- **JOIN**: resource details joins Categories and Users; audit joins Users.
- **GROUP BY / aggregate**: `resource_counts_by_category` counts resources per category.
- **Filtering and sorting**: `list_resources` supports search, category, subject, sort, direction.
- **Primary and foreign keys**: defined on all tables.
- **Unique and check constraints**: email uniqueness, role/visibility checks, file size ≥ 0.
- **Transactions**: `db_transaction` context manager commits or rolls back.
- **Indexes**: created per query pattern.
- **Normalization / 3NF**: subject mapping in a separate junction table.

## Scripts

- `database/schema.sql` — create database and all tables.
- `database/indexes.sql` — create performance indexes.
- `database/seed.sql` — optional non-sensitive sample data (development only).