---
phase: quick-015
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/models.py
  - core/achievements.py
  - core/views.py
  - templates/core/kid_settings.html
  - templates/core/kid_chore_list.html
  - core/migrations/NNNN_expand_unlockables.py
autonomous: true

must_haves:
  truths:
    - "Only chime (sound), confetti (animation), first ~6 emojis, solid bg color, and none-pattern/default-font are free"
    - "Locked items show lock icon + unlock criteria text in settings"
    - "Kids cannot save locked options via POST (server enforces)"
    - "New sounds play correctly in both settings preview and chore completion"
    - "New animations play correctly in both settings preview and chore completion"
    - "New patterns render correctly when selected"
    - "~25-30 new unlockable achievements appear in badge gallery"
  artifacts:
    - path: "core/models.py"
      provides: "New SoundPreference, AnimationPreference, BgPattern TextChoices entries"
    - path: "core/achievements.py"
      provides: "~25-30 new ACHIEVEMENT_DEFINITIONS with category=unlockable"
    - path: "core/views.py"
      provides: "Expanded _get_unlocked() and POST enforcement for all locked categories"
    - path: "templates/core/kid_settings.html"
      provides: "Lock icons on sounds, animations, emojis, gradient, dark mode, sidebar color"
    - path: "templates/core/kid_chore_list.html"
      provides: "New sound/animation JS functions for chore completion"
  key_links:
    - from: "core/views.py (_get_unlocked)"
      to: "templates/core/kid_settings.html"
      via: "context variables for unlocked sets"
    - from: "core/views.py (POST)"
      to: "core/views.py (_get_unlocked)"
      via: "server-side lock enforcement before save"
    - from: "core/achievements.py"
      to: "core/views.py"
      via: "achievement slugs match unlock map keys"
---

<objective>
Expand the unlockable system to lock most customization options behind achievement milestones. Add 5 new sounds, 4 new animations, 3 new patterns, and ~25-30 new unlockable achievement definitions. Keep a small starter set free (chime, confetti, first row of emojis, solid bg color, default font/pattern). Update the settings page to show lock icons on all gated items and enforce locks server-side.

Purpose: Make customization a reward system that motivates kids to complete chores and hit milestones.
Output: Expanded achievement definitions, new model choices, locked settings UI, server enforcement.
</objective>

<execution_context>
@/Users/ike/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ike/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/models.py
@core/achievements.py
@core/views.py
@templates/core/kid_settings.html
@templates/core/kid_chore_list.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add new model choices, achievement definitions, and migration</name>
  <files>core/models.py, core/achievements.py, core/migrations/NNNN_expand_unlockables.py</files>
  <action>
**In core/models.py:**

1. Add new entries to `User.SoundPreference` TextChoices:
   - LASER = "laser", "Laser"
   - POWERUP = "powerup", "Power Up"
   - LEVELUP = "levelup", "Level Up"
   - APPLAUSE = "applause", "Applause"
   - DRUMROLL = "drumroll", "Drumroll"

2. Add new entries to `User.AnimationPreference` TextChoices:
   - BUBBLES = "bubbles", "Bubbles"
   - RAINBOW = "rainbow", "Rainbow"
   - SPARKLE = "sparkle", "Sparkle"
   - SNOW = "snow", "Snow"

3. Add new entries to `User.BgPattern` TextChoices:
   - CHECKERBOARD = "checkerboard", "Checkerboard"
   - ZIGZAG = "zigzag", "Zigzag"
   - DIAMONDS = "diamonds", "Diamonds"

**In core/achievements.py:**

Add ~27 new entries to ACHIEVEMENT_DEFINITIONS with category="unlockable". Use these exact slugs and spread criteria across milestone types:

