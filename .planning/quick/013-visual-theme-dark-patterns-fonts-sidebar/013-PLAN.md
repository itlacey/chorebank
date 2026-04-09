---
phase: quick-013
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/models.py
  - core/migrations/0012_user_visual_theme_fields.py
  - core/views.py
  - templates/core/kid_settings.html
  - templates/base.html
autonomous: true

must_haves:
  truths:
    - "Kid can toggle dark mode on/off from settings and it persists across pages"
    - "Kid can pick a background pattern (stars, polka dots, stripes, waves) that overlays on their chosen background color"
    - "Kid can pick from 4 fun font styles and see text change across the app"
    - "Kid can set a sidebar accent color independently from background color"
  artifacts:
    - path: "core/models.py"
      provides: "New User fields: dark_mode, bg_pattern, font_style, sidebar_color"
    - path: "core/migrations/0012_user_visual_theme_fields.py"
      provides: "Migration for 4 new fields"
    - path: "templates/core/kid_settings.html"
      provides: "UI controls for all 4 features"
    - path: "templates/base.html"
      provides: "Dynamic style injection for dark mode, patterns, fonts, sidebar color"
  key_links:
    - from: "templates/core/kid_settings.html"
      to: "core/views.py"
      via: "form POST fields"
      pattern: "dark_mode|bg_pattern|font_style|sidebar_color"
    - from: "templates/base.html"
      to: "user model fields"
      via: "template context"
      pattern: "user\\.dark_mode|user\\.bg_pattern|user\\.font_style|user\\.sidebar_color"
---

<objective>
Add 4 visual theme customization features to kid settings: dark mode toggle, background patterns, custom font style, and sidebar accent color. All persist via User model fields and apply globally through base.html dynamic styles.

Purpose: Kids love personalizing their space -- these features make ChoreBank feel like "theirs"
Output: 4 new model fields, migration, settings UI cards, dynamic style injection in base template
</objective>

<execution_context>
@/Users/ike/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ike/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/models.py (User model -- add fields after bg_use_gradient)
@core/views.py (KidSettingsView at line 967 -- add context + POST handling)
@templates/core/kid_settings.html (settings page -- add 4 new cards)
@templates/base.html (base template -- add dynamic style injection)
@templates/base_kid.html (sidebar structure for accent color targeting)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add model fields and migration</name>
  <files>core/models.py, core/migrations/0012_user_visual_theme_fields.py</files>
  <action>
Add 4 new fields to the User model in core/models.py, after the bg_use_gradient field:

1. Add TextChoices classes:

```python
class FontStyle(models.TextChoices):
    DEFAULT = "default", "Default (Nunito)"
    ROUNDED = "rounded", "Rounded (Varela Round)"
    HANDWRITTEN = "handwritten", "Handwritten (Patrick Hand)"
    PIXEL = "pixel", "Pixel (Silkscreen)"
    COMIC = "comic", "Comic (Comic Neue)"

class BgPattern(models.TextChoices):
    NONE = "none", "None"
    STARS = "stars", "Stars"
    POLKA = "polka", "Polka Dots"
    STRIPES = "stripes", "Stripes"
    WAVES = "waves", "Waves"
```

2. Add fields:

```python
dark_mode = models.BooleanField(default=False)
bg_pattern = models.CharField(max_length=20, choices=BgPattern.choices, default="none")
font_style = models.CharField(max_length=20, choices=FontStyle.choices, default="default")
sidebar_color = models.CharField(max_length=7, default="", blank=True)
```

Then run `python manage.py makemigrations core` to auto-generate the migration.
  </action>
  <verify>
Run `python manage.py makemigrations --check core` (should report no changes needed after migration created).
Run `python manage.py migrate` to apply.
  </verify>
  <done>4 new fields on User model, migration applied to db.sqlite3</done>
</task>

<task type="auto">
  <name>Task 2: Add settings UI and view handling</name>
  <files>core/views.py, templates/core/kid_settings.html</files>
  <action>
**In core/views.py KidSettingsView:**

In `get()`, add to context dict:
```python
"dark_mode": request.user.dark_mode,
"bg_pattern": request.user.bg_pattern,
"pattern_choices": User.BgPattern.choices,
"font_style": request.user.font_style,
"font_choices": User.FontStyle.choices,
"sidebar_color": request.user.sidebar_color,
```

In `post()`, add handling before `request.user.save()`:
```python
# Dark mode
request.user.dark_mode = request.POST.get("dark_mode") == "on"

# Background pattern
bg_pattern = request.POST.get("bg_pattern", "none")
valid_patterns = [c[0] for c in User.BgPattern.choices]
if bg_pattern not in valid_patterns:
    bg_pattern = "none"
request.user.bg_pattern = bg_pattern

# Font style
font_style = request.POST.get("font_style", "default")
valid_fonts = [c[0] for c in User.FontStyle.choices]
if font_style not in valid_fonts:
    font_style = "default"
request.user.font_style = font_style

# Sidebar accent color
sidebar_color = request.POST.get("sidebar_color", "")
if sidebar_color and not hex_re.match(sidebar_color):
    sidebar_color = ""
request.user.sidebar_color = sidebar_color
```

