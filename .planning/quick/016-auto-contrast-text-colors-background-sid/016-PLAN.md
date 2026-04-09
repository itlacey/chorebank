---
phase: quick-016
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/templatetags/core_tags.py
  - templates/base.html
autonomous: true

must_haves:
  truths:
    - "Light sidebar color shows dark text on sidebar links and brand"
    - "Dark sidebar color shows light text on sidebar links and brand"
    - "Light background color shows dark text on page content"
    - "Dark background color shows light text on page content"
  artifacts:
    - path: "core/templatetags/core_tags.py"
      provides: "contrast_text_color template filter"
      contains: "contrast_text_color"
    - path: "templates/base.html"
      provides: "Dynamic text colors based on luminance"
      contains: "contrast_text_color"
  key_links:
    - from: "templates/base.html"
      to: "core/templatetags/core_tags.py"
      via: "template filter"
      pattern: "contrast_text_color"
---

<objective>
Add automatic contrast detection so text is always readable against user-chosen background and sidebar colors.

Purpose: When kids pick light backgrounds or light sidebar colors, text becomes unreadable because it stays light. This adds luminance-based contrast switching.
Output: A template filter that calculates relative luminance (WCAG formula) from a hex color and returns appropriate contrasting text color. Applied to both sidebar and body content styles in base.html.
</objective>

<execution_context>
@/Users/ike/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ike/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/templatetags/core_tags.py
@templates/base.html
@core/models.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add contrast_text_color template filter</name>
  <files>core/templatetags/core_tags.py</files>
  <action>
Add a `contrast_text_color` template filter to core_tags.py that:

1. Takes a hex color string (e.g., "#FF5733" or "FF5733") as input
2. Parses RGB components from the hex string
3. Calculates relative luminance using the WCAG 2.0 formula:
   - Convert each sRGB channel to linear: if c <= 0.03928 then c/12.92 else ((c+0.055)/1.055)^2.4
   - L = 0.2126*R + 0.7152*G + 0.0722*B
4. Returns dark text color for light backgrounds (L > 0.179) and light text color for dark backgrounds (L <= 0.179)
5. The filter should accept an optional argument for the "mode":
   - Default / "text": returns "#1a1a1a" for light bg, "#f0f0f0" for dark bg (general text)
   - "sidebar-link": returns "rgba(0,0,0,0.7)" for light bg, "rgba(255,255,255,0.85)" for dark bg
   - "sidebar-link-hover": returns "rgba(0,0,0,0.9)" for light bg, "#fff" for dark bg
   - "sidebar-hover-bg": returns "rgba(0,0,0,0.1)" for light bg, "rgba(255,255,255,0.15)" for dark bg
   - "sidebar-brand": returns "#222" for light bg, "#fff" for dark bg
   - "sidebar-btn": returns "rgba(0,0,0,0.6)" for light bg, "rgba(255,255,255,0.8)" for dark bg
   - "sidebar-btn-border": returns "rgba(0,0,0,0.2)" for light bg, "rgba(255,255,255,0.3)" for dark bg

Handle edge cases: empty string input returns empty string, malformed hex returns empty string (fail gracefully).

Use `@register.filter` so it can be used as `{{ color|contrast_text_color:"mode" }}`.
  </action>
  <verify>Open Django shell: `python manage.py shell -c "from core.templatetags.core_tags import contrast_text_color; print(contrast_text_color('#FFFFFF')); print(contrast_text_color('#000000')); print(contrast_text_color('#FF5733', 'sidebar-link'))"` -- should return dark text for white, light text for black.</verify>
  <done>Filter correctly returns dark text colors for light inputs and light text colors for dark inputs across all modes.</done>
</task>

<task type="auto">
  <name>Task 2: Apply contrast filter to base.html sidebar and background styles</name>
  <files>templates/base.html</files>
  <action>
Modify templates/base.html to use the new contrast filter. The `{% load core_tags %}` tag is likely already present; if not, add it at the top after `{% load static django_htmx %}`.

1. **Sidebar section** (around line 93-117): Replace the hardcoded white/light text colors in the `{% if user.sidebar_color %}` style block. Change from hardcoded `rgba(255,255,255,0.85)` etc. to use the filter:

```html
{% if user.is_authenticated and user.sidebar_color %}
<style>
  .app-sidebar {
    background-color: {{ user.sidebar_color }} !important;
  }
  .app-sidebar .nav-link {
    color: {{ user.sidebar_color|contrast_text_color:"sidebar-link" }} !important;
  }
  .app-sidebar .nav-link:hover,
  .app-sidebar .nav-link.active {
    color: {{ user.sidebar_color|contrast_text_color:"sidebar-link-hover" }} !important;
    background: {{ user.sidebar_color|contrast_text_color:"sidebar-hover-bg" }} !important;
  }
  .app-sidebar .sidebar-brand .brand-text {
    color: {{ user.sidebar_color|contrast_text_color:"sidebar-brand" }} !important;
  }
  .app-sidebar .btn-outline-secondary {
    color: {{ user.sidebar_color|contrast_text_color:"sidebar-btn" }} !important;
    border-color: {{ user.sidebar_color|contrast_text_color:"sidebar-btn-border" }} !important;
  }
  .app-sidebar .btn-outline-secondary:hover {
    background: {{ user.sidebar_color|contrast_text_color:"sidebar-hover-bg" }} !important;
    color: {{ user.sidebar_color|contrast_text_color:"sidebar-link-hover" }} !important;
  }
</style>
{% endif %}
```

2. **Background/body text section** (around line 40-91): After the existing bg_color style block (the one setting `background-color` or `background` gradient), add a rule for body text color. Insert inside the same `{% if user.bg_color_1 %}` block:

```html
  body, .app-main, .content-wrapper {
    color: {{ user.bg_color_1|contrast_text_color }} !important;
  }
```

However, do NOT apply this to `.card` elements -- cards have their own white/dark backgrounds from Bootstrap and should keep default text color. The contrast should only affect text that sits directly on the custom background (headers outside cards, breadcrumbs, etc.). If most content is inside cards, this might not be needed at all -- check the templates. If the main content is all inside cards, skip the body text color change and only do the sidebar fix. Use your judgment based on what you see in the actual templates.
  </action>
  <verify>Run `python manage.py runserver` and test with:
1. A kid account with a light sidebar color (e.g., #F5E6CA or #FFEB3B) -- sidebar text should be dark
2. Same kid with a dark sidebar color (e.g., #1B2838 or #4A0E4E) -- sidebar text should be white/light
3. Verify the app still renders correctly with no sidebar color set (default behavior unchanged)</verify>
  <done>Sidebar text automatically contrasts against the chosen sidebar color. Light sidebar = dark text, dark sidebar = light text. Default (no color set) behavior unchanged.</done>
</task>

</tasks>

<verification>
- Set sidebar_color to a light pastel (e.g., #F5E6CA) via kid settings -- sidebar links should appear dark
- Set sidebar_color to a dark color (e.g., #2C1810) -- sidebar links should appear light/white
- Set sidebar_color to empty -- default styling from chorebank.css applies
- Set bg_color_1 to a dark color -- verify cards are still readable
- No Python errors in template rendering
</verification>

<success_criteria>
- Text on sidebar is always readable regardless of sidebar color choice
- Text on background is always readable regardless of background color choice
- Default behavior (no custom colors) is completely unchanged
- No hardcoded white text assumptions remain in the sidebar color block
</success_criteria>

<output>
After completion, create `.planning/quick/016-auto-contrast-text-colors-background-sid/016-SUMMARY.md`
</output>