Sounds (6 locked -- fanfare, coin, xylophone already exist but need unlock achievements; laser, powerup, levelup, applause, drumroll are new):
- unlock_sound_fanfare: chore_total=10, "Complete 10 chores to unlock Fanfare sound"
- unlock_sound_coin: streak_current=5, "Get a 5-day streak to unlock Coin sound"
- unlock_sound_xylophone: time_earned_minutes=120, "Earn 2 hours of time to unlock Xylophone sound"
- unlock_sound_laser: chore_total=75, "Complete 75 chores to unlock Laser sound"
- unlock_sound_powerup: bonus_total=15, "Complete 15 bonus chores to unlock Power Up sound"
- unlock_sound_levelup: streak_current=14, "Get a 14-day streak to unlock Level Up sound"
- unlock_sound_applause: chore_total=150, "Complete 150 chores to unlock Applause sound"
- unlock_sound_drumroll: timer_sessions=25, "Use timer 25 times to unlock Drumroll sound"

Animations (7 locked -- fireworks, stars, hearts exist but need unlock achievements; bubbles, rainbow, sparkle, snow are new):
- unlock_anim_fireworks: chore_total=20, "Complete 20 chores to unlock Fireworks animation"
- unlock_anim_stars: streak_current=10, "Get a 10-day streak to unlock Stars animation"
- unlock_anim_hearts: time_earned_minutes=180, "Earn 3 hours of time to unlock Hearts animation"
- unlock_anim_bubbles: bonus_total=10, "Complete 10 bonus chores to unlock Bubbles animation"
- unlock_anim_rainbow: chore_total=100, "Complete 100 chores to unlock Rainbow animation"
- unlock_anim_sparkle: timer_sessions=15, "Use timer 15 times to unlock Sparkle animation"
- unlock_anim_snow: streak_current=21, "Get a 21-day streak to unlock Snow animation"

Emoji groups (5 -- first row "Animals" ~6 emojis free, lock the rest by row):
- unlock_emoji_faces: chore_total=5, "Complete 5 chores to unlock Face emojis"
- unlock_emoji_space: time_earned_minutes=30, "Earn 30 min of time to unlock Space emojis"
- unlock_emoji_sports: bonus_total=3, "Complete 3 bonus chores to unlock Sports emojis"
- unlock_emoji_fantasy: streak_current=7, "Get a 7-day streak to unlock Fantasy emojis"
- unlock_emoji_ninja: chore_total=200, "Complete 200 chores to unlock Ninja emoji"

Feature unlocks (3):
- unlock_gradient: chore_total=30, "Complete 30 chores to unlock Gradient mode"
- unlock_dark_mode: streak_current=3, "Get a 3-day streak to unlock Dark Mode"
- unlock_sidebar_color: time_earned_minutes=60, "Earn 1 hour of time to unlock Sidebar Color"

New patterns (3):
- unlock_pattern_checkerboard: chore_total=40, "Complete 40 chores to unlock Checkerboard pattern"
- unlock_pattern_zigzag: bonus_total=20, "Complete 20 bonus chores to unlock Zigzag pattern"
- unlock_pattern_diamonds: timer_sessions=30, "Use timer 30 times to unlock Diamonds pattern"

Use appropriate emojis for each (sound ones use speaker/music emojis, animation ones use sparkle/party emojis, etc.).

Total new unlockables: 8 sounds + 7 animations + 5 emojis + 3 features + 3 patterns = 26 new (on top of 8 existing = 34 total unlockables).

**Migration:** Run `python manage.py makemigrations core` to generate migration for the new TextChoices on sound_preference, animation_preference, and bg_pattern fields. Then run `python manage.py migrate`. Then run seed: `python manage.py seed_achievements` (or call seed_achievements() from shell if no management command exists -- check first).
  </action>
  <verify>
- `python manage.py makemigrations --check` shows no pending migrations
- `python manage.py migrate` succeeds
- `python manage.py shell -c "from core.achievements import ACHIEVEMENT_DEFINITIONS; print(len([a for a in ACHIEVEMENT_DEFINITIONS if a['category']=='unlockable']))"` shows ~34
- `python manage.py shell -c "from core.achievements import seed_achievements; seed_achievements(); from core.models import Achievement; print(Achievement.objects.filter(category='unlockable').count())"` shows ~34
  </verify>
  <done>New TextChoices entries exist for 5 sounds, 4 animations, 3 patterns. ~26 new unlockable achievement definitions added (34 total unlockables). Migration applied. Achievements seeded in DB.</done>
