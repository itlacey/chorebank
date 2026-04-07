---
phase: quick
plan: 003
subsystem: timer
tags: [ui, timer, kid-experience]

dependency-graph:
  requires: [03-02]
  provides: ["Use All button on timer page"]
  affects: []

tech-stack:
  added: []
  patterns: ["reuse existing setMinutes() JS for new UI entry point"]

key-files:
  created: []
  modified: [templates/core/timer.html]

decisions:
  - id: quick-003-1
    description: "btn-success + btn-lg styling with lightning icon distinguishes Use All from outline presets"
    reason: "Visual hierarchy -- Use All is primary action, presets are secondary"

metrics:
  duration: "1 min"
  completed: "2026-04-06"
---

# Quick 003: Use All Button on Timer Page Summary

**One-liner:** Green "Use All" button in timer presets area fills minutes input with kid's full balance via existing setMinutes() function.

## What Was Done

### Task 1: Add "Use All" button to timer template
**Commit:** `d87b9d5` -- `feat(quick-003): add Use All button to kid timer page`

Added a prominent green button after the preset duration buttons in the timer setup page:
- Button calls `setMinutes({{ balance }})` to populate the minutes input with full balance
- Label shows exact balance: "Use All (X min)" so kid knows what they're committing
- `btn-success btn-lg` styling (green, large) visually distinct from `btn-outline-primary` presets
- Lightning icon (`bi-lightning-fill`) adds visual punch
- Vertical pipe separator between presets and Use All for clear grouping
- No backend changes needed -- leverages existing `setMinutes()` JS and server-side validation

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add "Use All" button to timer template | d87b9d5 | templates/core/timer.html |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- Template parses without errors (confirmed via Django template engine)
- Button is inside the `{% else %}` block guarding balance > 0
- `setMinutes({{ balance }})` populates input and enables Start button
- Existing `TimerStartView` validates balance server-side

## Self-Check: PASSED
