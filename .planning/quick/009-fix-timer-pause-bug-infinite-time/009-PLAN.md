---
phase: quick-009
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/views.py
autonomous: true

must_haves:
  truths:
    - "Pausing and stopping a timer with partial minutes used does NOT refund those partial minutes"
    - "A kid using 3m50s of a 5m session gets back 1m (not 2m)"
    - "A kid using 0m30s of a 5m session gets back 4m (not 5m)"
  artifacts:
    - path: "core/views.py"
      provides: "Ceil-based used_minutes calculation in TimerStopView"
      contains: "math.ceil"
  key_links:
    - from: "core/views.py"
      to: "TimeBankTransaction"
      via: "refund calculation in TimerStopView.post"
      pattern: "math\\.ceil"
---

<objective>
Fix timer pause exploit where truncating partial minutes lets kids gain infinite screen time.

Purpose: Prevent kids from exploiting pause/stop to get refunded more time than they should.
Output: One-line fix in core/views.py using math.ceil instead of int() truncation.
</objective>

<execution_context>
@/Users/ike/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ike/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/views.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix truncation bug in TimerStopView refund calculation</name>
  <files>core/views.py</files>
  <action>
1. Add `import math` to the imports at the top of `core/views.py` (no existing math import).

2. In `TimerStopView.post()` at line 731, change:
   ```python
   used_minutes = int(used_seconds / 60)
   ```
   to:
   ```python
   used_minutes = math.ceil(used_seconds / 60)
   ```

This ensures partial minutes count as USED (rounded up), so kids cannot exploit pause/stop to get extra time refunded. For example:
- 3m50s used -> ceil(230/60) = ceil(3.83) = 4 minutes used -> refund 1m (was incorrectly 2m)
- 0m30s used -> ceil(30/60) = ceil(0.5) = 1 minute used -> refund 4m (was incorrectly 5m)

No other locations in the codebase have this truncation pattern -- the stale session auto-close path (line 601) does not refund time, so it is not affected.
  </action>
  <verify>
1. `python manage.py check` passes with no errors
2. `grep -n "math.ceil" core/views.py` shows the fix on the formerly-buggy line
3. `grep -n "import math" core/views.py` confirms the import exists
4. `grep -n "int(used_seconds" core/views.py` returns NO matches (old bug gone)
  </verify>
  <done>TimerStopView.post() uses math.ceil() for used_minutes calculation. Partial minutes are rounded UP so they count as used time, not refunded time. The infinite-time exploit is closed.</done>
</task>

</tasks>

<verification>
- `python manage.py check` passes
- No remaining `int(used_seconds` patterns in views.py
- `math.ceil` is used for the refund calculation
</verification>

<success_criteria>
- Partial minutes of screen time are rounded UP (counted as used)
- Kids can no longer exploit pause/stop to accumulate extra minutes
- No regressions in timer start/pause/resume/stop flow
</success_criteria>

<output>
After completion, create `.planning/quick/009-fix-timer-pause-bug-infinite-time/009-SUMMARY.md`
</output>
