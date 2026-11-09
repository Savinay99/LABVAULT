# LabVault

LabVault is a Django web application for academic laboratory resources and equipment. It provides student and administrator accounts, a searchable resource library with protected file uploads, laboratory equipment inventory, instrument bookings and maintenance records, and student report submissions with review workflows.

## Current architecture

- **Application:** Django 5.2 modular monolith (`core`, `accounts`, and `resources` apps).
- **UI:** Django templates with HTML, CSS, and vanilla JavaScript in `templates/` and `static/`.
- **Database:** Django ORM. SQL Server is supported through `mssql-django` and `pyodbc`; SQLite is available for local demonstrations and is used by the automated test settings.
- **Files:** Local storage for development or Azure Blob Storage when explicitly configured. Azure connectivity has not been verified from this repository environment.
- **Authentication:** Django sessions, a custom email-based user model, student/administrator roles, password reset, and Django's built-in `createsuperuser` command.
- **Entrypoints:** `manage.py`, `run.ps1`, and `run.bat`. The root `run.py` is a Django compatibility entrypoint.

`nextjs-frontend/` and `express-backend/` are a separate, currently unintegrated prototype; they are not needed to run the Django application. The old `app/` Flask package is legacy code and is not part of the active web application. The archived `_backup_*` directories and `Framer/` prototype are also not needed at runtime.

## Requirements

- Python 3.11 or later
- For SQL Server: Microsoft ODBC Driver 18 for SQL Server and a reachable SQL Server/Azure SQL database
- For Azure file storage: Azure Blob Storage configuration (optional)

## Local setup

From PowerShell in the project root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

The sample `.env` is for local development only and selects SQLite. Before starting, generate and set a unique local secret key:

```powershell
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Copy the generated value into `DJANGO_SECRET_KEY` in `.env`. Keep `.env` private; it is ignored by Git. Then apply migrations and start the server:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The `createsuperuser` command prompts for credentials; no demo account is created or printed by the launchers. Its account receives the LabVault administrator role.

You can use `./run.ps1` or `run.bat` after installing dependencies and configuring `.env`. To reset an administrator password, use `python manage.py changepassword <email>`.

## Configuration

See `.env.example` for the supported variables. Important settings:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Required outside debug mode; generate a unique value and keep it private. |
| `DJANGO_DEBUG` | Defaults to `False`; enable only for local development. |
| `ALLOWED_HOSTS` | Comma-separated hostnames accepted by Django. |
| `DB_ENGINE` | `sqlite` for a local demo or `mssql` for SQL Server/Azure SQL. |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | SQL Server connection details when using `mssql`. |
| `DB_DRIVER`, `DB_ENCRYPT`, `DB_TRUSTED_CONNECTION` | ODBC driver and connection security options. Encryption defaults to enabled. |
| `MEDIA_ROOT` | Local protected file location. Keep it outside a public static directory. |
| `AZURE_STORAGE_CONNECTION_STRING`, `AZURE_STORAGE_CONTAINER_NAME` | Optional Azure Blob Storage backend settings. |
| `SESSION_COOKIE_SECURE` | Defaults to enabled when debug is off; requires HTTPS in production. |
| `LOGIN_MAX_FAILED_ATTEMPTS`, `LOGIN_LOCKOUT_SECONDS` | Failed login threshold and lockout window (defaults: 5 attempts, 900 seconds). |

Production deployments must set `DJANGO_DEBUG=False`, a unique `DJANGO_SECRET_KEY`, correct `ALLOWED_HOSTS`, and HTTPS cookie settings. The application rejects a missing production secret key. Do not put credentials in source files or commit `.env`.

## Azure SQL and DP-900 mapping

The application is prepared to use SQL Server through Django's ORM and the `mssql-django` backend. Configure the ODBC Driver 18 connection variables above to point to Azure SQL Database; the application and migration setup does not prove that a live Azure database is reachable. This repository has not been connected to an Azure subscription or deployed.

The project demonstrates DP-900 concepts through relational tables, primary/foreign keys, unique and check constraints, normalized resource/subject relationships, ORM CRUD operations, indexes for common queries, and the separation of a relational database workload from object/file storage. Azure SQL Database is the intended managed relational service. Azure Blob Storage is optional for file objects; it is not required to demonstrate relational database concepts. Azure resource provisioning, identity integration, and live connectivity should be configured and verified by the project owner separately.

Schema and architecture references: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/DATABASE.md](docs/DATABASE.md), [docs/DP900_MAPPING.md](docs/DP900_MAPPING.md), and [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md). Some requirements in those documents remain planned; the completion report records verified status.

## Main workflows

- Register, sign in, reset a password, and manage a profile.
- Browse, search, upload, edit, bookmark, download, and delete resources subject to ownership/visibility permissions.
- Browse laboratory instruments, reserve available time slots, and review maintenance records.
- Submit laboratory reports and allow the resource owner or administrator to review submissions.
- Manage users through Django Admin and export available audit/equipment reports.

## Tests and checks

The test settings use an isolated SQLite database (`db_test.sqlite3`), so tests do not connect to SQL Server or Azure SQL:

```powershell
python manage.py check --settings=labvault_project.settings_test
python manage.py makemigrations --check --dry-run --settings=labvault_project.settings_test
python -m pytest -q
```

To run only authentication and route checks:

```powershell
python -m pytest tests/test_account_setup.py tests/test_auth_flow.py tests/test_routes.py -q
```

## Project layout

```text
accounts/             Custom user model, authentication, account views
core/                 Landing page and dashboards
resources/            Resources, equipment, bookings, submissions, storage
labvault_project/     Django settings, URL configuration, WSGI/ASGI
templates/            Server-rendered pages and email templates
static/               CSS and JavaScript
database/             SQL schema and design reference scripts
docs/                 Requirements, architecture, security, and academic mapping
tests/                Django and legacy service tests
```

## Academic submission checklist

The repository includes requirements, architecture, database, security, DP-900, test-plan, and traceability documents. Before submission, confirm the institution's required format, add any requested ER/architecture diagrams or screenshots, demonstrate the main student and administrator workflows, and include the current test output. Do not claim a live Azure deployment unless it has been independently connected and verified.