**In templates/core/kid_settings.html:**

Add 4 new cards between the Background Color card and the Sound/Animation row. Each card uses the existing `pref-card` class.

1. **Dark Mode card** (simple toggle):
   - Form switch checkbox, name="dark_mode", checked if `{{ dark_mode }}`
   - Icon: `bi-moon-stars`, label: "Dark Mode"
   - Small note: "Easier on the eyes at night"

2. **Background Pattern card**:
   - Radio buttons for each pattern choice, name="bg_pattern"
   - Show a small CSS preview swatch (50x50px div) next to each option demonstrating the pattern
   - Use the same pref-option layout as sound/animation cards
   - Icon: `bi-grid-3x3`, label: "Background Pattern"
   - Pattern previews use CSS only (repeating-linear-gradient, radial-gradient, etc.)

3. **Font Style card**:
   - Radio buttons for each font choice, name="font_style"
   - Each option label should render in its own font so kids see the style
   - Add inline style on each label: `style="font-family: 'Varela Round'"` etc.
   - Icon: `bi-fonts`, label: "Font Style"
   - Add a "Preview" button per option that briefly applies the font to the page (use JS to toggle body font-family for 3 seconds)

4. **Sidebar Accent Color card**:
   - Color picker input, same pattern as bg_color_1 picker
   - Hidden input name="sidebar_color"
   - Reset button to clear
   - Small preview bar showing the color
   - Icon: `bi-layout-sidebar`, label: "Sidebar Color"

For the pattern preview swatches, use these CSS patterns:
- Stars: `radial-gradient(2px 2px at random positions)` -- use a repeating pattern of small dots at varied positions to simulate stars
- Polka Dots: `radial-gradient(circle, rgba(0,0,0,0.08) 8px, transparent 8px)` with `background-size: 30px 30px`
- Stripes: `repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.05) 10px, rgba(0,0,0,0.05) 20px)`
- Waves: `url("data:image/svg+xml,...")` with a simple sine wave SVG, or use a repeating radial gradient to simulate waves

Add to the extra_css block: styles for pattern preview swatches (`.pattern-swatch { width: 50px; height: 50px; border-radius: 8px; border: 1px solid rgba(0,0,0,0.1); flex-shrink: 0; }`)

Add to the extra_js block:
- `previewFont(fontFamily)` -- temporarily sets `document.body.style.fontFamily` for 3 seconds, then reverts
- `updateSidebarPreview()` -- updates sidebar color preview swatch
- `resetSidebarColor()` -- clears sidebar color input and preview

Load Google Fonts for the font options in extra_css block:
```html
<link href="https://fonts.googleapis.com/css2?family=Varela+Round&family=Patrick+Hand&family=Silkscreen&family=Comic+Neue:wght@400;700&display=swap" rel="stylesheet">
```
  </action>
  <verify>
Run `python manage.py runserver` and navigate to kid settings page. Confirm all 4 new cards render. Toggle dark mode, select a pattern, pick a font, choose sidebar color, save. Reload and confirm values persist.
  </verify>
  <done>Settings page shows 4 new preference cards, form saves all values correctly</done>
</task>

<task type="auto">
  <name>Task 3: Apply theme in base template</name>
  <files>templates/base.html</files>
  <action>
Modify templates/base.html to apply the 4 visual theme preferences for authenticated users.

**1. Dark Mode:**
Change the `<html>` tag to be dynamic:
```html
<html lang="en" data-bs-theme="{% if user.is_authenticated and user.dark_mode %}dark{% else %}light{% endif %}">
```
Bootstrap 5.3 + AdminLTE 4 support `data-bs-theme="dark"` natively -- this handles most dark mode styling automatically.

**2. Background Pattern:**
In the existing `<style>` block (lines 31-42), extend to add pattern overlay. After the background color/gradient rules, add a `background-image` for patterns using `::before` pseudo-element on `.app-main`:

```html
{% if user.bg_pattern and user.bg_pattern != 'none' %}
.app-main { position: relative; }
.app-main::before {
  content: '';
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  pointer-events: none;
  z-index: 0;
  opacity: 0.4;
  {% if user.bg_pattern == 'stars' %}
  background-image:
    radial-gradient(1px 1px at 10% 20%, rgba(255,255,255,0.8) 50%, transparent 50%),
    radial-gradient(1.5px 1.5px at 40% 70%, rgba(255,255,255,0.6) 50%, transparent 50%),
    radial-gradient(1px 1px at 70% 30%, rgba(255,255,255,0.7) 50%, transparent 50%),
    radial-gradient(2px 2px at 25% 80%, rgba(255,255,255,0.5) 50%, transparent 50%),
    radial-gradient(1px 1px at 85% 55%, rgba(255,255,255,0.8) 50%, transparent 50%),
    radial-gradient(1.5px 1.5px at 55% 15%, rgba(255,255,255,0.6) 50%, transparent 50%);
  background-size: 200px 200px;
  {% elif user.bg_pattern == 'polka' %}
  background-image: radial-gradient(circle, rgba(0,0,0,0.08) 8px, transparent 8px);
  background-size: 30px 30px;
  {% elif user.bg_pattern == 'stripes' %}
  background-image: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 10px,
    rgba(0,0,0,0.04) 10px,
    rgba(0,0,0,0.04) 20px
  );
  {% elif user.bg_pattern == 'waves' %}
  background-image:
    repeating-radial-gradient(ellipse at 50% 100%, transparent 0px, transparent 20px, rgba(0,0,0,0.03) 20px, rgba(0,0,0,0.03) 25px, transparent 25px, transparent 45px);
  background-size: 80px 40px;
  {% endif %}
}
.app-main > * { position: relative; z-index: 1; }
{% endif %}
```

