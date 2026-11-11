# LabVault Role-Specific Dashboards — Design

Date: 2026-11-09
Status: Design approach approved by the user; written spec review pending

## Problem

Student, Faculty, and Administrator pages render different data, but all inherit the same global header, sidebar, metric-card grid, and content hierarchy. Their role differences are mostly labels and counts, so a user cannot quickly tell which workspace they are in.

## Goals

- Make each role dashboard visually and structurally distinct at first glance.
- Put that role's common work and primary actions first.
- Use role-appropriate navigation and visual language across both the app shell and dashboard content.
- Preserve existing URLs, permissions, data visibility, and workflows.
- Make each dashboard work at desktop, tablet, and mobile widths.

## Scope and non-goals

This is a focused information architecture and visual redesign of the existing three dashboards and their authenticated shell. It does not add database models, role types, new permissions, or a new product workflow. Dashboard content should use existing view context where practical. Any broken or misleading navigation discovered during implementation may be corrected without weakening access controls.

## Design

### Shared shell

Keep a familiar LabVault brand mark, account identity, responsive behavior, and sign-out. Render a clear role marker and a role-specific navigation set. Each role gets a distinct dashboard wrapper/data attribute so its page styling cannot unintentionally spill into another role.

### Student — Learning Desk

- Palette: cobalt and indigo with a bright, welcoming canvas.
- Visual hierarchy: greeting and library/equipment actions first; then concise cards for the student's equipment requests, submission statuses, and saved resources; then a learning-resource feed.
- Navigation: Overview, Resource Library, Instruments, Submissions, Verify File, Profile. Bookmarks remain accessible in the student dashboard; booking actions remain in Instruments and the dashboard.
- Existing student-only data remains scoped to the signed-in student.

### Faculty — Teaching Workbench

- Palette: teal and emerald with an instructor-focused workspace treatment.
- Visual hierarchy: review backlog and “Review submissions” action first; then submitted/reviewed/student metrics; then a prominent submission queue beside owned teaching resources.
- Navigation: Overview, Submissions & Grading, Resource Library, Upload Resource, Profile. Owned resources remain surfaced in the Faculty dashboard; navigation does not imply a new owner-filtered library page.
- The current rule that faculty can review submissions only for resources they own remains unchanged.

### Administrator — Operations Console

- Palette: deep slate/navy with amber status accents and dense, scan-friendly operational tables.
- Visual hierarchy: platform-wide totals, then system activity/resources/users and access audit trails; administrative actions and exports remain easy to reach.
- Navigation: Overview, Django Console, Instruments & Bookings, Submissions, Resource Library, Security Audit, Equipment Export, Audit Export, Profile. Maintenance actions remain linked from instrument records; no new maintenance index page is implied.
- Existing administrator-only checks and routes remain the source of authorization; hiding a link is never treated as permission enforcement.

## Implementation boundaries

- Put role-specific page styles in a dedicated dashboard stylesheet and scope selectors by role wrapper.
- Keep shared typography, buttons, focus treatment, and brand behavior from the existing design system.
- Replace generic authenticated navigation with role-aware navigation using existing named routes.
- Recompose each dashboard template around its existing view context. Only add context queries for existing operations that are already available and needed by the approved screen design; do not add models or alter authorization.
- Preserve empty states and clearly label them; use real database values rather than hard-coded counts.

## Acceptance criteria

1. A student, faculty member, and administrator can identify their dashboard role without reading the page title alone.
2. Header/sidebar navigation and content hierarchy differ materially for all three roles.
3. Student sees their own bookings, submissions, and bookmarks only.
4. Faculty sees their own resources and review queue only.
5. Administrator retains the existing institution-wide overview and audit information.
6. Existing dashboard routes, redirects, and authorization tests continue to pass.
7. No horizontal overflow at 1440px desktop, 768px tablet, or 390px mobile; tables/cards remain usable and navigation remains reachable.
8. Text, focus indicators, and role-status colors maintain readable contrast in all three palettes.
9. Browser verification visits each role dashboard in a disposable local database, with test-only accounts and data isolated from the user's configured database.

## Verification

- Run the existing Django automated suite and system/migration checks.
- Add or update template/route tests for role labels, role navigation, and content sections.
- Use a disposable SQLite database for browser verification; do not use Azure or the user's configured database.
- Verify the three dashboards at desktop, tablet, and mobile viewport sizes and report exact scope/results.

## Risks

- Shared styles may continue to flatten the look if role scopes are too weak; use clear wrapper classes and dedicated role navigation.
- Some target navigation labels do not map to dedicated views. Use existing named URLs and avoid fake controls.
- Empty disposable databases can make screens look sparse; browser verification should seed disposable test data and report that it is synthetic.
