---
phase: quick
plan: 017
subsystem: parent-analytics
tags: [analytics, completion-rates, reward-adjustment, parent-dashboard]
dependency_graph:
  requires: [02-chore-system, 04-automation-dashboard]
  provides: [chore-analytics-page, reward-suggestions]
  affects: []
tech_stack:
  added: []
  patterns: [bulk-aggregation-with-values-annotate]
key_files:
  created:
    - templates/core/chore_analytics.html
  modified:
    - core/views.py
    - core/urls.py
    - templates/base_parent.html
decisions:
  - id: q017-1
    description: "Completion rate thresholds: <30% danger, 30-60% warning, 60-85% success, >85% info"
    rationale: "Balanced thresholds that flag genuinely low-performing chores without over-alerting"
metrics:
  duration: "2 min"
  completed: "2026-04-18"
---

# Quick 017: Parent Chore Analytics & Reward Adjustment Summary

**One-liner:** Per-chore completion rate analytics with color-coded reward adjustment suggestions using bulk Django ORM aggregation.

## What Was Done

### Task 1: ChoreAnalyticsView with completion rate logic
- Added `ChoreAnalyticsView` (ParentRequiredMixin, TemplateView) to `core/views.py`
- Queries ChoreInstance records for last 30 days, grouped by chore + kid
- Computes total_instances, completed_count, completion_rate per combination
- Derives suggestion text and badge_class from rate thresholds
- Sorts by completion_rate ascending (worst performers first)
- Passes overall_completion_rate, needs_attention count, kid filter support
- Uses `.values().annotate()` bulk aggregation to avoid N+1

### Task 2: Analytics template and sidebar link
- Created `templates/core/chore_analytics.html` extending base_parent.html
- Kid filter dropdown at top with "All Kids" default
- Overall summary card with large percentage and color-coded progress bar
- Responsive table with chore name, kid, type badge, reward, completion rate bar, suggestion badge
- Empty state for no data in 30-day window
- Added "Analytics" sidebar link with bi-graph-up icon between "Chore Log" and "Settings"

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | ChoreAnalyticsView with completion rate logic | a42920c | core/views.py, core/urls.py |
| 2 | Analytics template and sidebar link | 8d6ea95 | templates/core/chore_analytics.html, templates/base_parent.html |

## Deviations from Plan

None -- plan executed exactly as written.

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| q017-1 | Completion rate thresholds: <30% danger, 30-60% warning, 60-85% success, >85% info | Balanced thresholds that flag genuinely low-performing chores without over-alerting |

## Self-Check: PASSED
