---
phase: quick-009
plan: 01
subsystem: timer
tags: [bug-fix, timer, refund, math]
dependency-graph:
  requires: [03-02]
  provides: [correct-timer-refund-calculation]
  affects: []
tech-stack:
  added: []
  patterns: [ceil-based-time-rounding]
key-files:
  created: []
  modified: [core/views.py]
decisions:
  - id: q009-ceil
    summary: "Use math.ceil for used_minutes so partial minutes count as used"
metrics:
  duration: "24s"
  completed: "2026-04-07"
---

# Quick 009: Fix Timer Pause Bug (Infinite Time Exploit) Summary

**One-liner:** Replace int() truncation with math.ceil() in TimerStopView refund calculation to prevent partial-minute exploit.

## What Changed

The timer refund calculation in `TimerStopView.post()` used `int(used_seconds / 60)` which truncated partial minutes down. This meant a kid using 3m50s of a 5m session would be charged only 3 minutes (refunded 2m instead of 1m). By repeatedly pausing and stopping sessions, a kid could accumulate free minutes indefinitely.

**Fix:** Changed to `math.ceil(used_seconds / 60)` so partial minutes round UP and count as used time.

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Fix truncation bug in TimerStopView refund calculation | b3f0a86 | core/views.py |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- `python manage.py check` passes with no issues
- `math.ceil` confirmed at line 732 of core/views.py
- `import math` confirmed at line 30
- No remaining `int(used_seconds` patterns in codebase

## Self-Check: PASSED
