---
phase: quick-015
plan: 01
subsystem: customization-unlockables
tags: [achievements, unlockables, sounds, animations, patterns, settings]
requires: [quick-014]
provides: [expanded-unlockable-system, locked-customization-ui, server-lock-enforcement]
affects: []
tech-stack:
  added: []
  patterns: [achievement-gated-customization, server-side-lock-enforcement]
key-files:
  created:
    - core/migrations/0014_expand_unlockables.py
  modified:
    - core/models.py
    - core/achievements.py
    - core/views.py
    - templates/core/kid_settings.html
    - templates/core/kid_chore_list.html
    - templates/base.html
decisions:
  - First 6 animal emojis are free; remaining 30 emojis gated by 5 group achievements
  - Chime sound and confetti animation are the free starter options
  - Gradient, dark mode, and sidebar color are feature-level unlocks
  - Server-side POST enforcement silently rejects locked values (falls back to free default)
metrics:
  duration: 8 min
  completed: 2026-04-08
---

# Quick-015: Expand Unlockables and Lock Customization Summary

**One-liner:** All customization options gated behind 34 achievement milestones with lock UI and server-side enforcement across sounds, animations, emojis, patterns, fonts, gradient, dark mode, and sidebar color.

## What Was Done

### Task 1: New model choices, achievement definitions, and migration
- Added 5 new SoundPreference entries: laser, powerup, levelup, applause, drumroll
- Added 4 new AnimationPreference entries: bubbles, rainbow, sparkle, snow
- Added 3 new BgPattern entries: checkerboard, zigzag, diamonds
- Added 26 new unlockable achievement definitions across 6 sub-categories: 8 sounds, 7 animations, 5 emoji groups, 3 features, 3 patterns
- Total unlockable achievements: 34 (was 8), total achievements: 79
- Migration 0014 applies schema changes and seeds achievements
- Commit: 6105e6f

### Task 2: Views, settings UI, and chore completion JS
- Expanded `_get_unlocked()` to return dict covering all 6 categories
- Added server-side POST enforcement for sounds, animations, emojis, gradient, dark mode, sidebar color
- Updated settings page with lock icons + unlock criteria text on all gated items
- Added 5 new Web Audio sound functions (laser, powerup, levelup, applause, drumroll) to both kid_settings.html and kid_chore_list.html
- Added 4 new canvas-confetti animation functions (bubbles, rainbow, sparkle, snow) to both pages
- Added 3 new pattern CSS swatches to settings page and 3 new pattern backgrounds to base.html
- Commit: c257735

## Deviations from Plan

None - plan executed exactly as written.

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 6105e6f | Add new model choices and 26 unlockable achievement definitions |
| 2 | c257735 | Lock all customization behind achievement unlocks with full UI and server enforcement |

## Self-Check: PASSED
