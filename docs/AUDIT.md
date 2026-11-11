# LabVault project audit

Audit date: 2026-11-09  
Scope: source review and local automated verification  
Status: no Azure or browser visual verification performed

For implementation scope, detailed results, and limitations, see [`LABVAULT_COMPLETION_REPORT.md`](../LABVAULT_COMPLETION_REPORT.md).

## Architecture

The active application is a Django 5.2 modular monolith (`core`, `accounts`, `resources`) with server-rendered templates and static CSS/JavaScript. `manage.py` is the primary entry point. SQLite is available for local demo/tests; SQL Server is supported through `mssql-django`. Local protected file storage is available, with Azure Blob Storage as an optional unverified backend.

The `app/` package is legacy Flask code. `nextjs-frontend/` and `express-backend/` are a separate, unintegrated prototype that uses an in-memory user store. The `Framer/` bundle is not required to run the Django app and is ignored by Git. These directories were preserved.

## Feature review

| Area | Verified implementation |
|---|---|
| Accounts | Email login/registration, roles, password reset/change, POST logout, login throttling, administrator manager setup |
| Resources | Upload validation, protected download, visibility/ownership checks, edit/delete, bookmark, search/filter/pagination, notifications |
| Equipment | Active/retired state, non-overlapping booking requests, admin approval/rejection, student cancellation of pending requests |
| Equipment custody | Admin issue and return workflow, due dates, overdue state, return condition |
| Maintenance | Authorized maintenance record creation and inventory state changes |
| Submissions | Student report upload and authorized review, grade, feedback, and notification |
| Audit/admin | Application audit events for key operations; operational records are read-only where appropriate in admin |
| Privacy/security | Dashboard/public activity privacy, safe redirect checks, POST-only mutations, input validation, production secret/cookie checks |

Consent capture, retention enforcement, account export/deletion, admin TOTP, tamper-proof audit storage, and live production operations are not implemented or verified.

## Verification

- `python -m pytest -q`: **109 passed**, with one upstream `defusedxml.cElementTree` deprecation warning.
- Django system check with `labvault_project.settings_test`: passed.
- `makemigrations --check --dry-run` with test settings: no changes detected.
- All Django migrations applied to isolated in-memory SQLite.
- `python -m pip check`: no broken requirements.
- Node syntax checks for the Express auth route, middleware, and JWT config passed.
- Production-mode Django deployment check ran with a throwaway key and returned the expected key-strength and optional HSTS preload advisories.

No real `.env` value was included in this audit. No Azure credential, account, or resource was used. No browser screenshots or responsive UI measurements were captured.

## Repository state

The starting tree already contained numerous modified and untracked files. Changes have been preserved; no reset or destructive cleanup was done. `.env`, databases, media, Node dependency/build output, and the large Framer prototype are excluded by ignore rules. The repository is on `master` with no remote configured. No push was performed. A checkpoint commit requires access to the read-only `.git` directory and is not included in this audit until that operation is authorized by the workspace permission layer.
