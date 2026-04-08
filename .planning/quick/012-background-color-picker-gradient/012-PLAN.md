---
phase: quick-012
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/models.py
  - core/views.py
  - templates/core/kid_settings.html
  - templates/base.html
  - static/css/chorebank.css
  - core/migrations/0011_user_bg_color_fields.py
autonomous: true

must_haves:
  truths:
    - "Kid can pick a solid background color using a color picker and see it applied immediately"
    - "Kid can pick two colors and enable a gradient background"
    - "Background color preference persists across sessions (stored in DB)"
    - "Default background remains #FAF8FC when no custom color is set"
  artifacts:
    - path: "core/models.py"
      provides: "bg_color_1, bg_color_2, bg_use_gradient fields on User"
      contains: "bg_color_1"
    - path: "core/migrations/0011_user_bg_color_fields.py"
      provides: "Migration for new background color fields"
    - path: "templates/core/kid_settings.html"
      provides: "Color picker UI section"
      contains: "color"
    - path: "templates/base.html"
      provides: "Dynamic background style injection"
      contains: "bg_color"
  key_links:
    - from: "templates/base.html"
      to: "User.bg_color_1"
      via: "inline style on body or app-wrapper"
      pattern: "bg_color"
    - from: "templates/core/kid_settings.html"
      to: "core/views.py KidSettingsView"
      via: "POST form submission"
      pattern: "bg_color"
---

<objective>
Add background color customization for kids: solid color picker and two-color gradient option.

Purpose: Let kids personalize their app experience beyond emoji/sound/animation, making ChoreBank feel like "their" app.
Output: New color fields on User model, color picker UI on kid settings page, dynamic background applied across all kid pages.
</objective>

<execution_context>
@/Users/ike/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ike/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/models.py
@core/views.py
@templates/base.html
@templates/base_kid.html
@templates/core/kid_settings.html
@static/css/chorebank.css
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add background color fields to User model and create migration</name>
  <files>core/models.py, core/migrations/0011_user_bg_color_fields.py</files>
  <action>
Add three new fields to the User model in core/models.py:

1. `bg_color_1` - CharField(max_length=7, default="", blank=True) -- primary/solid background color as hex (e.g. "#FF9A9E")
2. `bg_color_2` - CharField(max_length=7, default="", blank=True) -- second gradient color as hex
3. `bg_use_gradient` - BooleanField(default=False) -- whether to use gradient mode

Place these fields after `animation_preference` to keep personalization fields grouped.

Empty string for bg_color_1 means "use default theme background (#FAF8FC)".

Run `python manage.py makemigrations core` to generate the migration, then `python manage.py migrate` to apply it.
  </action>
  <verify>
Run `python manage.py makemigrations --check` (should say no changes detected).
Run `python manage.py shell -c "from core.models import User; u = User.objects.first(); print(u.bg_color_1, u.bg_color_2, u.bg_use_gradient)"` -- should print empty strings and False.
  </verify>
  <done>User model has bg_color_1, bg_color_2, bg_use_gradient fields. Migration applied successfully.</done>
</task>

<task type="auto">
  <name>Task 2: Add color picker UI to kid settings and wire view + base template</name>
  <files>core/views.py, templates/core/kid_settings.html, templates/base.html, static/css/chorebank.css</files>
  <action>
**KidSettingsView (core/views.py):**

In the `get` method, add to context:
- `bg_color_1`: request.user.bg_color_1
- `bg_color_2`: request.user.bg_color_2
- `bg_use_gradient`: request.user.bg_use_gradient

In the `post` method, read and save:
- `bg_color_1` from POST -- validate it matches regex `^#[0-9A-Fa-f]{6}$` or is empty string. If invalid, set to "".
- `bg_color_2` from POST -- same validation.
- `bg_use_gradient` from POST -- truthy check (`request.POST.get("bg_use_gradient") == "on"`).
- If bg_use_gradient is True but bg_color_2 is empty, set bg_use_gradient to False.
- Save on the user object alongside existing sound/animation/emoji saves.

**kid_settings.html:**

Add a new card section AFTER the avatar card and BEFORE the sound/animation row. Structure:

```
<div class="row g-4 mb-4">
  <div class="col-12">
    <div class="card pref-card">
      <div class="card-body">
        <h5 class="card-title mb-3">
          <i class="bi bi-palette me-2" style="color: #B19CD9;"></i>Background Color
        </h5>

        <!-- Solid color picker -->
        <div class="mb-3">
          <label class="form-label fw-500">Pick a color</label>
          <div class="d-flex align-items-center gap-3">
            <input type="color" id="bg_color_1_picker" class="form-control form-control-color"
                   value="{{ bg_color_1|default:'#FAF8FC' }}"
                   onchange="updateBgPreview()">
            <button type="button" class="btn btn-sm btn-outline-secondary"
                    onclick="resetBgColor()">
              <i class="bi bi-arrow-counterclockwise"></i> Reset to Default
            </button>
          </div>
          <input type="hidden" name="bg_color_1" id="bg_color_1_input" value="{{ bg_color_1 }}">
        </div>

        <!-- Gradient toggle -->
        <div class="form-check form-switch mb-3">
          <input class="form-check-input" type="checkbox" id="bg_gradient_toggle"
                 name="bg_use_gradient" {% if bg_use_gradient %}checked{% endif %}
                 onchange="toggleGradient()">
          <label class="form-check-label" for="bg_gradient_toggle">Use gradient (two colors)</label>
        </div>

        <!-- Second color picker (shown when gradient enabled) -->
        <div id="gradient_color_row" class="mb-3" style="{% if not bg_use_gradient %}display:none{% endif %}">
          <label class="form-label fw-500">Second color</label>
          <div class="d-flex align-items-center gap-3">
            <input type="color" id="bg_color_2_picker" class="form-control form-control-color"
                   value="{{ bg_color_2|default:'#E8D5F5' }}"
                   onchange="updateBgPreview()">
          </div>
          <input type="hidden" name="bg_color_2" id="bg_color_2_input" value="{{ bg_color_2 }}">
        </div>

        <!-- Live preview swatch -->
        <div class="mt-3">
          <label class="form-label fw-500">Preview</label>
          <div id="bg_preview" style="height: 60px; border-radius: 12px; border: 1px solid rgba(0,0,0,0.1);"></div>
        </div>
      </div>
    </div>
  </div>
</div>
```

