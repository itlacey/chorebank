---
phase: quick
plan: 006
subsystem: kid-experience
tags: [web-audio, canvas-confetti, user-preferences, personalization]
dependency-graph:
  requires: [quick-001]
  provides: [kid-personalized-celebrations]
  affects: []
tech-stack:
  added: []
  patterns: [web-audio-oscillator-dispatch, canvas-confetti-shape-variants]
key-files:
  created:
    - core/migrations/0010_user_animation_preference_user_sound_preference.py
    - templates/core/kid_settings.html
  modified:
    - core/models.py
    - core/views.py
    - core/urls.py
    - templates/base_kid.html
    - templates/core/kid_chore_list.html
decisions:
  - "Sound options via Web Audio oscillator patterns (no audio files): chime, fanfare, coin, xylophone"
  - "Animation options via canvas-confetti shapes: confetti, fireworks, stars, hearts"
  - "Hearts use confetti.shapeFromText emoji approach since heart is not a built-in shape"
  - "Preferences stored as CharField with TextChoices on User model, defaults preserve existing behavior"
metrics:
  duration: 2 min
  completed: 2026-04-07
---

# Quick 006: Kid Personalized Sounds & Animations Summary

Personalized celebration preferences for kids -- choose sound (chime/fanfare/coin/xylophone) and animation (confetti/fireworks/stars/hearts) for chore completion, with live preview on a new settings page.

## Task Commits

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Add preference fields and migration | 0c1e60f | User model: sound_preference + animation_preference fields |
| 2 | Kid settings page with previews | cec6f65 | KidSettingsView, kid_settings.html, nav link |
| 3 | Wire chore completion to preferences | 8bb6186 | Dynamic sound/animation dispatch in kid_chore_list.html |

## What Was Built

1. **User Model Fields**: `sound_preference` (chime/fanfare/coin/xylophone) and `animation_preference` (confetti/fireworks/stars/hearts) with sensible defaults so existing users are unaffected.

2. **Kid Settings Page** (`/kid/settings/`): Two-column layout with radio buttons and "Preview" buttons for each option. Sounds use Web Audio API oscillator patterns; animations use canvas-confetti library. Save button persists choices via POST.

3. **Dynamic Chore Completion**: `kid_chore_list.html` now reads the user's preferences via Django template variables and dispatches to the appropriate sound/animation function instead of hardcoded chime + confetti.

4. **Navigation**: Settings gear icon added to kid sidebar nav.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| TextChoices on User model | Simple, no extra tables, migrates cleanly |
| Web Audio oscillator patterns | No audio files to host/load, instant playback |
| Hearts via shapeFromText | canvas-confetti has no built-in heart shape |
| Identical JS functions on both pages | Previews match real chore completion exactly |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification

- [x] `python manage.py test` -- no failures (0 tests exist but system check passes)
- [x] `python manage.py makemigrations --check` -- no pending migrations
- [x] URL `/kid/settings/` resolves correctly
- [x] Default preferences (chime + confetti) preserved for existing users

## Self-Check: PASSED
