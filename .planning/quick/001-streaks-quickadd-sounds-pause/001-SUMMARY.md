---
phase: quick-001
plan: 01
subsystem: kid-engagement-parent-efficiency
tags: [streaks, quick-add, web-audio, timer-pause, htmx]
requires: [phase-02, phase-03]
provides: [streak-tracking, template-quick-add, chore-sounds, timer-pause-resume]
affects: []
tech-stack:
  added: []
  patterns: [computed-streaks, web-audio-ding, collapsible-quick-add]
key-files:
  created:
    - core/migrations/0008_add_timer_pause_fields.py
  modified:
    - core/models.py
    - core/views.py
    - core/urls.py
    - core/templatetags/core_tags.py
    - templates/core/kid_home.html
    - templates/core/kid_chore_list.html
    - templates/core/chore_list.html
    - templates/core/timer.html
decisions:
  - "Streaks computed on-the-fly from last 30 days (no stored fields) -- simple and always accurate"
  - "Only required chores count for streaks -- bonus chores don't break them"
  - "Days with no required chores are skipped (don't break streak)"
  - "Timer pause uses paused_at timestamp + paused_seconds accumulator pattern"
  - "Quick-add uses standard POST redirect (no HTMX) -- simpler for parent workflow"
metrics:
  duration: 6 min
  completed: 2026-04-03
---

# Quick Task 001: Streaks, Quick-Add, Sounds, Pause Summary

**One-liner:** Computed chore streaks with fire emoji UI, template quick-add for parents, Web Audio completion ding, and timer pause/resume with accurate balance tracking.

## Task Commits

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Streak tracking computation | `5e24a97` | get_streak/get_longest_streak classmethods on ChoreInstance, streak in view contexts |
| 2 | Display streaks in kid UI | `58b54f8` | Streak badge on kid home, streak banner on chore list, CSS pulse for 7+ |
| 3 | Quick-add chores from templates | `4f553db` | QuickAddChoreView, collapsible template picker on parent chore list |
| 4 | Sound effects on completion | `7b98bbe` | Web Audio two-tone ding (C5+E5) synced with confetti |
| 5 | Pause/resume timer | `cb3ae3a` | paused_at/paused_seconds fields, Pause/Resume views, UI state handling |

## What Was Built

### Streaks (Tasks 1-2)
- `ChoreInstance.get_streak(kid)` computes consecutive days where all required chores are completed
- `ChoreInstance.get_longest_streak(kid)` tracks the best streak in 30 days
- Days with zero required chores are skipped (weekends with no chores don't break streaks)
- Kid home page shows streak badge with fire emoji, pulse animation at 7+ days
- Kid chore list shows streak banner at top

### Quick-Add (Task 3)
- Collapsible "Quick Add from Template" section on parent chore list
- Template cards show name, reward, and type badge
- Clicking a template reveals inline form with kid checkboxes and recurrence select
- POST creates chore with sensible defaults from template and generates instances

### Sounds (Task 4)
- Web Audio API two-tone ding: C5 (523Hz, 150ms) then E5 (659Hz, 200ms)
- AudioContext initialized on first click (browser autoplay policy)
- Plays before confetti on chore completion via existing `chore-completed` event

### Timer Pause (Task 5)
- `paused_at` (DateTimeField) and `paused_seconds` (PositiveIntegerField) on TimerSession
- `TimerPauseView`: sets paused_at, freezes JS timer
- `TimerResumeView`: accumulates pause duration, returns new end_time_ms
- `TimerStopView`: deducts paused_seconds from used time for accurate refund
- Stale session auto-close accounts for paused time
- UI: Pause button (yellow) swaps with Resume button (green), overlay turns muted blue (#D0D8E0)
- Paused state persists across page reloads

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

1. **Computed streaks, not stored** -- `get_streak()` queries last 30 days each time. Avoids migration complexity and stale data. Performance is fine (single query, 30-day window).
2. **Required chores only for streaks** -- Bonus chores are optional by definition; including them would make streaks trivially easy.
3. **Skip days with no required chores** -- A weekend with no assigned chores shouldn't penalize a kid's streak.
4. **Pause accumulator pattern** -- `paused_at` marks when pause started, `paused_seconds` accumulates total. Simple, handles multiple pause/resume cycles.
5. **Quick-add uses standard POST** -- No HTMX complexity needed; parent workflow is "pick template, submit, see result."

## Verification

- `python manage.py check` -- no issues
- `python manage.py makemigrations --check` -- no pending migrations
- `python manage.py test` -- no failures (0 tests exist)
- Streak computation returns correct integers via shell

## Self-Check: PASSED
