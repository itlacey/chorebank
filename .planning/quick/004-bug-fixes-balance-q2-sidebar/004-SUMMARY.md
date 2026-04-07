---
phase: quick
plan: 004
subsystem: kid-ui
tags: [htmx, balance, navbar, real-time]
completed: 2026-04-07
duration: "1 min"
dependency_graph:
  requires: [03-01, 02-03]
  provides: [real-time-balance-badge-refresh]
  affects: []
tech_stack:
  added: []
  patterns: [htmx-event-driven-partial-refresh]
key_files:
  created: []
  modified:
    - core/views.py
    - core/urls.py
    - templates/base_kid.html
decisions:
  - id: quick-004-01
    description: "BalanceBadgeView duplicates color logic from template tag rather than calling tag directly -- keeps view self-contained and avoids template tag invocation overhead for HTMX partial"
metrics:
  tasks_completed: 1
  tasks_total: 1
---

# Quick Task 004: Fix Balance Badge Refresh After Chore Completion

**One-liner:** HTMX-driven balance badge refresh on chore-completed event using lightweight partial endpoint

## What Was Done

### Task 1: Add balance badge endpoint and wire HTMX refresh

**Commit:** 74ab869

Added `BalanceBadgeView` -- a simple GET endpoint returning the `_balance_badge.html` partial with fresh balance data. Wired the kid navbar badge in `base_kid.html` with `hx-trigger="chore-completed from:body"` so the badge auto-refreshes whenever the existing chore completion event fires.

**Files modified:**
- `core/views.py` -- Added `BalanceBadgeView(KidRequiredMixin, View)` with balance computation and color coding
- `core/urls.py` -- Added `/kid/balance-badge/` route mapped to `BalanceBadgeView`
- `templates/base_kid.html` -- Added `hx-get` and `hx-trigger` attributes to balance badge container

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 74ab869 | Add HTMX balance badge refresh on chore completion |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

- `python manage.py check` -- 0 issues
- `BalanceBadgeView` imports successfully
- `hx-trigger="chore-completed from:body"` confirmed in base_kid.html
- Reuses existing `_balance_badge.html` partial (no template duplication)

## Self-Check: PASSED
