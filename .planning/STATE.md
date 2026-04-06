# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31)

**Core value:** Kids always know exactly how much screen time they've earned, and parents control the rules without daily nagging — the system enforces itself.
**Current focus:** Phase 4 complete. Quick tasks in progress.

## Current Position

Phase: 4 of 4 (Automation & Dashboard)
Plan: 2 of 2 in current phase
Status: Quick tasks in progress
Last activity: 2026-04-03 -- Completed quick-002 (fix kid chore Done button)

Progress: [████████████] 100% + quick tasks

## Performance Metrics

**Velocity:**
- Total plans completed: 12
- Average duration: 2.8 min
- Total execution time: 0.57 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation-auth | 3 | 14 min | 4.7 min |
| 02-chore-system | 4 | 10 min | 2.5 min |
| 03-time-bank-timer | 3 | 6 min | 2.0 min |
| 04-automation-dashboard | 2 | 4 min | 2.0 min |

**Recent Trend:**
- Last 5 plans: 03-02 (2 min), 03-03 (2 min), 04-01 (2 min), 04-02 (2 min)
- Trend: Stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: 4 phases derived from requirement dependencies — Foundation, Chores, Time Bank, Automation
- [Roadmap]: Single Django app (core/) per research recommendation — all models cross-reference
- [Roadmap]: AdminLTE 4 with Bootstrap 5.3 fallback — validate integration in Phase 1
- [01-01]: AdminLTE 4 via CDN (rc7) — full control over version, better than pip package
- [01-01]: OverlayScrollbars included via CDN for AdminLTE 4 sidebar support
- [01-01]: AUTH_PASSWORD_VALIDATORS left empty — Plan 02 adds PinValidator
- [01-01]: Pastel palette: primary #7C9CBF, kid accent #B19CD9, background #FAF8FC
- [01-02]: PinAuthBackend is thin ModelBackend subclass — PINs use standard Django hashing
- [01-02]: Login page is standalone HTML (no sidebar) — card-picker UI pattern
- [01-02]: Role redirect uses URL paths (/parent/, /kid/) — named URLs come in Plan 03
- [01-03]: HomeRouterView at root URL dispatches by role — LOGIN_REDIRECT_URL is "/"
- [01-03]: bank_balance template tag returns placeholder "0 min" — real balance in Phase 3
- [01-03]: Kid home uses playful tone per CONTEXT.md guidelines
- [01-03]: Parent home card grid designed as Phase 4 dashboard foundation
- [02-01]: Django Q2 with ORM broker -- no Redis dependency needed for task scheduling
- [02-01]: django-q2 install upgraded Django 4.1 to 4.2 -- compatible, no issues
- [02-01]: _is_due_on guards custom recurrence with null-check on recurrence_interval
- [02-02]: ChoreForm conditional clean() -- bonus forces penalty=0, required demands penalty>0
- [02-02]: Weekday checkboxes sync to hidden recurrence_days field as comma-separated ints
- [02-02]: Logout button in base.html sidebar-wrapper, outside sidebar_nav block, shows on all pages
- [02-03]: canvas-confetti CDN for celebratory animation on chore completion
- [02-03]: Tomorrow label via view context var rather than custom template filter
- [02-03]: Pastel confetti colors matching app palette from 01-01
- [02-04]: Monthly recurrence has no sub-fields -- fires on same day-of-month as created_at
- [03-01]: Balance derived from SUM(amount) per kid, never stored as mutable field
- [03-01]: Color coding: green (>=15min), orange (<15min), red (<=0)
- [03-01]: EARN transaction created only when reward_minutes > 0
- [03-02]: Optimistic SPEND at timer start with ADJUST refund on early stop
- [03-02]: Stale sessions auto-closed on page load (no cron needed)
- [03-02]: Color thresholds at 25% (orange) and 10% (red) of total time
- [03-02]: Web Audio API alarm at 880Hz for timer expiry notification
- [03-03]: Load More button self-replaces via hx-target outerHTML for seamless HTMX pagination
- [03-03]: Kid balance cards above adjustment form for parent context
- [03-03]: Preset buttons use data attributes and vanilla JS
- [04-01]: No date filtering on due_date in process_penalties -- processes ALL overdue for catch-up resilience
- [04-01]: select_for_update inside transaction.atomic prevents race conditions between workers
- [04-02]: Bulk queries for transactions and chore counts avoid N+1 on dashboard
- [04-02]: Missed chore detection based on date/completion status, independent of penalty_applied flag

### Pending Todos

None

### Blockers/Concerns

- AdminLTE 4 integration VALIDATED in 01-01 — CDN approach works, sidebar renders correctly
- Railway cron service cost — verify pricing for two cron services; consolidate if needed
- Timer pause/resume IMPLEMENTED in quick-001 -- paused_at/paused_seconds pattern

## Session Continuity

Last session: 2026-04-03
Stopped at: Completed quick-002-PLAN.md (fix kid chore Done button)
Resume file: None
