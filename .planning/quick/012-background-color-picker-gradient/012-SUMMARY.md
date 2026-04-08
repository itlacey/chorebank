---
phase: quick-012
plan: 01
subsystem: personalization
tags: [color-picker, gradient, background, kid-settings, css]
dependency-graph:
  requires: [quick-010]
  provides: [kid-background-color-customization]
  affects: []
tech-stack:
  added: []
  patterns: [inline-style-injection, hex-validation]
key-files:
  created:
    - core/migrations/0011_user_bg_color_fields.py
  modified:
    - core/models.py
    - core/views.py
    - templates/core/kid_settings.html
    - templates/base.html
    - static/css/chorebank.css
decisions:
  - "Background color stored as hex string fields on User model (bg_color_1, bg_color_2, bg_use_gradient)"
  - "Empty bg_color_1 means use default theme background (#FAF8FC)"
  - "Dynamic style tag injected in base.html body for all pages"
metrics:
  duration: 4 min
  completed: 2026-04-08
---

# Quick-012: Background Color Picker & Gradient Summary

Kid background color customization with solid color picker and two-color gradient option, applied across all kid pages via base.html inline style injection.

## Task Commits

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Add background color fields to User model | 45acae7 | bg_color_1, bg_color_2, bg_use_gradient fields + migration 0011 |
| 2 | Add color picker UI and wire view + base template | 9c4b0f0 | Color picker card, JS preview, hex validation, base.html style injection |

## What Was Built

1. **User model fields**: `bg_color_1`, `bg_color_2` (CharField max_length=7), `bg_use_gradient` (BooleanField) for storing background color preferences per kid.

2. **Color picker UI**: New card on kid settings page between avatar and sound/animation sections. Includes:
   - Native HTML color input for primary color
   - Gradient toggle switch to enable two-color mode
   - Second color picker (shown/hidden by toggle)
   - Live preview swatch showing solid or gradient
   - Reset to Default button

3. **Dynamic background**: Inline `<style>` tag in base.html applies the kid's chosen color (solid or gradient with `background-attachment: fixed`) to `body` and `.app-main`. Only renders when user is authenticated and has a custom color set.

4. **Server-side validation**: Hex color regex validation (`^#[0-9A-Fa-f]{6}$`) in KidSettingsView POST handler. Invalid colors reset to empty string. Gradient disabled if second color is missing.

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Hex string fields (not ColorField) | No extra dependency; 7-char hex is simple and sufficient |
| Inline style in base.html body | Applies to all pages without modifying every template; overrides CSS variable with !important |
| Empty string = default theme | No need for sentinel value; falsy check in template is clean |

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED
