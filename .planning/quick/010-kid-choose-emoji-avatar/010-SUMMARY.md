---
phase: quick-010
plan: 01
subsystem: kid-ui
tags: [emoji, avatar, settings, kid-personalization]
dependency_graph:
  requires: [quick-006]
  provides: [emoji-avatar-picker-ui]
  affects: []
tech_stack:
  added: []
  patterns: [emoji-grid-picker, hidden-input-selection]
file_tracking:
  key_files:
    created: []
    modified:
      - core/views.py
      - templates/core/kid_settings.html
decisions:
  - id: "quick-010-01"
    description: "25 emojis in 5 categories (animals, faces, space/nature, sports/fun)"
    rationale: "Curated kid-friendly set, covers diverse interests, fits nicely in 6-col grid"
metrics:
  duration: "< 1 min"
  completed: "2026-04-08"
---

# Quick 010: Kid Choose Emoji Avatar Summary

**One-liner:** Emoji avatar picker grid on kid settings page with 25 kid-friendly options, keyboard accessible

## What Was Done

Added a "My Avatar" card to the kid settings page with a responsive grid of 25 curated emojis. Kids can click (or keyboard-navigate) to select an emoji, and it persists on save alongside existing sound/animation preferences.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add emoji avatar picker to kid settings | 7a81ce3 | core/views.py, templates/core/kid_settings.html |

## Changes Detail

### core/views.py
- Added `EMOJI_CHOICES` list with 25 emojis in 5 categories (animals, faces, space/nature, sports/fun)
- `KidSettingsView.get()` now passes `emoji_choices` and `current_emoji` to template context
- `KidSettingsView.post()` validates `emoji_avatar` against EMOJI_CHOICES before saving

### templates/core/kid_settings.html
- Added CSS for `.emoji-grid` (6-col desktop, 4-col mobile), `.emoji-option` with hover/selected states
- Added "My Avatar" card with full-width emoji grid above existing sound/animation cards
- Added `selectEmoji()` JS function and keyboard event listeners for accessibility

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | 25 emojis in 5 categories | Kid-friendly curation, fits 6-col grid layout evenly (4 rows + 1 partial) |

## Self-Check: PASSED