Add JavaScript in the `extra_js` block (before existing sound/animation scripts):

```javascript
// ========== Background Color Picker ==========
function updateBgPreview() {
    const color1 = document.getElementById('bg_color_1_picker').value;
    const color2 = document.getElementById('bg_color_2_picker').value;
    const useGradient = document.getElementById('bg_gradient_toggle').checked;
    const preview = document.getElementById('bg_preview');

    // Update hidden inputs
    document.getElementById('bg_color_1_input').value = color1;
    document.getElementById('bg_color_2_input').value = color2;

    // Update preview
    if (useGradient) {
        preview.style.background = `linear-gradient(135deg, ${color1}, ${color2})`;
    } else {
        preview.style.background = color1;
    }
}

function toggleGradient() {
    const row = document.getElementById('gradient_color_row');
    const isGradient = document.getElementById('bg_gradient_toggle').checked;
    row.style.display = isGradient ? '' : 'none';
    updateBgPreview();
}

function resetBgColor() {
    document.getElementById('bg_color_1_picker').value = '#FAF8FC';
    document.getElementById('bg_color_1_input').value = '';
    document.getElementById('bg_color_2_picker').value = '#E8D5F5';
    document.getElementById('bg_color_2_input').value = '';
    document.getElementById('bg_gradient_toggle').checked = false;
    toggleGradient();
}

// Initialize preview on load
document.addEventListener('DOMContentLoaded', updateBgPreview);
```

**base.html:**

Add a dynamic inline style block right after `<body class="layout-fixed sidebar-expand-lg">` (line 29). Use Django template logic to inject background color ONLY if the user is authenticated and has a custom bg_color_1 set:

```html
{% if user.is_authenticated and user.bg_color_1 %}
<style>
  body, .app-main {
    {% if user.bg_use_gradient and user.bg_color_2 %}
    background: linear-gradient(135deg, {{ user.bg_color_1 }}, {{ user.bg_color_2 }}) !important;
    background-attachment: fixed !important;
    {% else %}
    background-color: {{ user.bg_color_1 }} !important;
    {% endif %}
  }
</style>
{% endif %}
```

Place this style tag inside the `<body>` element, right after the opening body tag and before `<div class="app-wrapper">`. This keeps it scoped and ensures it overrides the CSS variable-based background.

**chorebank.css:**

Add a utility class at the bottom for the color picker input sizing:

```css
/* Color picker sizing */
.form-control-color {
    width: 60px;
    height: 40px;
    padding: 4px;
    border-radius: 8px;
    cursor: pointer;
}
```
  </action>
  <verify>
Run `python manage.py runserver` and visit /kid/settings/ as a kid user.
Verify: color picker card appears between avatar and sound/animation sections.
Verify: picking a color updates the preview swatch in real-time.
Verify: toggling gradient shows/hides second color picker.
Verify: clicking "Reset to Default" clears colors.
Verify: saving settings and refreshing shows the chosen background applied to all pages.
Verify: visiting other kid pages (home, chores, timer) also shows the custom background.
Verify: parent pages are NOT affected (parents don't have bg_color set).
  </verify>
  <done>
Kids can pick a solid color or two-color gradient for their background. Color persists in DB. Preview updates live. Background applies across all kid pages via base.html. Default theme unaffected when no custom color is set.
  </done>
</task>

</tasks>

<verification>
1. `python manage.py makemigrations --check` -- no pending migrations
2. `python manage.py test` -- existing tests pass (no regressions)
3. Manual: Log in as kid, go to Settings, pick a solid color, save -- background changes on all pages
4. Manual: Enable gradient, pick two colors, save -- gradient background on all pages
5. Manual: Click Reset to Default, save -- background returns to #FAF8FC
6. Manual: Log in as parent -- default background, no color picker in parent views
7. Manual: Log in as different kid -- each kid has independent background preference
</verification>

<success_criteria>
- Kids can customize background with solid color or two-color gradient
- Color preference persists in database across sessions
- Live preview in settings before saving
- Background applies to all kid pages (home, chores, timer, history, settings)
- Default pastel background (#FAF8FC) when no custom color is set
- Parent pages unaffected
</success_criteria>

<output>
After completion, create `.planning/quick/012-background-color-picker-gradient/012-SUMMARY.md`
</output>