</task>

<task type="auto">
  <name>Task 2: Update views, settings UI, and chore completion JS for lock enforcement</name>
  <files>core/views.py, templates/core/kid_settings.html, templates/core/kid_chore_list.html</files>
  <action>
**In core/views.py:**

1. Expand unlock maps. Replace the current `PATTERN_UNLOCK_MAP`, `FONT_UNLOCK_MAP`, `PATTERN_UNLOCK_TEXT`, `FONT_UNLOCK_TEXT` with a unified approach. Add these maps:

```python
SOUND_UNLOCK_MAP = {
    "unlock_sound_fanfare": "fanfare",
    "unlock_sound_coin": "coin",
    "unlock_sound_xylophone": "xylophone",
    "unlock_sound_laser": "laser",
    "unlock_sound_powerup": "powerup",
    "unlock_sound_levelup": "levelup",
    "unlock_sound_applause": "applause",
    "unlock_sound_drumroll": "drumroll",
}
ANIM_UNLOCK_MAP = {
    "unlock_anim_fireworks": "fireworks",
    "unlock_anim_stars": "stars",
    "unlock_anim_hearts": "hearts",
    "unlock_anim_bubbles": "bubbles",
    "unlock_anim_rainbow": "rainbow",
    "unlock_anim_sparkle": "sparkle",
    "unlock_anim_snow": "snow",
}
EMOJI_GROUPS = {
    # Map group name -> (list of emojis in that group, unlock slug)
    "animals": (EMOJI_CHOICES[0:6], None),  # FREE - first 6 (first row displayed as Animals, indexes 0-5 if first row = animals, but check actual EMOJI_CHOICES order)
    # Actually look at EMOJI_CHOICES: first 10 are Animals, next 5 Faces, next 5 Space, next 5 Sports, next 11 Fantasy, next 1 Ninja
    # FREE: first row in grid = first 6 emojis (Animals[0:6])
    # Lock remaining animals (4) with faces group... Actually simpler: just define which emojis are free
}
```

Better approach for emojis -- define FREE_EMOJIS as the first 6 from EMOJI_CHOICES (the basic animal emojis: dog, cat, bunny, fox, bear, unicorn). Then map unlock slugs to emoji index ranges:

```python
FREE_EMOJI_COUNT = 6  # First 6 emojis in EMOJI_CHOICES are free

EMOJI_UNLOCK_MAP = {
    "unlock_emoji_faces": EMOJI_CHOICES[10:15],    # Faces row
    "unlock_emoji_space": EMOJI_CHOICES[15:20],     # Space/nature row  
    "unlock_emoji_sports": EMOJI_CHOICES[20:25],    # Sports/fun row
    "unlock_emoji_fantasy": EMOJI_CHOICES[25:35],   # Fantasy row (10 emojis)
    "unlock_emoji_ninja": EMOJI_CHOICES[35:36],     # Ninja (1 emoji)
}
# Animals 6-10 (remaining 4 animals after free 6) unlock with faces
```

Actually the simplest approach: EMOJI_CHOICES[0:6] are free. Remaining animals (index 6-9) unlock with unlock_emoji_faces. Then each group maps to its slug. But since the grid is 6-wide, the "rows" in the grid are: row 1 = [0:6] free animals, row 2 = [6:12] = remaining animals + first 2 faces, etc. This gets messy with grid alignment.

**Simpler approach:** Define which emoji indices are in each unlock group:

```python
EMOJI_UNLOCK_GROUPS = {
    # slug -> set of emoji characters that this achievement unlocks
    "unlock_emoji_faces": set(EMOJI_CHOICES[6:15]),    # remaining animals + faces
    "unlock_emoji_space": set(EMOJI_CHOICES[15:20]),    # space/nature
    "unlock_emoji_sports": set(EMOJI_CHOICES[20:25]),   # sports/fun
    "unlock_emoji_fantasy": set(EMOJI_CHOICES[25:35]),  # fantasy
    "unlock_emoji_ninja": set(EMOJI_CHOICES[35:]),      # ninja
}
FREE_EMOJIS = set(EMOJI_CHOICES[0:6])  # first 6 animals
```

