# LabVault Final Quality Assurance Report

Date: 2026-11-09  
Project: `E:\labvault`  
Application: Django 5.2 modular monolith

## QA result

The requested final QA was completed against the active Django application using its automated suite and an isolated local QA database. The suite passes. Browser testing exercised the principal student and administrator booking, equipment, maintenance, submission, grading, and resource management flows. QA found and fixed a stale grade display and responsive tablet/mobile layout and navigation issues.

This report does not certify a production deployment. Azure was not provisioned or deployed, and no live Azure service was accessed.

## Exact automated results

| Command / check | Result |
|---|---|
| `.venv\\Scripts\\python.exe -m pytest -q` | **115 passed**, 1 warning, 10.45s. Warning: third-party `openid` imports deprecated `defusedxml.cElementTree`. |
| `manage.py check --settings=labvault_project.settings_test` | Passed: no issues (0 silenced). |
| `manage.py makemigrations --check --dry-run --settings=labvault_project.settings_test` | Passed: no changes detected. |
| `manage.py migrate --check --settings=labvault_project.settings_test` | Passed: no unapplied migrations. |
| `python -m pip check` | Passed: no broken requirements. |

All automated checks used the test configuration. Browser workflow data was written only to `scratch/qa_20261109.sqlite3`, a disposable isolated SQLite database; no configured/local application database or Azure database was used. The test suite includes coverage of authentication and role restrictions, booking approval/rejection/cancellation, issue and return, overdue tracking, maintenance permissions and records, resource operations, report review/grading, audit logging, and request method/CSRF protections.

## Features and workflows verified

- Authentication: administrator and student logged in through the browser. Unauthorized student access to `/admin-dashboard/` returned HTTP 403. The automated suite covers registration, login safeguards, role permissions, and account flows.
- Student workflow: browsed instruments, requested equipment, saw pending status, and cancelled a pending booking. A second request was later rejected by an administrator.
- Administrator workflow: reviewed and approved a request, issued the instrument with a due date, recorded its return condition, and completed the return. The UI reflected the instrument returning to available. The overdue issue fixture appeared in the administrator queue with overdue indication and return controls.
- Maintenance: recorded a failed inspection (instrument moved to under maintenance), then a passing calibration (instrument returned to available); both records were visible in maintenance history. Added a maintenance history entry point to each instrument card.
- Submissions and grading: submitted a report file as a student; reviewed it in the administrator submissions hub; entered grade 92.5 and feedback. Fixed student dashboard and resource detail templates so reviewed status, grade, reviewer, and feedback display from the current model fields.
- Resource management: uploaded a resource through the browser, opened it in the library, and updated its title and description. Resource deletion behavior is covered by the automated regression suite; deletion was not invoked in the browser session.
- QA database evidence after workflows: booking states included cancelled, rejected, completed, and issued; two maintenance records, one reviewed submission with grade 92.5, and 14 audit records were present.
- Navigation and footer: desktop dashboard and page navigation were visually reviewed. Instrument cards now link to maintenance history. No evidence was collected for every footer destination or every secondary page link.

## Browser and responsive verification

The application was actually launched locally at `http://127.0.0.1:8010` using test settings and the isolated QA database. Browser testing was performed at desktop (1440×900), tablet (768×1024), and mobile (390×844).

At all three sizes, the administrator dashboard had no document-level horizontal overflow. At mobile width, the dashboard, instruments, maintenance, submissions, resource library, and administrator dashboard pages measured 375 CSS pixels of document width within a 390-pixel viewport. At tablet width, the dashboard measured 753 pixels within a 768-pixel viewport. The mobile navigation toggle opened and closed, and changing the tablet sidebar to normal document flow fixed the previous control obstruction. Tables retain their own horizontal scrolling where their columns require it.

Browser workflows verified login, catalog browsing, booking creation/cancellation, administrator approval/rejection, issue and return, maintenance entry, report submission/review/grading, and resource upload/edit. The registration form, every modal/error state, every secondary link/button, file download behavior, and every page at each viewport were not exhaustively browser-tested. Automated tests cover the relevant backend protections; this is not a claim of exhaustive visual or accessibility certification. The cinematic intro/loader can reappear during navigation and must be dismissed to interact; this remains a usability issue. A request for `/favicon.ico` was observed returning 404.

## Security and configuration checks

- Automated tests passed for access control and security-sensitive workflows. Student access to the administrator dashboard was denied in the browser (403).
- Browser form POSTs succeeded with the application's CSRF flow; automated checks cover protected POST operations. Authentication protections and validation are represented in the test suite.
- The QA run used test settings and synthetic accounts/files only. No secrets were added to the project as part of QA.
- Production hardening still requires environment-specific validation of `SECRET_KEY`, allowed hosts, HTTPS, secure cookies, database credentials/networking, storage permissions, backups, and operational monitoring. Application audit records are not tamper-proof or a substitute for institutional retention controls.

## Database and migrations

The test configuration and isolated QA SQLite database were migrated for the QA run. `migrate --check` found no unapplied migrations and `makemigrations --check --dry-run` found no model/migration drift. No production or Azure database was touched. QA fixtures are disposable and are not production data.

