---
phase: quick
plan: 007
type: execute
wave: 1
depends_on: []
files_modified:
  - templates/core/_chore_log_rows.html
  - templates/core/_transaction_rows.html
  - templates/base.html
autonomous: true

must_haves:
  truths:
    - "All timestamps across the app display in the user's local timezone, not UTC"
    - "Times update correctly for any browser timezone"
    - "HTMX 'Load More' rows also get timezone-converted times"
  artifacts:
    - path: "templates/core/_chore_log_rows.html"
      provides: "UTC ISO timestamps in data attributes for client-side conversion"
    - path: "templates/core/_transaction_rows.html"
      provides: "UTC ISO timestamps in data attributes for client-side conversion"
    - path: "templates/base.html"
      provides: "Global JS that converts UTC timestamps to local time on page load and after HTMX swaps"
  key_links:
    - from: "templates/base.html"
      to: "templates/core/_chore_log_rows.html, templates/core/_transaction_rows.html"
      via: "JS reads data-utc attribute and writes formatted local time"
      pattern: "data-utc"
---

<objective>
Fix timestamp display across the app so times show in the user's local timezone instead of UTC.

Affected pages:
1. /parent/chores/log/ — completed_at times (g:i A format)
2. /parent/bank/history/ — created_at times (M j, g:i A format)

Approach: Add `data-utc` attributes with ISO timestamps to both row templates. Add global JS in base.html that converts all `.local-time[data-utc]` elements to local time. This runs on DOMContentLoaded and after every htmx:afterSwap, covering Load More rows automatically.
</objective>

<execution_context>
@/Users/ike/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ike/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@templates/core/_chore_log_rows.html
@templates/core/_transaction_rows.html
@templates/core/chore_log.html
@templates/core/transaction_history.html
@templates/base.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add data-utc attributes to timestamp cells in row templates</name>
  <files>
    templates/core/_chore_log_rows.html
    templates/core/_transaction_rows.html
  </files>
  <action>
In `_chore_log_rows.html`:
- Change line 18 from `{{ inst.completed_at|date:"g:i A" }}` to:
  `<span class="local-time" data-utc="{{ inst.completed_at|date:'c' }}">{{ inst.completed_at|date:"g:i A" }}</span>`
- The fallback text ensures the page works if JS is disabled (stays UTC).

In `_transaction_rows.html`:
- Change line 20 from `{{ txn.created_at|date:"M j, g:i A" }}` to:
  `<span class="local-time" data-utc="{{ txn.created_at|date:'c' }}" data-format="long">{{ txn.created_at|date:"M j, g:i A" }}</span>`
- The `data-format="long"` attribute tells the JS to include the date portion (M j) in the formatted output.

Do NOT modify views.py or models.py.
  </action>
  <verify>
View page source of both pages — `data-utc` attributes should contain ISO timestamps.
  </verify>
  <done>
- Both row templates have data-utc attributes on timestamp elements
- Fallback UTC display preserved for no-JS
  </done>
</task>

<task type="auto">
  <name>Task 2: Add global timezone conversion JS to base.html</name>
  <files>
    templates/base.html
  </files>
  <action>
In `base.html`, add a script block BEFORE the `{% block extra_js %}` line (around line 141) that:

1. Defines a `convertTimesToLocal()` function that:
   - Selects all `.local-time[data-utc]` elements
   - For each element, parses the `data-utc` value as a Date
   - If element has `data-format="long"`, format with: `{ month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true }`
   - Otherwise (short format), format with: `{ hour: 'numeric', minute: '2-digit', hour12: true }`
   - Uses `new Intl.DateTimeFormat(undefined, options).format(date)` for locale-aware output
   - Sets element's textContent to the formatted string

2. Calls `convertTimesToLocal()` on DOMContentLoaded

3. Listens for `htmx:afterSwap` on document.body to call `convertTimesToLocal()` again, so Load More rows also get converted.

This goes in base.html so it applies to ALL pages with .local-time elements — current and future.

Do NOT modify any other files in this task.
  </action>
  <verify>
1. Visit /parent/chores/log/ — times should be in local timezone
2. Visit /parent/bank/history/ — times should be in local timezone with date
3. Click "Load More" on either page — new rows should also have local times
4. No JS console errors
  </verify>
  <done>
- Global timezone conversion JS in base.html
- Works on initial load and HTMX swaps
- Two format modes: short (time only) and long (date + time)
  </done>
</task>

</tasks>

<verification>
1. Both pages render without JS errors
2. Chore log times display in local timezone (time only)
3. Transaction history times display in local timezone (date + time)
4. "Load More" works on both pages with local times
5. Pages still render acceptably with JS disabled (UTC fallback)
</verification>

<success_criteria>
- All timestamp displays across the app show in user's local browser timezone
- Works for initial page load and HTMX-loaded additional rows
- No backend changes needed
- Zero new dependencies
- Single global JS solution, not per-page duplication
</success_criteria>

<output>
After completion, create `.planning/quick/007-fix-chore-log-timezone-from-browser/007-SUMMARY.md`
</output>
