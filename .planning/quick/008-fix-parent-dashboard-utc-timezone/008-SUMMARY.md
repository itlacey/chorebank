---
phase: quick-008
plan: 01
subsystem: dashboard-timezone
tags: [timezone, middleware, parent-dashboard, localdate]
dependency_graph:
  requires: [quick-007]
  provides: [timezone-middleware, local-date-boundaries, local-time-display]
  affects: []
tech_stack:
  added: []
  patterns: [timezone-middleware-cookie, zoneinfo-activation]
key_files:
  created:
    - core/middleware.py
  modified:
    - templates/base.html
    - chorebank/settings.py
    - templates/core/parent_home.html
decisions:
  - id: q008-01
    choice: "America/New_York fallback when browser_tz cookie missing"
    reason: "Family is in Eastern Time; sensible default prevents UTC issues on first load"
metrics:
  duration: "49 seconds"
  completed: "2026-04-07"
---

# Quick 008: Fix Parent Dashboard UTC Timezone Summary

**One-liner:** TimezoneMiddleware activates browser IANA timezone per-request so dashboard localdate/localtime reflect user's actual local time instead of UTC.

## What Was Done

### Task 1: Add timezone cookie JS and Django TimezoneMiddleware
- Created `core/middleware.py` with `TimezoneMiddleware` that reads `browser_tz` cookie
- JS snippet in `base.html` sets `browser_tz` cookie via `Intl.DateTimeFormat().resolvedOptions().timeZone`
- Middleware validates timezone with `zoneinfo.ZoneInfo`, falls back to `America/New_York`
- Calls `timezone.activate()` before request, `timezone.deactivate()` in `finally` block
- Registered in `settings.py` MIDDLEWARE after `AuthenticationMiddleware`
- **Commit:** `89d1757`

### Task 2: Add local-time display to parent dashboard activity timestamps
- Added `{{ txn.created_at|date:"M j, g:i A" }}` to each transaction row in parent_home.html
- Django's `date` filter respects the activated timezone automatically
- Compact 0.7rem styling keeps the UI clean
- **Commit:** `3aaa7a5`

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 89d1757 | TimezoneMiddleware + browser_tz cookie JS |
| 2 | 3aaa7a5 | Local-time timestamps on parent dashboard transactions |

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| q008-01 | America/New_York fallback | Family is EST; prevents UTC display on first page load before cookie is set |

## How It Works

1. Browser JS sets `browser_tz` cookie (e.g., `America/New_York`) on every page load
2. `TimezoneMiddleware` reads the cookie and calls `django.utils.timezone.activate()`
3. Django's `localdate()` in `ParentHomeView` now returns the correct local date
4. "Chores done today" and "This week" counts use local date boundaries
5. Transaction timestamps render via `|date` filter in the activated timezone
6. On response completion, `timezone.deactivate()` cleans up

## Self-Check: PASSED
