# LabVault Four-Role Phase — Codex Master Implementation Prompt

Copy the prompt below into Codex with the `E:\labvault` project open. It is deliberately based on the current Django repository and does not authorize Azure deployment.

---

## PROMPT START

You are the lead architect and implementation engineer for the existing LabVault project at `E:\labvault`.

Implement the four-role phase described here in the existing application. Work in the real repository. Preserve functioning features and current visual design. Do not rebuild the project from scratch, replace working modules, or trust the status labels in older documentation without checking the current code.

### 1. Non-negotiable constraints

- The active application is Django 5.2 in a server-rendered modular monolith. Use the existing `core`, `accounts`, and `resources` apps and their templates/static assets. Do not switch the active app to Flask, Next.js, or Express.
- Azure implementation is out of scope. Do not run Azure login, provision resources, deploy, or require Azure credentials. Preserve Azure SQL and Blob Storage integration code. Keep the app runnable with local test/development configuration and Azure variables absent.
- Preserve the approved LabVault visual language: tokens, typography, spacing, shared shell, components and responsive behavior. Do not redesign the application or add animation libraries.
- Do not add AI features, AI branding, or AI-related user-facing text. Avoid the word “smart” in user-facing copy.
- Do not invent metrics or leave placeholder routes, buttons, fake data, or unimplemented UI controls.
- Do not hard-delete history-bearing users, instruments, bookings, submissions, or audit records through routine UI. Deactivate/archive and preserve history.
- Do not edit `.env`, production data, external systems, or Azure. Do not remove user work or prior QA modifications. Avoid broad unrelated refactors.
- The role policy below is fixed in code. The admin UI may show the permission matrix read-only; do not implement editable permission rules.
- Do not ask the user to repeat choices already fixed here. If the repository reveals a real conflict or a destructive migration would be needed, document it and choose the safest non-destructive path.

### 2. Verify the actual baseline before changing code

Inspect the repository, `AGENTS.md` files, current branch/status/diff, README, installed dependencies, models, forms, views, URLs, templates, static assets, migrations, tests, security settings, storage adapters, and project documentation. Preserve uncommitted user changes.

The starting state found during specification review was:

- `accounts.User` had application roles `student` and `administrator`, email login, and student/admin convenience properties. Registration explicitly creates student accounts.
- Existing resource models included `Resource`, `ResourceFiles`, `Category`, `Subject`, `ResourceSubject`, access logs, bookmarks, `Notification`, and `AuditLog`.
- Existing equipment models included `Instrument`, `InstrumentBooking`, `InstrumentIssue`, and `InstrumentMaintenance`. `Instrument.asset_id` was unique, while location was text and no Room model existed.
- `LabSubmission` stored student/resource/file metadata/hash/status/grade/feedback/reviewer/timestamps, but had no course/assignment scope or submission-version history.
- The interface used Django templates, CSS and vanilla JavaScript.
- SQL Server through `mssql-django` and optional Azure Blob Storage were configurable. This does not mean live Azure was tested.

These are inspection clues, not assumptions. Verify them against the current checkout. Build a concise baseline feature/status matrix (`existing and working`, `existing but incomplete`, `new`) before implementation. Run the baseline tests/checks before editing. Do not claim an unrun check.

### 3. Four fixed application roles and authority boundaries

Implement exactly one LabVault role per user:

- `student`: own bookings, submissions, grades/feedback, profile and notifications; authorized course resources; request/cancel own pending booking and resubmit only when permitted.
- `faculty`: assigned-course dashboard, students, sessions, course resources, course-scoped booking/issue read-only visibility, submissions and history, grading/feedback/resubmission request, progress and course export.
- `lab_manager`: operational inventory, room allocations, all booking decisions, equipment issue/return, maintenance/inspection, room schedules, operational reports and notifications.
- `admin`: user/role lifecycle, academic structure and assignments, operational policy values, system summaries, read-only oversight, audit/security events and system-wide reports.

Fixed workflow policy:

1. Public registration creates Student accounts only.
2. Only Admin provisions Faculty and Lab Manager accounts. Enforce a temporary password change before using protected pages if temporary credentials are implemented.
3. Lab Manager exclusively approves/rejects routine bookings and records equipment issue/return.
4. Faculty exclusively reviews/grades submissions and requests resubmission, scoped to assigned courses.
5. Admin does not do routine inventory work or grade. Admin may perform a booking override only with a written reason; the action is audited and notifies the Lab Manager. Emergency equipment deactivation requires a reason and audit record.
6. A student sees only their own private data. Faculty scope is limited to their assigned courses and students enrolled in those courses. Lab Manager cannot manage accounts or grades. Admin cannot silently alter grades.
7. Roles/permissions are not editable in the UI. Operational policy is limited to typed, validated values.
8. Protect against self-role changes and deactivating/demoting the last active administrator.

Keep Django `is_staff` and `is_superuser` semantics distinct from application roles; do not use either as a shortcut for LabVault authorization.

### 4. Permission matrix

Legend: V view, C create, U update, A approve/decide, X archive/deactivate, E export, own current user's records, course assigned courses.

| Feature | Student | Faculty | Lab Manager | Admin |
|---|---|---|---|---|
| Own profile/notifications | V/U | V/U | V/U | V/U |
| Other accounts/activity | — | — | — | V/C/U/X/E |
| Role assignment | — | — | — | C/U, not self |
| Own bookings | V/C/cancel pending | — | V all | V all |
| Course bookings | — | V course/read-only | V all | V all |
| Routine booking approval | — | — | A | — |
| Emergency booking override | — | — | — | A with reason/audit/notice |
| Issue/return | V own | V course | C/U | V read-only |
| Equipment details | V public | V public | V/C/U/X | V; emergency X audited |
| Room/allocation/schedules | — | V course schedule | V/C/U/X | V and master-data control |
| Maintenance | — | — | V/C/U | V read-only |
| Course/subject data | V own | V assigned | V operational refs | V/C/U/X |
| Assignment/enrollment | V own enrollment | V assigned | — | V/C/U/X |
| Resources/manuals | V authorized | V/C/U/X assigned | V/C/U equipment docs | V/U/X oversight |
| Submissions | C/V own/resubmit when permitted | V assigned | — | V read-only |
| Grade/feedback | V own | V/C/U/A assigned | — | V read-only |
| Progress/grade export | V own | V/E course | — | V/E system-wide |
| Operational reports | — | — | V/E | V/E |
| Audit/security log | — | — | — | V/E |
| Operational policy | — | read-only where relevant | V read-only | V/U |

Deletion of history-bearing records is archive/deactivation. Hiding UI is never a substitute for server enforcement.

### 5. Architecture and authorization implementation

- Continue with the Django modular monolith. Add bounded modules only when useful; do not split into services or activate dormant prototypes.
- Create a central authorization layer: named role guards/decorators or mixins plus reusable scoped-query helpers for Student-owned records and Faculty course scope. Use it consistently across HTML views, downloads, forms, exports, and any APIs.
- Deny by default. Anonymous users go to login. Logged-in users with the wrong role get 403. Return 404 for an out-of-scope object where this avoids leaking its existence.
- Resolve object scope in the queryset/service before rendering or mutating. Validate submitted related-object IDs server-side; never accept client-supplied user/course/role authority.
- Use explicit form allowlists. Self-service profile forms cannot write role, activation, enrollment, or employee IDs. Admin-only role assignment must be audited.
- Change navigation according to role, but test direct URL access independently.
- Audit role changes, activation/deactivation, booking approval/rejection/override, issue/return, instrument move/deactivation, maintenance transitions, grading/resubmission, policy changes, and exports. Never log secrets, passwords, or private file contents.
- Preserve CSRF on state changes, POST-only workflow transitions, secure session settings, input validation, upload allowlists and size checks, randomized storage keys, checksums, and protected file downloads.
- Verify role/account changes invalidate active sessions. Keep error pages free of internal details.

### 6. Data model and migration strategy

First map existing migrations/models and production-like data constraints. Reuse existing models. Do not create duplicate resource, instrument, booking, issue, maintenance, submission, subject, notification, or audit tables.

