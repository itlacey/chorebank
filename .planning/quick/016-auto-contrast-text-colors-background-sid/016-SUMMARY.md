---
phase: quick-016
plan: 01
subsystem: ui-theming
tags: [contrast, accessibility, WCAG, luminance, template-filter]
dependency-graph:
  requires: [quick-012, quick-013]
  provides: [auto-contrast-text-colors]
  affects: []
tech-stack:
  added: []
  patterns: [WCAG-2.0-luminance, template-filter-contrast]
key-files:
  created: []
  modified:
    - core/templatetags/core_tags.py
    - templates/base.html
decisions:
  - id: q016-01
    decision: "Contrast applied to page headers on background but NOT card content"
    reason: "Cards have their own Bootstrap bg; only text sitting directly on custom background needs contrast"
metrics:
  duration: "2 min"
  completed: "2026-04-08"
---

# Quick-016: Auto Contrast Text Colors Summary

WCAG 2.0 luminance-based contrast filter for sidebar and background text readability.

## What Was Done

### Task 1: contrast_text_color template filter
- Added `contrast_text_color` filter to `core/templatetags/core_tags.py`
- Implements WCAG 2.0 relative luminance formula (sRGB linearization + weighted sum)
- Threshold at L=0.179 distinguishes light from dark backgrounds
- 7 modes for different UI elements: text, sidebar-link, sidebar-link-hover, sidebar-hover-bg, sidebar-brand, sidebar-btn, sidebar-btn-border
- Graceful fallback: empty/malformed hex returns empty string
- **Commit:** b14725c

### Task 2: Apply contrast filter to base.html
- Replaced all 6 hardcoded `rgba(255,255,255,...)` and `#fff` values in sidebar color block with dynamic `contrast_text_color` filter calls
- Added `{% load core_tags %}` to base.html
- Added contrast-aware text color for `.app-content-header` and page headers when custom background color is set
- Cards retain default Bootstrap text colors (unaffected by background contrast)
- **Commit:** f1bd0e1

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add contrast_text_color template filter | b14725c | core/templatetags/core_tags.py |
| 2 | Apply contrast filter to base.html | f1bd0e1 | templates/base.html |

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

1. **Page header contrast only (not full body text):** Applied contrast color to `.app-content-header` and direct child headings/paragraphs of content container, not to entire body. Since all main content lives inside Bootstrap cards with their own backgrounds, applying to body would be unnecessary and could interfere with card readability.

## Verification

- `contrast_text_color('#FFFFFF')` returns `#1a1a1a` (dark text for white bg)
- `contrast_text_color('#000000')` returns `#f0f0f0` (light text for black bg)
- `contrast_text_color('#FFEB3B', 'sidebar-link')` returns `rgba(0,0,0,0.7)` (dark for light yellow)
- Template renders correctly with light sidebar color producing dark text
- No hardcoded white text assumptions remain in sidebar color block
- Django system check passes with no issues

## Self-Check: PASSED
