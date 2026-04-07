---
phase: quick
plan: 003
type: execute
wave: 1
depends_on: []
files_modified: [templates/core/timer.html]
autonomous: true

must_haves:
  truths:
    - "Kid sees a 'Use All' button on the timer setup page when they have a positive balance"
    - "Clicking 'Use All' fills the minutes input with the kid's full balance and enables the Start button"
    - "The 'Use All' button visually stands out from the duration presets as the primary action"
  artifacts:
    - path: "templates/core/timer.html"
      provides: "Use All button in timer setup"
      contains: "Use All"
  key_links:
    - from: "Use All button onclick"
      to: "setMinutes()"
      via: "onclick handler passing balance value"
      pattern: "setMinutes.*balance"
---

<objective>
Add a "Use All" button to the kid timer page that starts a session using the kid's entire bank balance, without requiring manual duration selection.

Purpose: Kids often want to just use all their earned time. Currently they must type or pick a preset. One button removes that friction.
Output: Updated timer.html with a "Use All" button.
</objective>

<execution_context>
@/Users/ike/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ike/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@templates/core/timer.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add "Use All" button to timer template</name>
  <files>templates/core/timer.html</files>
  <action>
In `templates/core/timer.html`, add a "Use All" button in the presets area (line ~38-54, the `#presets` div). Place it AFTER the existing preset buttons as a distinct, prominent option.

Implementation details:
- Add a button that calls `setMinutes({{ balance }})` on click
- Style it as `btn-success` (green, matching the Start button theme) and `btn-lg` to distinguish it from the `btn-outline-primary` preset buttons
- Button text: "Use All ({{ balance_display }})" so the kid sees exactly how much time they're using
- The button should always appear when balance > 0 (it's inside the existing `{% else %}` block that already guards for positive balance)
- Add a small visual separator (e.g., a vertical pipe or slight margin) between the preset buttons and the Use All button so they read as two distinct groups

No backend changes needed. The existing `setMinutes()` JS function handles setting the input value and enabling the Start button. The existing `TimerStartView` validates balance server-side.
  </action>
  <verify>
Run the dev server (`python manage.py runserver`) and visit `/kid/timer/` as a kid user with positive balance. Confirm:
1. "Use All" button appears after preset buttons
2. Button shows the full balance in its label
3. Clicking it fills the minutes input with the full balance value
4. Start button becomes enabled after clicking Use All
5. Timer starts successfully using the full balance
  </verify>
  <done>
"Use All" button visible on timer page, fills input with full balance on click, timer can be started with full balance.
  </done>
</task>

</tasks>

<verification>
- Template renders without errors
- Button appears only when balance > 0 (same guard as other presets)
- Clicking "Use All" correctly populates the minutes input and enables Start
- Full flow works: Use All -> Start -> timer runs for full balance duration
</verification>

<success_criteria>
Kid can tap "Use All" and immediately start a timer for their entire balance without typing or picking a preset.
</success_criteria>

<output>
After completion, create `.planning/quick/003-timer-use-all-balance/003-SUMMARY.md`
</output>
