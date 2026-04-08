---
phase: quick-008
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - templates/base.html
  - core/middleware.py
  - chorebank/settings.py
  - core/views.py
autonomous: true
must_haves:
  truths:
    - "Parent dashboard 'chores done today' count reflects local date, not UTC date"
    - "Parent dashboard 'This week' count uses local Monday-through-today boundary"
    - "Activity timestamps on parent dashboard display in local time"
    - "At 8pm EST, chore counts still show correctly for the current local day"
  artifacts:
    - path: "core/middleware.py"
      provides: "TimezoneMiddleware that activates Django timezone from browser cookie"
    - path: "templates/base.html"
      provides: "JS that sets browser_tz cookie with IANA timezone"
  key_links:
    - from: "templates/base.html"
      to: "core/middleware.py"
      via: "browser_tz cookie"
      pattern: "browser_tz"
    - from: "core/middleware.py"
      to: "core/views.py"
      via: "django.utils.timezone.activate"
      pattern: "timezone.activate"
---

<objective>
Fix parent dashboard UTC timezone issues: "chores done today" count resets at UTC midnight
instead of local midnight, and activity timestamps display in UTC. Add a timezone middleware
that reads the browser timezone from a cookie (set via JS) and activates it for each request,
so Django's `localdate()` returns the correct local date.

Purpose: Parents in EST see chore counts reset at 8pm (UTC midnight) which is confusing and wrong.
Output: Timezone-aware dashboard that respects browser local time for all date boundaries and display.
</objective>

<execution_context>
@/Users/ike/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ike/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@templates/base.html
@core/views.py (ParentHomeView around line 211-290)
@chorebank/settings.py (MIDDLEWARE list around line 50, TIME_ZONE at line 114)
@core/middleware.py (may not exist yet)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add timezone cookie JS and Django TimezoneMiddleware</name>
  <files>
    templates/base.html
    core/middleware.py
    chorebank/settings.py
  </files>
  <action>
1. In `templates/base.html`, add a small JS snippet (before the existing timezone conversion script) that sets a `browser_tz` cookie with the IANA timezone name from `Intl.DateTimeFormat().resolvedOptions().timeZone`. Set cookie with `path=/; max-age=31536000; SameSite=Lax`. Only set if not already matching to avoid unnecessary writes. Example:
   ```js
   (function() {
       var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
       if (tz && document.cookie.indexOf('browser_tz=' + tz) === -1) {
           document.cookie = 'browser_tz=' + tz + '; path=/; max-age=31536000; SameSite=Lax';
       }
   })();
   ```

2. Create `core/middleware.py` with a `TimezoneMiddleware` class:
   - Read `browser_tz` cookie from `request.COOKIES`
   - Validate it with `zoneinfo.ZoneInfo(tz_name)` (catch exceptions for invalid values)
   - Call `django.utils.timezone.activate(zoneinfo.ZoneInfo(tz_name))` if valid
   - Call `django.utils.timezone.deactivate()` in the response/finally (use `__call__` pattern)
   - Fallback: if no cookie or invalid, use `America/New_York` as default (family is EST)

3. In `chorebank/settings.py`, add `"core.middleware.TimezoneMiddleware"` to MIDDLEWARE list, after `AuthenticationMiddleware` (so request.user is available if needed later, and timezone is active for all views).
  </action>
  <verify>
    - `python manage.py check` passes with no errors
    - `grep -n "TimezoneMiddleware" chorebank/settings.py` shows it in MIDDLEWARE
    - `grep -n "browser_tz" templates/base.html` shows cookie-setting JS
    - `python -c "from core.middleware import TimezoneMiddleware; print('OK')"` imports without error
  </verify>
  <done>
    TimezoneMiddleware reads browser_tz cookie and activates Django timezone per-request. JS in base.html sets the cookie on every page load. Django's `localdate()` and `localtime()` now return browser-local values.
  </done>
</task>

<task type="auto">
  <name>Task 2: Add local-time display to parent dashboard activity timestamps</name>
  <files>
    templates/core/parent_home.html
  </files>
  <action>
With the middleware in place, `localdate()` in ParentHomeView already returns the correct local date for "today" and "this week" boundaries -- no view changes needed for chore counts.

For activity timestamps: the parent_home.html template currently shows no timestamps for recent transactions (only type + note + amount). The `timesince` filter IS used for time_requests (line 20: `{{ req.created_at|timesince }} ago`). 

1. For the time_requests section (line 20), the `timesince` filter is timezone-aware when Django timezone is activated, so this should already work correctly with the middleware. No change needed.

2. For recent transactions (lines 78-107), there are currently NO timestamps shown. Add a small timestamp to each transaction row showing when it occurred. After the amount div (around line 103), add:
   ```html
   <small class="text-muted d-block text-end" style="font-size: 0.7rem;">
       {{ txn.created_at|date:"M j, g:i A" }}
   </small>
   ```
   Django's `date` filter respects the activated timezone, so this will display in local time.

Note: The `localdate()` call on line 218 of views.py does NOT need modification -- once the TimezoneMiddleware activates the browser timezone, `localdate()` automatically returns the date in that timezone. This is Django's built-in behavior.
  </action>
  <verify>
    - Run dev server: `python manage.py runserver`
    - Visit parent dashboard, confirm chore counts show correctly for local date
    - Confirm recent activity transactions show timestamps in local time format
    - Verify that at late evening hours, "today" boundary is still correct (not UTC midnight)
  </verify>
  <done>
    Parent dashboard chore counts ("X/Y chores done today", "This week") use local date boundaries. Recent activity transactions display timestamps in the browser's local timezone. The `timesince` display for time requests also respects local timezone.
  </done>
</task>

</tasks>

<verification>
1. `python manage.py check` -- no Django errors
2. Parent dashboard loads without errors
3. Chore counts reflect local date, not UTC date
4. Transaction timestamps display in local time
5. Cookie `browser_tz` is set in browser after first page load
</verification>

<success_criteria>
- Parent at 8pm EST sees correct "today" chore counts (not reset to 0)
- Weekly chore counts use local Monday boundary
- Recent activity shows timestamps like "Apr 7, 3:45 PM" in local time
- TimezoneMiddleware activates correct timezone for every request
</success_criteria>

<output>
After completion, create `.planning/quick/008-fix-parent-dashboard-utc-timezone/008-SUMMARY.md`
</output>
