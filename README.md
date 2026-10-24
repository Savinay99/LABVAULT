# LabVault

LabVault is a secure academic laboratory resource and document management portal. It helps students organize, upload, manage, search, and access academic laboratory resources — lab manuals, experiment documents, practical notes, source code files, project documents, and academic reference materials.

## Technology Stack

- **Frontend:** HTML5, CSS3, Vanilla JavaScript (no frameworks)
- **Backend:** Python Flask (modular monolith)
- **Database:** Microsoft SQL Server / Azure SQL Database via pyodbc
- **Password hashing:** Werkzeug (pbkdf2:sha256)
- **CSRF protection:** Flask-WTF
- **Testing:** pytest, Flask test client

## Project Structure

```
LabVault/
  app/
    __init__.py          Application factory + error handlers + security headers
    config.py            Environment-based configuration
    extensions.py        Flask extensions (CSRF)
    routes/
      auth.py            Registration, login, logout
      dashboard.py       Landing page, dashboard
      resources.py       Library, upload, details, edit, delete, download
      profile.py         Profile, password change
      admin.py           Administration (user management, resource moderation, audit)
    services/
      auth_service.py    Registration, login, password change, sessions
      resource_service.py Resource business logic + authorization
      storage_service.py Local + Azure Blob storage abstraction
    repositories/
      db.py              pyodbc connection management + transactions
      user_repository.py User CRUD
      resource_repository.py Resource CRUD, search, pagination, subjects
      audit_repository.py Audit log
    security/
      validation.py      Input validation and output escaping
      permissions.py     Role-based access control
    templates/           Jinja2 templates (all pages)
    static/
      css/style.css      Application stylesheet
  database/
    schema.sql           Normalized (3NF) schema
    indexes.sql          Query-pattern indexes
    seed.sql             Optional sample data
  tests/                 pytest suite (40 tests)
  docs/                  Architecture, database design, security, testing
  .env.example           Configuration placeholders
  .gitignore
  requirements.txt
  run.py                 Application entry point
  README.md
```

## Features

- User registration and login with secure password hashing
- Server-side validation on all inputs
- Role-based access control (student, administrator)
- Resource upload, download, edit, delete with ownership enforcement
- Search, filtering (category/subject), sorting, pagination
- File type and size validation; unpredictable storage keys
- Protected local storage outside the application directory
- Audit logging for administrative actions
- Security headers (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy)
- CSRF protection on all state-changing forms
- Login rate-limiting guidance
- Responsive, accessible UI

## Prerequisites

- Python 3.11+
- Microsoft ODBC Driver 17 for SQL Server (for Azure SQL / SQL Server)
- A Microsoft SQL Server or Azure SQL Database instance

## Local Development

### 1. Clone / create the project

```powershell
cd E:\tryis
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment

Copy `.env.example` to `.env` and fill in values. **Never commit `.env`** — it is gitignored.

```powershell
copy .env.example .env
# Edit .env with a text editor and set your database connection details
```

### 5. Initialize the database

Run `database/schema.sql` against your SQL Server / Azure SQL Database, then optionally `database/indexes.sql` and `database/seed.sql`.

```powershell
sqlcmd -S your-server.database.windows.net -U labvault_admin -P your-password -d LabVault -i database\schema.sql
sqlcmd -S your-server.database.windows.net -U labvault_admin -P your-password -d LabVault -i database\indexes.sql
```

### 6. Run the application

```powershell
$env:FLASK_ENV="development"
python run.py
```

Open http://127.0.0.1:5000 in your browser.

### Bootstrap the First Administrator

There are no hardcoded administrator credentials. To create the first administrator:

1. Register a normal account through the UI.
2. Connect to the database and update the role:

```sql
UPDATE Users SET Role = 'administrator' WHERE Email = 'your-email@example.edu';
```

## Verified functionality

The following have been exercised and pass without any external credentials:

- User registration, login, logout, and password change
- Resource upload, details, edit, delete, download
- Library search/filter/sort/pagination and subject/category management
- Admin user management, resource moderation, and audit log
- Access control (ownership, visibility, admin bypass)
- CSRF protection on all state-changing forms
- Security headers (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, HSTS)
- File extension, size, and magic-byte signature validation
- Open-redirect protection on login `next` parameter
- Login rate limiting / lockout (5 failures → 900s lockout)

Run the suite:

```powershell
python -m pytest tests/
```

## External services required for production (not verified in this environment)

These require real credentials and are NOT exercised by the test suite:

| Integration | Configured via | Notes |
|-------------|---------------|-------|
| SQL Server / Azure SQL Database | `DB_SERVER`, `DB_DATABASE`, `DB_USERNAME`, `DB_PASSWORD` (or `DB_TRUSTED_CONNECTION=yes`) | Required for all data persistence. Install Microsoft ODBC Driver 17 for SQL Server. |
| Azure Blob Storage (optional) | `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER_NAME` | Falls back to local protected storage under `STORAGE_PATH` when unset. Requires `azure-storage-blob` package. |
| SMTP / email verification | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` | Documented only — email verification and password reset are not implemented. |

Do not create paid cloud resources to test this project. Local development runs entirely on local storage and a configured SQL Server instance.

## Azure SQL schema deployment

Deploy `database/schema.sql` first against an empty target database. It creates the `LabVault` database if missing, then all tables (Users, Categories, Subjects, Resources, ResourceSubjects, AuditLogs) in 3NF with parameterized queries enforced by the repository layer. Then run `database/indexes.sql` for query-pattern indexes, and optionally `database/seed.sql` for sample data. Never drop/truncate an existing database automatically.

## Azure Blob Storage configuration (optional production override)

Set `AZURE_STORAGE_CONNECTION_STRING` and `AZURE_STORAGE_CONTAINER_NAME` (default `labvault`). The container is kept private and downloads are served via short-lived SAS URLs. Install the `azure-storage-blob` package. When unset, `LocalProtectedStorage` is used and files are stored under `STORAGE_PATH` (default `storage/`).

## Security

- Passwords are hashed with Werkzeug (pbkdf2:sha256). Never plaintext.
- Sessions use HttpOnly, SameSite cookies; Secure in HTTPS deployments.
- CSRF tokens on all state-changing forms.
- All SQL queries are parameterized (no concatenation).
- Files stored outside the application directory; downloads enforce authorization.
- Content Security Policy restricts scripts/styles to same-origin.
- No secrets in source code or frontend JavaScript.
- Login rate limiting: 5 failed attempts → 900-second lockout window (per email, including unknown accounts to prevent enumeration).

## Limitations

- File content scanning is limited to magic-byte signature validation; it is not comprehensive malware scanning.
- Email verification and password reset are not implemented (SMTP not configured).
- Login lockout state is in-memory and not shared across processes/workers; for multi-worker production deployment, back it with Redis or a database table.

## License

Internal academic project.