Note: For dark mode + stars pattern, stars should use white/light colors (which the above already does). For dark mode + polka/stripes/waves, the rgba(0,0,0,...) will be subtle on dark backgrounds -- consider using rgba(255,255,255,...) instead when dark_mode is on. Add a conditional:
- If `user.dark_mode`: use `rgba(255,255,255,0.08)` for polka, stripes, waves
- If not `user.dark_mode`: use `rgba(0,0,0,0.08)` as above

**3. Font Style:**
In the existing Google Fonts link (line 13), this only loads Nunito. The additional fonts are loaded on the settings page. For applying them globally, add a conditional font link in `<head>`:

```html
{% if user.is_authenticated and user.font_style and user.font_style != 'default' %}
<link href="https://fonts.googleapis.com/css2?family={% if user.font_style == 'rounded' %}Varela+Round{% elif user.font_style == 'handwritten' %}Patrick+Hand{% elif user.font_style == 'pixel' %}Silkscreen{% elif user.font_style == 'comic' %}Comic+Neue:wght@400;700{% endif %}&display=swap" rel="stylesheet">
<style>
body, .sidebar-menu, .app-header, .card, .btn {
  font-family: '{% if user.font_style == "rounded" %}Varela Round{% elif user.font_style == "handwritten" %}Patrick Hand{% elif user.font_style == "pixel" %}Silkscreen{% elif user.font_style == "comic" %}Comic Neue{% endif %}', sans-serif !important;
}
</style>
{% endif %}
```

**4. Sidebar Accent Color:**
Add conditional styling for the sidebar when `user.sidebar_color` is set:

```html
{% if user.is_authenticated and user.sidebar_color %}
<style>
.app-sidebar {
  background-color: {{ user.sidebar_color }} !important;
}
.app-sidebar .nav-link {
  color: rgba(255,255,255,0.85) !important;
}
.app-sidebar .nav-link:hover,
.app-sidebar .nav-link.active {
  color: #fff !important;
  background: rgba(255,255,255,0.15) !important;
}
.app-sidebar .sidebar-brand .brand-text {
  color: #fff !important;
}
.app-sidebar .btn-outline-secondary {
  color: rgba(255,255,255,0.8) !important;
  border-color: rgba(255,255,255,0.3) !important;
}
.app-sidebar .btn-outline-secondary:hover {
  background: rgba(255,255,255,0.15) !important;
  color: #fff !important;
}
</style>
{% endif %}
```

Keep all dynamic styles organized in a single `{% if user.is_authenticated %}` block to avoid scattered style tags.
  </action>
  <verify>
Run `python manage.py runserver`. Log in as a kid. Go to settings, enable dark mode -- confirm entire page goes dark via Bootstrap dark theme. Select "Polka Dots" pattern -- confirm dots overlay appears on background. Select "Handwritten" font -- confirm text across pages changes to Patrick Hand. Set sidebar color to a bright purple -- confirm sidebar changes color with readable white text. Save and navigate to other pages to confirm all settings persist globally.
  </verify>
  <done>
All 4 visual theme features apply globally:
- Dark mode toggles Bootstrap data-bs-theme between light/dark
- Background patterns overlay on the user's chosen background color
- Font style changes text across all pages
- Sidebar accent color overrides sidebar background with appropriate text contrast
  </done>
</task>

</tasks>

<verification>
1. `python manage.py test` -- existing tests still pass
2. Log in as kid, visit settings, verify all 4 new cards render with correct current values
3. Toggle dark mode on, save -- entire app uses dark theme
4. Select each pattern one at a time, save -- pattern visible as overlay on background
5. Select each font, save -- text changes across all pages
6. Set sidebar color, save, navigate pages -- sidebar stays colored
7. Reset all to defaults -- app returns to normal appearance
8. Log in as parent -- confirm no theme settings leak (parents see default)
</verification>

<success_criteria>
- 4 new User model fields with migration applied
- Kid settings page has Dark Mode, Background Pattern, Font Style, and Sidebar Color cards
- All preferences persist across sessions
- Dark mode uses Bootstrap 5.3 native dark theme (data-bs-theme="dark")
- Patterns render as CSS-only overlays (no images)
- Fonts load from Google Fonts CDN
- Sidebar color overrides with readable white text
- No regressions in existing functionality
</success_criteria>

<output>
After completion, create `.planning/quick/013-visual-theme-dark-patterns-fonts-sidebar/013-SUMMARY.md`
</output>