## Remaining issues

- The cinematic intro/loader returns on route navigation and requires dismissal; consider making it one-time or respecting a persisted dismissal preference.
- `/favicon.ico` returned 404 during the local browser run.
- The browser pass was representative, not exhaustive: registration, every control/error state, all footer destinations, and real file download integrity were not visually exercised.
- Azure services, institutional SMTP, production secrets/hostnames, production database/storage configuration, and operational controls remain unverified.
- Legacy Flask, Next.js, and Express prototypes remain in the repository and are not the active Django application.

## Azure implementation steps pending

No Azure resources were provisioned or deployed, per instruction. When authorized to implement Azure, the remaining work is:

1. Select the target subscription, region, resource naming, and supported SQL Server/Azure SQL topology; provision a non-production database and network access restricted to the application.
2. Configure the Django SQL Server backend and required ODBC driver in the target runtime; provide credentials through managed identity where supported or a secret store, never source control. Set production `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, HTTPS, and secure cookie settings.
3. Create a private Azure Blob container and configure the Django storage backend, identity/role assignment, allowed file limits/types, and private download access. Keep local storage available for local development.
4. Deploy to a non-production app environment, apply Django migrations there, and verify login/roles, SQL connectivity, resource upload/download, hashes, booking and return transactions, maintenance, grading, and audit records.
5. Configure TLS/custom hostname, monitoring and alerting, database/blob backup and retention, restore checks, and operational access policies; run deployment checks and a complete smoke test before considering production.

## Academic submission readiness

**Ready for a local academic demonstration of the verified workflows, with stated limitations.** The automated suite passes and the core browser workflows work at tested viewports. Do not describe this as 100% complete, production-ready, or Azure-ready. Before a formal submission, compare the project against the institution's rubric and demonstrate the remaining registration and secondary-page flows; resolve the loader and favicon issues if the rubric expects a polished release.

## Supplemental PDF and dashboard verification — 2026-11-09

- Replaced the old fixed-position, truncating PDF generation with a flowing ReportLab Platypus layout in `resources/manual_pdf.py`. Source-provided sections wrap across pages; long tables continue with repeated column headers. Optional sections are omitted when the experiment record has no data, avoiding invented observations or conclusions.
- Updated six existing PDF manuals in place. Their resource IDs and the total resource count (22) remained unchanged. Each manual rendered to one letter-size page with no clipped content in visual review. The six originals were backed up in ignored `scratch/` review storage before replacement.
- A synthetic QA-only eight-page manual was generated and raster-reviewed. Long prose flowed across pages, the three-column observation table continued onto the next page with a repeated header, and calculations/results/viva/conclusion appeared without overlapping the footer. This sample exists only under ignored `scratch/pdf-review/` and is not a resource record.
- Reworked “Recently Added Resources” into responsive cards with title/detail links, category/contributor/date, visibility, and a “View all” library link. Permission-filtered source query and resource access rules were left intact. The dashboard route regression test verifies the card and destination links.
- Browser session opened the running application and reached the sign-in page; an authenticated browser session was unavailable in this pass, so the updated card layout was not visually checked in-browser at desktop/tablet/mobile. Previous general dashboard viewport measurements above are from the prior QA run and do not constitute viewport-specific verification of these new cards.
- New tests: PDF pagination without truncation, optional observation table rendering, and dashboard card/link rendering. Full suite: **112 passed**, one existing third-party deprecation warning. Django system check passed; migration drift check found no changes; dependency check passed. No Azure resources were provisioned.

## Role-separated dashboards — 2026-11-09

- Before this change, the persisted user model had only Student and Administrator roles, `/dashboard/` rendered the same dashboard for both, and the “Faculty / Admin” submission branch exposed every submission to any non-student account.
- Added the Faculty role and migration `accounts.0004_alter_user_role`. The registration form still creates Student accounts; administrators assign the Faculty role through Django admin.
- Created role-specific destinations: Student `/dashboard/`, Faculty `/faculty-dashboard/`, and Administrator `/admin-dashboard/`. Generic `/dashboard/` routes each signed-in user to their own page; navigation points to that role's page.
- Added a faculty overview with counts and recent submissions/resources owned by that faculty member. The review queue and grade/download permissions are restricted to resources owned by that faculty account; administrator access remains institution-wide.
- Added tests for role routing, unauthorized dashboard access, faculty queue scoping, and student/faculty denial for other people's submissions. Full suite now reports **115 passed**, one third-party deprecation warning. The role migration was applied and checked on a new disposable SQLite database at `scratch/role_dashboards_qa.sqlite3`; no user or production database was migrated.
- Browser visual testing was not performed for the new dashboard page in this turn. The route and access checks were exercised through Django's test client.
- Course assignments, enrollment-aware visibility, faculty course/grade analytics, and scheduled lab sessions remain future work because the current schema has no faculty-course enrollment or timetable models. They should be designed before building course-specific dashboards; resource ownership is the current faculty review boundary.

## Azure SQL readiness and final local verification — 2026-11-09

- The user confirmed Azure CLI reauthentication will be done tomorrow. The refresh token for Azure for Students expired, so no region, quota, resource, or identity checks could be performed, and no Azure resources were created.
- Added `DB_AUTH_MODE=managed_identity` support to the Django SQL Server settings. The configuration inspection confirmed the managed identity mode omits username/password and composes `Encrypt=yes;TrustServerCertificate=no;Authentication=ActiveDirectoryMsi`.
- Added production static-file configuration: `STATIC_ROOT`, production WhiteNoise middleware, and compressed manifest static storage. Local/test mode continues using Django's static file storage. Added `whitenoise==6.12.0` to `requirements.txt`.
- WhiteNoise 6.12.0 was installed into the ignored project virtual environment. Production-mode Django system check passed with the WhiteNoise middleware/storage enabled, and `collectstatic --dry-run --noinput` discovered 137 static files. Azure Oryx installation/build logs still need verification after deployment.
- Azure SQL migrations, managed identity permissions, Blob persistence, production settings, and the deployed login/static-asset smoke check remain unverified and are explicitly pending in `.azure/deployment-plan.md`.
- Latest local verification after the settings changes: `.venv\\Scripts\\python.exe -m pytest -q` — **116 passed, 1 third-party deprecation warning, 9.99s**; Django system check — **no issues**; migration drift check — **no changes detected**; dependency health — **no broken installed requirements**.
- Applied all Django migrations to disposable `scratch/azure_readiness.sqlite3`, then ran `migrate --check` successfully. This is SQLite-only and does not certify SQL Server/Azure SQL compatibility.
- Ran a configuration inspection with managed identity mode and verified no DB username/password are included. No live Azure SQL connection was attempted.
- Remaining non-blocking dependency warning: `openid` imports deprecated `defusedxml.cElementTree`.
- Academic submission readiness: **local automated QA passes; Azure deployment and Azure SQL verification remain pending**. Do not claim production completion until the Azure checklist is completed and the deployed app is smoke-tested.
- Local browser smoke test: launched Django against disposable `scratch/browser_smoke.sqlite3` and opened `/`, `/accounts/login/`, and `/accounts/register/`; the pages rendered with expected navigation and forms. An unauthenticated visit to `/resources/library/` redirected to sign-in. No authenticated role workflows, responsive viewport checks, or Azure/browser deployment checks were performed in this smoke pass. Minor copy mismatch observed: the landing page labels the library “Public” while the route requires sign-in.

## Role-specific dashboard implementation — 2026-11-09

- Replaced the shared dashboard experience with three distinct workspaces: Student Learning Desk, Faculty Teaching Workbench, and Admin Operations Console. Each has role-specific navigation, page structure, color treatment, and primary workflow focus while continuing to use existing role permissions and routes.
- Student view surfaces booking activity, submission feedback, saved manuals, and catalog actions. Faculty view prioritizes owned-resource review and publishing. Administrator view prioritizes system operations, account/resource activity, and audit context.
- Added role-specific responsive layout and focus styling in `static/css/dashboards.css`; no schema or migrations were added for this redesign.
- Automated verification after the changes: `.venv\Scripts\python.exe -m pytest -q` — **116 passed, 1 third-party deprecation warning**; test-settings Django system check — **no issues**; migration drift check — **no changes detected**; dependency check — **no broken requirements**; `git diff --check` — **passed** (Git emitted only line-ending normalization notices).
- Role route/template checks assert distinct role markers, headings, content, and navigation; cross-role access remains covered by the test suite. These are automated Django checks, not browser evidence.
- Browser verification of the new authenticated dashboards was **not completed** in this pass. The existing visible browser server on port 8000 used a different database than the synthetic accounts, and a separate local runserver could not be reached from the browser runner. Screenshots from the attempt were login pages and were discarded as dashboard evidence. Therefore the three dashboards have not been visually confirmed in a real browser, and desktop/tablet/mobile responsive behavior remains unverified by browser for this change.
- No critical or high-priority defect was identified by the automated checks. Follow-up before presentation: open each role with valid accounts and inspect all three viewport sizes, navigation, dashboard actions, and visual overflow. Azure remains pending as documented above.

## Role access clarity follow-up — 2026-11-10

- Fixed the raw debug-mode 403 shown when a user opened a different role's dashboard. The role dashboards still enforce their existing permission checks; mismatches now return a branded 403 explaining the signed-in role and required workspace.
- The denial page offers a safe route back to the current role's dashboard or a CSRF-protected sign-out that preserves the requested workspace. The sign-in page then identifies the expected account role.
- Verification: `.venv\Scripts\python.exe -m pytest -q` — **117 passed, 1 third-party deprecation warning, 11.18s**; Django system check — **no issues**; migration drift check — **no changes detected**; `git diff --check` — **passed** (line-ending normalization notices only).
- Added regression coverage for student/faculty/administrator role mismatch responses and the sign-out-to-targeted-sign-in flow. Browser verification with valid accounts is still pending because the active browser server does not contain the synthetic QA accounts; no real account credentials were available for this pass.
