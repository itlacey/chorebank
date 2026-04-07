---
phase: quick-005
plan: 01
subsystem: features
tags: [timer-history, weekly-summary, streaks, time-requests, htmx]
depends_on:
  requires: [quick-001, 03-02, 04-02]
  provides: [timer-history-page, weekly-chore-summary, streak-on-parent-dashboard, ask-for-time]
  affects: []
tech-stack:
  added: []
  patterns: [htmx-load-more, rate-limited-requests]
key-files:
  created:
    - templates/core/timer_history.html
    - templates/core/_timer_history_rows.html
    - templates/core/_ask_time_result.html
    - templates/core/_empty.html
    - core/migrations/0009_timerequest.py
  modified:
    - core/models.py
    - core/views.py
    - core/urls.py
    - templates/core/parent_home.html
    - templates/core/kid_home.html
    - templates/core/timer.html
    - templates/base_kid.html
metrics:
  duration: 3 min
  completed: 2026-04-07
---

# Quick 005: Feature Wins - History, Summary, Streaks, Ask

Four quick feature wins surfacing existing data and adding kid-parent communication.

## One-liner

Timer history page, weekly chore summary + streaks on parent dashboard, and ask-for-more-time button with parent notifications.

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Timer session history page for kids | c4f6337 | timer_history.html, _timer_history_rows.html, base_kid.html |
| 2 | Weekly chore summary + streak on parent dashboard | f3c20a7 | views.py, parent_home.html |
| 3 | Ask for More Time button and parent notifications | 4b716da | models.py, views.py, urls.py, kid_home.html, timer.html, parent_home.html |

## What Was Built

### Task 1: Timer Session History
- TimerHistoryView with HTMX load-more pagination (PAGE_SIZE=20)
- Shows date, start time, duration (actual vs requested), and end reason (manual/expired)
- History nav item added to kid sidebar with clock-history icon

### Task 2: Weekly Chore Summary + Streaks on Parent Dashboard
- Bulk-fetched weekly chore instances (Monday through today) to avoid N+1
- "This week: X/Y chores" line below daily progress bar on kid cards
- Fire streak display with day count and longest streak when streak > 0

### Task 3: Ask for More Time
- TimeRequest model (kid, message, created_at, dismissed)
- Rate-limited to one non-dismissed request per 30 minutes
- HTMX button on kid home page and timer page (especially when balance <= 0)
- Parent dashboard notification banner with per-request dismiss buttons

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Rate limit 30 min on time requests | Prevents spam while still letting kids ask again if no response |
| TimeRequest model vs simple notification | Persistent requests survive page reloads, parents see history |
| Button shown for all kids (not just zero balance) | Kids with time may still want more; button styled differently |

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `python manage.py check` passes with no errors
- `python manage.py makemigrations --check` shows no pending migrations
- All new URLs registered: /kid/timer/history/, /kid/ask-time/, /parent/dismiss-request/<pk>/
- Parent dashboard shows weekly summary, streaks, and time request notifications
- Kid home and timer pages show "Ask for More Time" button

## Self-Check: PASSED
