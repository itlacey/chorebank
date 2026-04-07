---
phase: quick
plan: 007
subsystem: ui
tags: [timezone, intl, javascript, htmx]

requires:
  - phase: 02-chore-system
    provides: chore log with completed_at timestamps
  - phase: 03-time-bank-timer
    provides: transaction history with created_at timestamps
provides:
  - "Client-side UTC-to-local timezone conversion for all timestamps"
  - "data-utc pattern for future timestamp elements"
affects: [any page adding timestamps]

tech-stack:
  added: []
  patterns: ["data-utc attribute pattern for client-side timezone conversion via Intl.DateTimeFormat"]

key-files:
  created: []
  modified:
    - templates/core/_chore_log_rows.html
    - templates/core/_transaction_rows.html
    - templates/base.html

key-decisions:
  - "Intl.DateTimeFormat for locale-aware formatting instead of manual string building"
  - "data-format='long' attribute distinguishes date+time vs time-only display"
  - "htmx:afterSwap listener ensures Load More rows also get converted"

patterns-established:
  - "data-utc pattern: wrap timestamps in .local-time span with data-utc ISO attribute for automatic conversion"

duration: 1min
completed: 2026-04-07
---

# Quick 007: Fix Chore Log Timezone from Browser Summary

**Client-side UTC-to-local timezone conversion using Intl.DateTimeFormat with data-utc attributes and htmx:afterSwap support**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-07T19:46:36Z
- **Completed:** 2026-04-07T19:47:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- All timestamps across the app now display in the user's local browser timezone
- HTMX "Load More" rows automatically get timezone conversion via htmx:afterSwap listener
- Zero backend changes, zero new dependencies -- pure client-side JS solution

## Task Commits

Each task was committed atomically:

1. **Task 1: Add data-utc attributes to timestamp cells** - `b323898` (feat)
2. **Task 2: Add global timezone conversion JS to base.html** - `c9eae48` (feat)

## Files Created/Modified
- `templates/core/_chore_log_rows.html` - Added .local-time span with data-utc around completed_at
- `templates/core/_transaction_rows.html` - Added .local-time span with data-utc and data-format="long" around created_at
- `templates/base.html` - Added convertTimesToLocal() JS with DOMContentLoaded and htmx:afterSwap listeners

## Decisions Made
- Used Intl.DateTimeFormat for locale-aware formatting (respects user's locale settings)
- Two format modes via data-format attribute: short (time only) and long (date + time)
- Global JS in base.html rather than per-page scripts for DRY approach

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Pattern established for any future timestamp displays: wrap in .local-time span with data-utc
- No blockers

## Self-Check: PASSED

---
*Quick task: 007*
*Completed: 2026-04-07*
