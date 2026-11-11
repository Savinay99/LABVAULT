# Role-Specific Dashboards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Student, Faculty, and Administrator workspaces visibly distinct while preserving current routes, permissions, and data boundaries.

**Architecture:** Add role-specific authenticated navigation to the shared shell, and recompose each existing role dashboard template with an explicit role wrapper and purpose-specific hierarchy. Keep the visual system in a scoped dashboard stylesheet, using current Django view contexts and existing named URLs.

**Tech Stack:** Django templates, CSS custom properties, existing Django views, pytest-django, local browser.

---

## File map

- Modify `templates/base.html` — role identity, role-specific navigation, dashboard stylesheet hook.
- Modify `templates/dashboard/index.html` — Student Learning Desk structure and clear task hierarchy.
- Modify `templates/faculty/dashboard.html` — Faculty Teaching Workbench structure.
- Modify `templates/admin/dashboard.html` — Administrator Operations Console structure.
- Create `static/css/dashboards.css` — scoped color, layout, navigation, responsive, and focus styles.
- Modify `core/views.py` only if the approved dashboard needs a count from an existing model; do not change permissions.
- Modify `tests/test_routes.py` — role-specific labels/nav/content assertions and preserve isolation checks.
- Update `LABVAULT_COMPLETION_REPORT.md` — exact implementation and verification results.

## Task 1: Lock role navigation and identity with tests

- [ ] Add assertions that signed-in Student, Faculty, and Administrator responses contain their distinct navigation labels and root role classes.
- [ ] Assert each dashboard omits at least one navigation label reserved for another role.
- [ ] Run focused role dashboard tests and confirm the new assertions fail because the shell is currently shared.

## Task 2: Implement role-aware shared shell

- [ ] Add a stable role class/data attribute to authenticated dashboard content.
- [ ] Render role-specific sidebar labels using existing routes only; keep a shared logo, user identity, and sign-out.
- [ ] Load the dashboard stylesheet from the base template.
- [ ] Re-run the focused tests and confirm shell assertions pass.

## Task 3: Redesign Student Learning Desk

- [ ] Add test assertions for equipment booking, submission, bookmark, resource-library, and student-role sections.
- [ ] Run the focused test and observe failure before template changes.
- [ ] Recompose the Student template: welcome/quick actions first, bookings/submission status and bookmarks next, learning resources after.
- [ ] Add scoped student styles and responsive empty states.
- [ ] Run focused student dashboard and privacy tests.

## Task 4: Redesign Faculty Teaching Workbench

- [ ] Add test assertions for review queue priority, owned resources, faculty role marker, and faculty-only navigation.
- [ ] Run focused tests and observe failure.
- [ ] Recompose Faculty template with a prominent pending-review area, review metrics, and owned-resource panel.
- [ ] Add scoped faculty colors/layout; preserve the owner-filtered query and review permissions.
- [ ] Run faculty access-isolation and dashboard tests.

## Task 5: Redesign Administrator Operations Console

- [ ] Add test assertions for admin role marker, global platform metrics, audit activity, and admin-only navigation.
- [ ] Run focused tests and observe failure.
- [ ] Recompose Admin template into a platform overview with operational action cards and scan-friendly activity/audit tables.
- [ ] Reuse existing context and add only necessary aggregate queries over already-supported equipment/booking/maintenance models.
- [ ] Add scoped administrator styling and responsive table handling.
- [ ] Run administrator permission, dashboard, export, booking, and maintenance tests.

## Task 6: Responsive and accessibility pass

- [ ] Verify 1440px desktop, 768px tablet, and 390px mobile viewport styles.
- [ ] Ensure navigation remains available on small screens, tables scroll within their own containers, and no page-level horizontal overflow occurs.
- [ ] Check palette text contrast, visible keyboard focus, semantic headings, and accessible link names.
- [ ] Fix issues found and rerun relevant tests.

## Task 7: Final verification and report

- [ ] Run the complete pytest suite, Django system check, migration drift check, and `pip check`.
- [ ] Use a disposable SQLite database with synthetic role accounts/data for browser visits to all three dashboards; never use the user's configured DB or Azure.
- [ ] Update `LABVAULT_COMPLETION_REPORT.md` with actual browser, viewport, and automated results.
- [ ] Report any remaining limitations; do not claim unverified Azure SQL behavior.
