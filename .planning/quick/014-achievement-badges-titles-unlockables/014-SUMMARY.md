---
phase: quick
plan: 014
subsystem: gamification
tags: [achievements, badges, titles, unlockables, gamification]
requires: [quick-013]
provides: [achievement-system, badge-gallery, locked-patterns-fonts]
affects: []
tech-stack:
  added: []
  patterns: [achievement-checking-on-action, lazy-stat-computation, unlock-gating]
key-files:
  created:
    - core/achievements.py
    - core/migrations/0013_achievement_system.py
    - templates/core/kid_badges.html
  modified:
    - core/models.py
    - core/views.py
    - core/urls.py
    - templates/base_kid.html
    - templates/core/kid_settings.html
decisions:
  - 53 achievements across 8 categories (plan estimated 54, actual count is 53)
  - Lazy stat computation -- only queries DB for stat categories with unearned achievements
  - Unlock criteria text hardcoded in templates for simplicity over dict lookup
metrics:
  duration: 6 min
  completed: 2026-04-08
---

# Quick 014: Achievement Badges, Titles, and Unlockables Summary

**53 achievements across 8 categories with badge gallery, active badge/title selection, and pattern/font unlock gating**

## Task Commits

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Achievement models, migration, and seed data | ade5422 | Achievement + UserAchievement models, 53 seeded achievements, check_achievements logic, active_badge/active_title on User |
| 2 | Wire checking + badge gallery + locked settings | 8f52a66 | check_achievements on chore/timer, KidBadgesView, badge gallery template, locked patterns/fonts in settings |

## What Was Built

### Achievement System (core/achievements.py)
- 53 achievement definitions across 8 categories: Streaks (10), Chore Count (8), Time Earned (8), Time Used (5), Bonus (5), Speed (4), Variety (5), Unlockable (8)
- `seed_achievements()` -- idempotent seeding via update_or_create
- `check_achievements(user)` -- lazy stat computation, only queries stats for unearned categories
- Handles complex criteria: perfect_week, weekend_warrior, comeback, timer_long_session

### Models (core/models.py)
- Achievement: slug, emoji, title, description, category, criteria_type, criteria_value
- UserAchievement: user FK, achievement FK, earned_at (unique_together)
- User: active_badge FK, active_title FK (both nullable)

### Badge Gallery (/kid/badges/)
- Shows all 53 badges grouped by category
- Earned badges: colorful with gradient background, "Set Badge" and "Set Title" buttons
- Unearned badges: greyed out (opacity 0.45, grayscale filter) with description of unlock criteria
- Progress bar showing earned/total count
- Active badge/title display at top with clear buttons

### Locked Settings (kid_settings.html)
- Patterns (Stars, Polka, Stripes, Waves) locked until achievement earned
- Fonts (Rounded, Handwritten, Pixel, Comic) locked until achievement earned
- Lock icon + human-readable unlock criteria on locked options
- Check icon on unlocked options
- Server-side enforcement: POST handler forces locked values back to defaults

### Integration
- check_achievements() called in CompleteChoreView.post() and TimerStopView.post()
- "Badges" nav item in kid sidebar between History and Settings

## Deviations from Plan

### Minor Count Difference
- Plan stated 54 achievements, actual definitions total 53 (10+8+8+5+5+4+5+8=53). The plan's arithmetic was slightly off. All listed achievements are present.

## Self-Check: PASSED
