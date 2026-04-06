---
phase: quick
plan: 002
subsystem: frontend
tags: [htmx, csrf, bug-fix]

dependency-graph:
  requires: [02-03]
  provides: ["Working HTMX requests across all pages"]
  affects: []

tech-stack:
  added: []
  patterns: ["Cookie-based CSRF token for HTMX requests"]

key-files:
  created: []
  modified:
    - templates/base.html

decisions:
  - id: Q002-1
    decision: "Cookie-based CSRF instead of DOM query"
    reason: "More robust -- works regardless of form presence on page"

metrics:
  duration: "3 min"
  completed: "2026-04-03"
---

# Quick 002: Fix Kid Chore Done Button Summary

**One-liner:** Replaced wrong template tag and switched to cookie-based CSRF to restore HTMX functionality site-wide.

## What Was Done

### Task 1: Load HTMX library and fix CSRF token delivery
- Replaced `{% django_htmx_script %}` with `{% htmx_script %}` in `templates/base.html`
- `{% django_htmx_script %}` only outputs a debug helper script, not the actual HTMX library
- `{% htmx_script %}` loads `htmx.min.js` via a deferred script tag
- Replaced DOM-based CSRF token lookup (`document.querySelector("[name=csrfmiddlewaretoken]")`) with cookie-based approach (`document.cookie` parsing for `csrftoken`)
- Verified `CSRF_COOKIE_HTTPONLY` is not set (Django default False), so cookie is JS-readable

### Task 2: End-to-end verification
- Started dev server, logged in as kid user `zeke`
- Confirmed kid chore list page renders with HTMX script tag (`htmx.min.js`)
- Confirmed `hx-post` attribute present on Done button
- Confirmed `htmx:configRequest` listener present in page
- POSTed to `/kid/chores/1/complete/` with HTMX headers
- Got 200 response with `HX-Trigger: chore-completed` header
- Response HTML contains `check-circle-fill` (completed checkmark state)

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Load HTMX library and fix CSRF token delivery | a628de7 | templates/base.html |
| 2 | End-to-end verification | (no changes) | verification only |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

1. `templates/base.html` contains `{% htmx_script %}` -- PASS
2. Rendered HTML includes `<script src="...htmx.min.js" defer>` -- PASS
3. CSRF token read from cookie in inline script -- PASS
4. `python manage.py check` passes -- PASS
5. CompleteChoreView returns 200 + `HX-Trigger: chore-completed` -- PASS

## Self-Check: PASSED