Corresponding unlock text:
```python
SOUND_UNLOCK_TEXT = {
    "fanfare": "Complete 10 chores", "coin": "Get a 5-day streak",
    "xylophone": "Earn 2 hours of time", "laser": "Complete 75 chores",
    "powerup": "Complete 15 bonus chores", "levelup": "Get a 14-day streak",
    "applause": "Complete 150 chores", "drumroll": "Use timer 25 times",
}
ANIM_UNLOCK_TEXT = {
    "fireworks": "Complete 20 chores", "stars": "Get a 10-day streak",
    "hearts": "Earn 3 hours of time", "bubbles": "Complete 10 bonus chores",
    "rainbow": "Complete 100 chores", "sparkle": "Use timer 15 times",
    "snow": "Get a 21-day streak",
}
FEATURE_UNLOCK_TEXT = {
    "gradient": "Complete 30 chores", "dark_mode": "Get a 3-day streak",
    "sidebar_color": "Earn 1 hour of time",
}
```

2. Expand `_get_unlocked(user)` to return a dict (or multiple sets) covering all categories:

```python
def _get_unlocked(user):
    earned_slugs = set(
        UserAchievement.objects.filter(user=user).values_list("achievement__slug", flat=True)
    )
    unlocked_patterns = {v for k, v in PATTERN_UNLOCK_MAP.items() if k in earned_slugs}
    unlocked_fonts = {v for k, v in FONT_UNLOCK_MAP.items() if k in earned_slugs}
    unlocked_sounds = {v for k, v in SOUND_UNLOCK_MAP.items() if k in earned_slugs}
    unlocked_anims = {v for k, v in ANIM_UNLOCK_MAP.items() if k in earned_slugs}
    
    unlocked_emojis = set(FREE_EMOJIS)
    for slug, emoji_set in EMOJI_UNLOCK_GROUPS.items():
        if slug in earned_slugs:
            unlocked_emojis |= emoji_set
    
    unlocked_features = set()
    if "unlock_gradient" in earned_slugs:
        unlocked_features.add("gradient")
    if "unlock_dark_mode" in earned_slugs:
        unlocked_features.add("dark_mode")
    if "unlock_sidebar_color" in earned_slugs:
        unlocked_features.add("sidebar_color")
    
    return {
        "patterns": unlocked_patterns,
        "fonts": unlocked_fonts,
        "sounds": unlocked_sounds,
        "animations": unlocked_anims,
        "emojis": unlocked_emojis,
        "features": unlocked_features,
    }
```

3. Update `KidSettingsView.get()` to pass all unlock data to template:

```python
unlocked = _get_unlocked(request.user)
# Pass individual sets for template use
context = {
    ...existing context...,
    "unlocked_patterns": unlocked["patterns"],
    "unlocked_fonts": unlocked["fonts"],
    "unlocked_sounds": unlocked["sounds"],
    "unlocked_animations": unlocked["animations"],
    "unlocked_emojis": unlocked["emojis"],
    "unlocked_features": unlocked["features"],
    "sound_unlock_text": SOUND_UNLOCK_TEXT,
    "anim_unlock_text": ANIM_UNLOCK_TEXT,
    "feature_unlock_text": FEATURE_UNLOCK_TEXT,
    "pattern_unlock_text": PATTERN_UNLOCK_TEXT,
    "font_unlock_text": FONT_UNLOCK_TEXT,
}
```

4. Update `KidSettingsView.post()` to enforce ALL locks:

