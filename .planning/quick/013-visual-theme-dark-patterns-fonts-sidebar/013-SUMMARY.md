---
phase: quick-013
plan: 01
subsystem: kid-personalization
tags: [dark-mode, css-patterns, google-fonts, sidebar-color, visual-theme]

dependency_graph:
  requires: [quick-012]
  provides: [dark-mode-toggle, bg-patterns, font-styles, sidebar-accent-color]
  affects: []

tech_stack:
  added: [Google Fonts (Varela Round, Patrick Hand, Silkscreen, Comic Neue)]
  patterns: [Bootstrap data-bs-theme dark mode, CSS-only background patterns, conditional CDN font loading]

key_files:
  created:
    - core/migrations/0012_user_visual_theme_fields.py
  modified:
    - core/models.py
    - core/views.py
    - templates/core/kid_settings.html
    - templates/base.html

decisions:
  - id: quick-013-dark
    description: "Use Bootstrap 5.3 native data-bs-theme='dark' for dark mode -- zero custom CSS needed"
  - id: quick-013-patterns
    description: "CSS-only patterns with dark-mode-aware colors (white rgba on dark, black rgba on light)"
  - id: quick-013-fonts
    description: "Conditionally load Google Fonts CDN per user preference to avoid loading unused fonts"

metrics:
  duration: 3 min
  completed: 2026-04-08
---

# Quick-013: Visual Theme - Dark Mode, Patterns, Fonts, Sidebar Color

Kid visual theme customization: dark mode toggle, CSS background patterns, Google Fonts style picker, and sidebar accent color -- all persisting via User model fields and applied globally through base.html.

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add model fields and migration | 16f7d64 | core/models.py, core/migrations/0012_user_visual_theme_fields.py |
| 2 | Add settings UI and view handling | 5e24fcd | core/views.py, templates/core/kid_settings.html |
| 3 | Apply theme in base template | 376ac50 | templates/base.html |

## What Was Built

**4 new User model fields:** `dark_mode` (BooleanField), `bg_pattern` (CharField with choices), `font_style` (CharField with choices), `sidebar_color` (CharField).

**Settings UI:** 4 new preference cards on kid settings page:
- Dark Mode: form switch toggle
- Background Pattern: radio buttons with CSS preview swatches (stars, polka dots, stripes, waves)
- Font Style: radio buttons rendered in their own font, with 3-second live preview button
- Sidebar Color: color picker with reset button and preview bar

**Global theme application in base.html:**
- Dark mode: `data-bs-theme="dark"` on `<html>` element (Bootstrap 5.3 native)
- Patterns: CSS `::before` pseudo-element overlay on `.app-main` with dark-mode-aware colors
- Fonts: conditional Google Fonts CDN link + body font-family override
- Sidebar: background-color override with white text contrast rules

## Decisions Made

1. **Bootstrap native dark mode** -- `data-bs-theme="dark"` handles all color inversions automatically with zero custom CSS
2. **Dark-mode-aware patterns** -- polka/stripes/waves use `rgba(255,255,255,...)` on dark backgrounds, `rgba(0,0,0,...)` on light
3. **Conditional font loading** -- only loads the selected Google Font (not all 4) to minimize page weight

## Deviations from Plan

None -- plan executed exactly as written.

## Self-Check: PASSED