#### Existing models to evolve

- Extend `User` with the four fixed roles. Create a reversible, tested data migration mapping `administrator` to `admin`; leave student roles unchanged. Preserve Django staff/superuser fields separately. Update convenience properties, managers, admin forms, tests, templates, and seed/test factories.
- Reuse `Subject` as the course/subject identity after confirming its use. Add Department/course metadata only when it does not duplicate another existing model.
- Preserve `Instrument` as one row per individually tracked asset. Keep asset ID unique; add optional unique serial number and nullable Room FK. Existing text location must be preserved and mapped only when the mapping is unambiguous. Do not silently discard it.
- Reuse booking/issue/maintenance models. Add optional course, decision actor/time/note, scheduling/status fields as necessary. Preserve existing statuses and history.
- Evolve `LabSubmission` as a logical submission, retaining its existing associations during migration. Preserve current files, grades, feedback, reviewers, and timestamps.
- Reuse resource/file, Notification, and AuditLog models. Extend only missing fields/indexes after checking portability.

#### Add only missing relational entities

1. `Department` where no equivalent exists.
2. One-to-one role profiles for student/faculty/lab manager only for role-specific identifiers; avoid a giant profile full of unrelated nullable columns.
3. `CourseAssignment(faculty, subject/course, term)` unique on faculty/course/term.
4. `Enrollment(student, subject/course, term, active)` unique on student/course/term.
5. `Laboratory` and `Room`, with room unique within laboratory and nonnegative capacity. Add nullable room links to existing instruments and preserve legacy location.
6. Instrument movement history (asset, old/new room, actor, timestamp) if the existing audit event cannot represent a durable asset timeline.
7. `LabSession(course, room, start, end, instructor)` only if no scheduling equivalent exists.
8. `Assignment(course, title, instructions, due date, active/archive)` if existing resources cannot represent coursework assignments cleanly.
9. `SubmissionVersion(submission, version, safe file metadata/hash/storage key, actor, timestamp)`, unique per submission/version. Migrate the current file to version 1.
10. `SubmissionReview(version, reviewer, bounded grade, feedback, decision, timestamp)` to preserve review history. Migrate existing grade/reviewer/feedback to a review row where present.
11. Typed and validated operational policy storage only for real policy settings.

Do not add a stored `overdue` flag or duplicated availability table: derive these from issue due/return timestamps and booking/maintenance/session records. Keep one row per serialized instrument; report quantity by counting active assets instead of duplicating an inventory total. Bulk consumables, costs, QR labels, PDF export, email integration, and multi-role users are out of scope.

Use appropriate FK deletion rules, unique/check constraints and query-driven indexes. At minimum inspect indexes for role/active, course scope, booking conflict queries, due/return, maintenance schedule/status, submission assignment/status/student, notification recipient/read state, and audit actor/action/time. Use `transaction.atomic()` and database-appropriate row locks for approval, issue/return, room and equipment conflict decisions. If an invariant cannot be portably constrained, document and test the service-level guarantee. Test migrations forward and backward on isolated test copies where supported; never reset or recreate the user's database.

### 7. Required portal behavior

#### Student

- Personalized dashboard with real active/pending bookings, issued/due/overdue items, submission states/grades, and unread notifications.
- Search/filter equipment by category, room, status and date availability; show public specifications and booking conflict feedback.
- Request a valid booking, track status/decision note, cancel own pending request, see issued equipment/due date/history.
- Access public or enrolled-course manuals through authorized download.
- Submit files to assignments, see deadlines/status/review, and resubmit only when allowed. Display feedback and review history.
- Manage profile without changing role or account state.

#### Faculty

- Distinct dashboard with assigned courses, review queue, assigned student counts, sessions and recent academic activity from real data.
- Course pages and all filters/counts/downloads/exports are scoped to assignments/enrollments.
- Read-only course booking/issue information; no booking decision/issue/return controls.
- Review versions, grade within valid range, provide feedback, or request resubmission with a reason. Preserve history and send student notification.
- Manage resources for assigned courses and export assigned-course grades only.

#### Lab Manager

- Distinct operational dashboard and inventory CRUD/archive; unique asset/serial, specifications, condition, status, category and room allocation.
- Booking queue with availability conflict information, filters and decision notes. Approve/reject; issue approved items with due date; receive return with condition notes.
- Maintenance and inspection record creation/scheduling/completion. Failed inspection prevents booking; restoration to available follows an explicit successful workflow.
- Manage laboratories/rooms/capacity and sessions, with room-overlap checks.
- Operational reports and scoped CSV: inventory/condition, utilization, bookings, overdue, maintenance.

#### Admin

- Distinct governance dashboard and user/role/account lifecycle UI.
- Manage departments/subjects, Faculty assignments, student enrollments, labs/rooms master data and operational policies.
- Show fixed permission matrix read-only. System-wide reports and audit/security event viewing/export.
- Read-only grade/inventory oversight; reason-required, audited booking override and emergency equipment deactivation; notify Lab Manager.
- Protect last active admin and self-role change.

### 8. Shared UI, usability and accessibility

- Start with baseline screenshots of current pages and inventory existing CSS tokens/components. Retain the current visual design.
- Give each role role-appropriate navigation and dashboard while reusing shared layout/components.
- Lists use usable search/filters/pagination; every status is labeled with text as well as color.
- Provide validation, permission-denied, empty, loading, success and failure states. Confirm disruptive status changes.
- Make all buttons/links functional; remove or clearly disable unavailable actions. No fake metrics.
- Check desktop/tablet/mobile at 1280, 768 and 360 CSS pixels. Tables may scroll internally; page-level horizontal overflow is not acceptable.
- Keyboard test navigation, form controls and dialogs. Include labels, visible focus, semantic headings, sufficient contrast, alt text and accessible messages.
- Fix the current reported loader so it plays at most once per browser session and never blocks navigation/authenticated route changes. Add the missing favicon and link tag without redesigning the logo.

### 9. Tests and verification required

Add or update tests before relying on UI changes. Use the current test settings/pytest conventions. Do not skip existing tests to achieve a pass.

#### Unit/model/service tests

- Role constants/migration, profile invariants, unique/valid grade, booking and room overlap rules, overdue computation, status transitions, audit and notification creation.
- Atomic booking approval/issue/return and maintenance transitions, including invalid sequences and concurrency-sensitive service behavior.
- Resource and submission version migration/persistence; checksums and protected file authorization.

#### Permission matrix tests

For every protected route family, test anonymous plus all four roles, including direct URLs, object ID substitution, POST requests, downloads, filters, and exports. Specifically prove:

- Student A cannot see or mutate Student B's bookings/submissions/profile/files.
- Faculty cannot list/read/download/grade a student or course outside their assignment, even by changing IDs/query parameters.
- Faculty cannot approve, reject, issue, return, or mutate inventory.
- Lab Manager cannot change roles, grade, access global audit logs, or edit course/enrollment data.
- Admin cannot grade; emergency operational overrides require reason and create audit + notification.
- Self-role changes and removal/demotion of the last active admin are denied.
- Every successful role mutation/event is auditable; every denied mutation leaves records unchanged.

#### End-to-end browser workflows

Actually start the local application using an isolated test database and test files. Never use production credentials/data. Use a real browser automation surface if available; otherwise report precisely which UI was and was not verified.

1. Student login → search/filter equipment → request → see pending → cancel own pending request.
2. Lab Manager login → find booking → approve and reject two requests → issue approved item → return with condition → inspect audit/notification.
3. Overdue issue is shown to the owner, Faculty only when the student/course is assigned, Lab Manager and Admin according to matrix.
4. Lab Manager creates failed inspection and repair/pass record; status/availability changes correctly.
5. Admin provisions Faculty and Lab Manager, changes role/state, records audit, protects last admin, sets policy.
6. Admin assigns Faculty to course and enrolls students; each sees only permitted scopes.
7. Student submits report → assigned Faculty reviews/grades or requests resubmission → student uploads next version and sees feedback/history → Admin sees read-only result.
8. Resource creation/edit/archive, course access, and protected download behavior.
9. Navigation, footer, all visible buttons/links/forms/dialogs and permission/error states.
10. Responsive checks at 360, 768 and 1280 pixels; verify no page overflow and keyboard operation.