```python
unlocked = _get_unlocked(request.user)

# Sound lock enforcement (chime is free)
if sound != "chime" and sound not in unlocked["sounds"]:
    sound = "chime"

# Animation lock enforcement (confetti is free)  
if animation != "confetti" and animation not in unlocked["animations"]:
    animation = "confetti"

# Emoji lock enforcement
if emoji_avatar not in unlocked["emojis"]:
    emoji_avatar = request.user.emoji_avatar  # keep current

# Gradient lock enforcement
if bg_use_gradient and "gradient" not in unlocked["features"]:
    bg_use_gradient = False

# Dark mode lock enforcement
if request.POST.get("dark_mode") == "on" and "dark_mode" not in unlocked["features"]:
    request.user.dark_mode = False
else:
    request.user.dark_mode = request.POST.get("dark_mode") == "on"

# Sidebar color lock enforcement
if sidebar_color and "sidebar_color" not in unlocked["features"]:
    sidebar_color = ""

# Pattern lock enforcement (already exists, keep it)
# Font lock enforcement (already exists, keep it)
```

**In templates/core/kid_settings.html:**

5. Update Sound Preferences card to show lock icons (same pattern as patterns/fonts). For each sound choice, if value != "chime" and value not in unlocked_sounds, show opacity-50, disabled radio, lock icon + unlock text from sound_unlock_text dict. Use the exact same HTML pattern as the background pattern section (lines 223-244 of current template). The preview button should only show for unlocked sounds.

6. Update Animation Preferences card similarly. If value != "confetti" and value not in unlocked_animations, show lock icon + unlock text from anim_unlock_text.

7. Update Emoji grid to show lock on locked emojis. For each emoji, if emoji not in unlocked_emojis, add opacity-50 and a small lock overlay. Make locked emojis non-clickable (remove onclick or add a check). One approach: add a data-locked attribute and check in JS:

```html
<div class="emoji-option {% if current_emoji == emoji %}selected{% endif %} {% if emoji not in unlocked_emojis %}locked opacity-50{% endif %}"
     {% if emoji in unlocked_emojis %}onclick="selectEmoji(this, '{{ emoji }}')"{% endif %}
     ...>
    {{ emoji }}
    {% if emoji not in unlocked_emojis %}
    <span style="font-size: 0.6rem; position: absolute; bottom: 2px; right: 2px;"><i class="bi bi-lock-fill"></i></span>
    {% endif %}
</div>
```
Make each emoji-option position: relative so the lock icon positions correctly. Add a small tooltip or title attribute showing which group it belongs to and what's needed.

8. Update Background Color card: wrap the gradient toggle in a lock check. If "gradient" not in unlocked_features, show the toggle as disabled with lock icon + "Complete 30 chores to unlock". Keep the solid color picker always available (free).

9. Update Dark Mode card: if "dark_mode" not in unlocked_features, show toggle as disabled with lock icon + "Get a 3-day streak to unlock".

10. Update Sidebar Color card: if "sidebar_color" not in unlocked_features, show the color picker as disabled with lock icon + "Earn 1 hour of time to unlock".

11. Add CSS for new pattern swatches in the `<style>` block:

```css
.pattern-swatch-checkerboard {
    background-image: repeating-conic-gradient(rgba(0,0,0,0.1) 0% 25%, transparent 0% 50%);
    background-size: 16px 16px;
}
.pattern-swatch-zigzag {
    background-image: linear-gradient(135deg, rgba(0,0,0,0.08) 25%, transparent 25%),
        linear-gradient(225deg, rgba(0,0,0,0.08) 25%, transparent 25%),
        linear-gradient(45deg, rgba(0,0,0,0.08) 25%, transparent 25%),
        linear-gradient(315deg, rgba(0,0,0,0.08) 25%, transparent 25%);
    background-size: 20px 10px;
    background-position: 0 0, 10px 0, 10px -5px, 0px 5px;
}
.pattern-swatch-diamonds {
    background-image: 
        linear-gradient(45deg, rgba(0,0,0,0.08) 25%, transparent 25%, transparent 75%, rgba(0,0,0,0.08) 75%),
        linear-gradient(45deg, rgba(0,0,0,0.08) 25%, transparent 25%, transparent 75%, rgba(0,0,0,0.08) 75%);
    background-size: 20px 20px;
    background-position: 0 0, 10px 10px;
}
```

**In templates/core/kid_chore_list.html:**

12. Add new sound functions for the 5 new sounds using Web Audio API (same pattern as existing):

```javascript
function playLaser() {
    initAudioCtx();
    const now = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(1200, now);
    osc.frequency.exponentialRampToValueAtTime(100, now + 0.3);
    gain.gain.setValueAtTime(0.2, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);
    osc.start(now); osc.stop(now + 0.3);
}

function playPowerup() {
    initAudioCtx();
    const now = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain); gain.connect(audioCtx.destination);
    osc.frequency.setValueAtTime(300, now);
    osc.frequency.exponentialRampToValueAtTime(1200, now + 0.4);
    gain.gain.setValueAtTime(0.2, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
    osc.start(now); osc.stop(now + 0.4);
}

function playLevelup() {
    initAudioCtx();
    const now = audioCtx.currentTime;
    const notes = [523, 659, 784, 1047]; // C5, E5, G5, C6
    notes.forEach((freq, i) => {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain); gain.connect(audioCtx.destination);
        osc.frequency.value = freq;
        const start = now + i * 0.1;
        gain.gain.setValueAtTime(0.2, start);
        gain.gain.exponentialRampToValueAtTime(0.01, start + 0.2);
        osc.start(start); osc.stop(start + 0.2);
    });
}

function playApplause() {
    initAudioCtx();
    const now = audioCtx.currentTime;
    // White noise burst simulating applause
    const bufferSize = audioCtx.sampleRate * 0.6;
    const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / bufferSize, 0.5);
    }
    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    const gain = audioCtx.createGain();
    const filter = audioCtx.createBiquadFilter();
    filter.type = "bandpass";
    filter.frequency.value = 3000;
    source.connect(filter); filter.connect(gain); gain.connect(audioCtx.destination);
    gain.gain.setValueAtTime(0.15, now);
    gain.gain.exponentialRampToValueAtTime(0.01, now + 0.6);
    source.start(now);
}

function playDrumroll() {
    initAudioCtx();
    const now = audioCtx.currentTime;
    for (let i = 0; i < 12; i++) {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain); gain.connect(audioCtx.destination);
        osc.type = "triangle";
        osc.frequency.value = 150 + Math.random() * 30;
        const start = now + i * 0.04;
        gain.gain.setValueAtTime(0.12 + (i / 12) * 0.08, start);
        gain.gain.exponentialRampToValueAtTime(0.01, start + 0.05);
        osc.start(start); osc.stop(start + 0.05);
    }
}
```

Update the `playChoreSound()` dispatch map to include new sounds:
```javascript
const fn = { chime: playChime, fanfare: playFanfare, coin: playCoin, xylophone: playXylophone, laser: playLaser, powerup: playPowerup, levelup: playLevelup, applause: playApplause, drumroll: playDrumroll };
```

13. Add new animation functions for the 4 new animations:

```javascript
function playBubbles() {
    for (let i = 0; i < 5; i++) {
        setTimeout(() => {
            confetti({
                particleCount: 15,
                spread: 30,
                startVelocity: 20,
                origin: { x: 0.2 + Math.random() * 0.6, y: 0.8 },
                colors: ["#89CFF0", "#A7D8DE", "#B0E0E6", "#87CEEB"],
                shapes: ["circle"],
                gravity: 0.3,
                disableForReducedMotion: true,
            });
        }, i * 100);
    }
}

function playRainbow() {
    const colors = ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#4B0082", "#9400D3"];
    colors.forEach((color, i) => {
        setTimeout(() => {
            confetti({
                particleCount: 20,
                angle: 90,
                spread: 40,
                origin: { x: 0.1 + i * 0.12, y: 0.7 },
                colors: [color],
                disableForReducedMotion: true,
            });
        }, i * 80);
    });
}

function playSparkle() {
    const sparkleShape = confetti.shapeFromText({ text: "\u2728", scalar: 2 });
    confetti({
        particleCount: 50,
        spread: 100,
        origin: { y: 0.6 },
        shapes: [sparkleShape],
        scalar: 1.2,
        colors: ["#FFD700", "#FFF8DC", "#FFFACD", "#F0E68C"],
        disableForReducedMotion: true,
    });
}

function playSnow() {
    confetti({
        particleCount: 60,
        spread: 180,
        startVelocity: 10,
        origin: { y: 0 },
        colors: ["#FFFFFF", "#F0F8FF", "#E6E6FA"],
        shapes: ["circle"],
        gravity: 0.4,
        drift: 0.5,
        ticks: 200,
        disableForReducedMotion: true,
    });
}
```