Do not state browser verification unless the browser was used. Save genuine before/after screenshots or note if unavailable. Use synthetic data in disposable test storage.

#### Commands

Run the repository's supported full test suite plus appropriate checks, including where available:

- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe manage.py check --settings=labvault_project.settings_test`
- `.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=labvault_project.settings_test`
- Apply migrations on isolated SQLite and check no unapplied migrations; never target configured production or Azure DB.
- `.venv\Scripts\python.exe -m pip check`
- Production configuration checks with synthetic throwaway settings only; report expected environment-dependent warnings instead of weakening security defaults.
- Frontend/dependency audit only for active components; dormant prototype dependencies are not the active app.

Report exact command, exit status, count, warning/error and duration where practical. Fix all critical/high issues that can be safely fixed within this phase. Record noncritical issues.

### 10. Documentation to produce/update

Keep docs consistent with actual code and label planned/unverified behavior honestly. Update or create:

- `LABVAULT_PRODUCT_SPECIFICATION.md` and this prompt as project scope references.
- `docs/ARCHITECTURE.md` with role, component and data-flow diagrams.
- `docs/DATABASE.md` with current ERD, fields/constraints/indexes, migration notes, key query examples and known service-level invariants.
- `docs/PERMISSION_MATRIX.md` with the implemented matrix.
- `docs/SECURITY_AND_PRIVACY.md` with implemented vs planned controls and scoping test evidence.
- `docs/AZURE_MAPPING.md` with local configuration, preserved integration points, and exact later Azure work; explicitly state that this phase did not connect/deploy.
- Role workflow guides and `docs/DEMO_SCRIPT.md` if they can be completed from verified behavior.
- `LABVAULT_COMPLETION_REPORT.md` with test evidence, browser/responsive results, migration status, remaining defects, academic readiness, and Azure tasks pending.
- A concise repository cleanup report only if needed; do not delete legacy folders without an explicit separate cleanup scope.

### 11. Execution sequence

1. Inspect current state and preserve changes. Capture baseline checks/screenshots and write an evidence-based existing/partial/new matrix.
2. Build/test centralized role guards, scoping helpers, and safe role migration before expanding UI. Test direct access denial.
3. Design only the missing profile, department/course assignment/enrollment, lab/room/session, assignment and submission history schema. Review each relation against existing models before adding it.
4. Create reversible migrations and test forward/backward behavior on isolated databases with existing representative data.
5. Implement role services/views and workflows with transactions, audit, notifications, and explicit forms.
6. Build each portal using the existing design system. Ensure all links/actions and empty/error states work.
7. Run automated role/workflow/security tests and real-browser E2E/responsive checks. Fix defects and rerun the full suite.
8. Update architecture/database/security/Azure/user documentation and final report from evidence.

Do not stop after planning: complete the authorized implementation and verification. If an essential ambiguity remains after inspecting source and this prompt, state the safe assumption, continue independent work, and ask only for input that genuinely blocks a risky or irreversible decision.

### 12. Final response format

When implementation is finished, report:

1. Summary of what changed, including what existing functionality was reused.
2. Files/models/migrations changed and any data migration behavior.
3. Exact test/system/migration/security command results.
4. Browser workflows and viewport sizes actually verified; list any not verified.
5. Remaining bugs, risks and scope exclusions.
6. Exact Azure work pending and an explicit statement that Azure was not provisioned/deployed/tested.
7. Academic demo/submission readiness with qualifications; never claim 100% completion without evidence.

## PROMPT END

---

Use the product specification at `LABVAULT_PRODUCT_SPECIFICATION.md` as the source of truth for detailed role behavior, data design, priorities, acceptance criteria, and submission mapping. If the project code changes later, inspect it again; this prompt is not a substitute for a current-code audit.