Update the `playCelebration()` dispatch map:
```javascript
const fn = { confetti: playConfetti, fireworks: playFireworks, stars: playStars, hearts: playHearts, bubbles: playBubbles, rainbow: playRainbow, sparkle: playSparkle, snow: playSnow };
```

**In templates/core/kid_settings.html:**

14. Copy the same new sound/animation JS functions into the settings page preview script section. Update the `previewSound()` dispatch and `previewAnimation()` dispatch to include all new options.

15. Also add CSS pattern classes to the base template or wherever patterns are applied for bg_pattern rendering. Check if there's a shared pattern CSS file or if patterns are applied in base_kid.html. The new patterns (checkerboard, zigzag, diamonds) need CSS in the same place the existing patterns (stars, polka, stripes, waves) are defined for the actual page background (not just the swatch). Search for where `.bg-pattern-stars` or similar classes are defined and add the new ones.
  </action>
  <verify>
- `python manage.py runserver` starts without errors
- Visit /kid/settings/ as a kid user with NO achievements: only chime sound selectable, only confetti animation selectable, only first 6 emojis clickable, gradient toggle disabled, dark mode toggle disabled, sidebar color picker disabled, all non-free patterns/fonts locked. All locked items show lock icon + unlock criteria text.
- Try submitting the form with browser dev tools to force a locked value (e.g., sound=laser) -- server should reject and default to free option.
- Visit /kid/settings/ as a kid who HAS earned relevant achievements: unlocked items are selectable and saveable.
- Visit /kid/chores/ and complete a chore: new sounds (if selected) play correctly, new animations (if selected) play correctly.
- New pattern swatches render correctly in settings page.
  </verify>
  <done>
All customization options properly gated behind achievement unlocks. Settings page shows lock icons with unlock criteria on all locked items. Server-side POST enforcement rejects locked selections. New sounds (laser, powerup, levelup, applause, drumroll) play via Web Audio in both settings preview and chore completion. New animations (bubbles, rainbow, sparkle, snow) play via canvas-confetti in both pages. New pattern swatches display correctly. Free starter set: chime, confetti, first 6 emojis, solid bg color, none pattern, default font.
  </done>
</task>

</tasks>

<verification>
1. Start dev server: `python manage.py runserver`
2. Log in as a kid with no achievements -- verify ALL customization is locked except free defaults
3. In Django admin or shell, award a few test achievements to the kid -- verify corresponding options unlock
4. Save settings with an unlocked option -- verify it persists
5. Attempt to POST a locked value via curl/devtools -- verify server rejects
6. Complete a chore with each new sound/animation selected -- verify playback
7. Check badge gallery (/kid/badges/) -- verify ~34 unlockable achievements appear
</verification>

<success_criteria>
- 5 new sounds, 4 new animations, 3 new patterns added as model choices with migration
- ~26 new unlockable achievements defined and seeded (34 total unlockables)
- Settings page shows lock icons + criteria text on all locked items
- Server-side enforcement prevents saving locked options
- All new sounds/animations work in both settings preview and chore completion
- Free starter set: chime, confetti, first 6 emojis, solid bg color, none pattern, default font
</success_criteria>

<output>
After completion, create `.planning/quick/015-expand-unlockables-lock-customization/015-SUMMARY.md`
</output>
