---
phase: quick
plan: 014
type: execute
wave: 1
depends_on: []
files_modified:
  - core/models.py
  - core/achievements.py
  - core/migrations/0013_achievement_system.py
  - core/views.py
  - core/urls.py
  - templates/base_kid.html
  - templates/core/kid_badges.html
  - templates/core/kid_settings.html
autonomous: false

must_haves:
  truths:
    - "Kid can view all ~50 badges in a gallery, earned ones colorful, unearned ones greyed with unlock criteria"
    - "Kid earns badges automatically when completing chores or stopping timer"
    - "Kid can set an active badge + title combo displayed on their profile"
    - "Patterns and fonts are locked until the kid earns the corresponding unlockable achievement"
    - "Settings page shows lock icons on locked patterns/fonts with what's needed to unlock"
  artifacts:
    - path: "core/models.py"
      provides: "Achievement and UserAchievement models, active_badge/active_title fields on User"
      contains: "class Achievement"
    - path: "core/achievements.py"
      provides: "Achievement checking logic and seed data definition"
      contains: "def check_achievements"
    - path: "core/migrations/0013_achievement_system.py"
      provides: "Database migration for Achievement, UserAchievement, User fields"
    - path: "templates/core/kid_badges.html"
      provides: "Badge gallery page"
    - path: "templates/core/kid_settings.html"
      provides: "Updated settings with locked patterns/fonts and active badge/title picker"
  key_links:
    - from: "core/views.py (CompleteChoreView)"
      to: "core/achievements.py (check_achievements)"
      via: "function call after chore completion"
      pattern: "check_achievements.*request.user"
    - from: "core/views.py (TimerStopView)"
      to: "core/achievements.py (check_achievements)"
      via: "function call after timer stop"
      pattern: "check_achievements.*request.user"
    - from: "core/views.py (KidSettingsView)"
      to: "core/models.py (UserAchievement)"
      via: "query unlocked achievements to gate patterns/fonts"
      pattern: "userachievement.*achievement__slug"
---

<objective>
Add a complete achievement system with ~50 badges/titles, a badge gallery page, active badge/title selection, and lock patterns/fonts behind achievement milestones.

Purpose: Gamification layer that rewards kids for consistency, effort, and variety -- making chores more engaging.
Output: Achievement and UserAchievement models, ~50 seeded achievements, auto-checking on chore completion and timer stop, badge gallery page, locked patterns/fonts in settings.
</objective>

<execution_context>
@/Users/ike/.claude/get-shit-done/workflows/execute-plan.md
@/Users/ike/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@core/models.py
@core/views.py
@core/urls.py
@templates/base_kid.html
@templates/core/kid_settings.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Achievement models, migration, and seed data</name>
  <files>
    core/models.py
    core/achievements.py
    core/migrations/0013_achievement_system.py
  </files>
  <action>
  1. Add to core/models.py AFTER TimerSession class:

  **Achievement model:**
  - slug: CharField(max_length=50, unique=True) -- machine identifier like "streak_1", "chore_count_10"
  - emoji: CharField(max_length=10) -- the badge emoji
  - title: CharField(max_length=60) -- display name like "First Step", "Chore Champion"
  - description: CharField(max_length=200) -- how to earn it like "Complete a 1-day streak"
  - category: CharField with TextChoices: STREAK, CHORE_COUNT, TIME_EARNED, TIME_USED, BONUS, SPEED, VARIETY, UNLOCKABLE
  - criteria_type: CharField(max_length=30) -- machine-readable check type like "streak_current", "chore_total", "time_earned_minutes", "timer_sessions", "bonus_total", "chore_early", "chore_variety", "unlock_pattern_stars", etc.
  - criteria_value: IntegerField -- threshold value
  - ordering by category, criteria_value

  **UserAchievement model:**
  - user: FK to User (related_name="achievements_earned")
  - achievement: FK to Achievement (related_name="earners")
  - earned_at: DateTimeField(auto_now_add=True)
  - unique_together: [user, achievement]
  - ordering: ["-earned_at"]

  **Add to User model:**
  - active_badge: FK to Achievement, null=True, blank=True, on_delete=SET_NULL, related_name="badge_users"
  - active_title: FK to Achievement, null=True, blank=True, on_delete=SET_NULL, related_name="title_users"

  2. Create core/achievements.py with:

  **ACHIEVEMENT_DEFINITIONS** -- a list of dicts defining all ~50 achievements. Each dict has: slug, emoji, title, description, category, criteria_type, criteria_value. Use these exact achievements:

  STREAKS (10):
  - streak_1: "First Step" (foot emoji), streak_current >= 1
  - streak_3: "Consistent" (calendar emoji), streak_current >= 3
  - streak_7: "Dedicated" (fire emoji), streak_current >= 7
  - streak_14: "Unstoppable" (rocket emoji), streak_current >= 14
  - streak_30: "Legend" (crown emoji), streak_current >= 30
  - comeback: "Comeback Kid" (boomerang/cycle emoji), special check -- has a streak of 0 in history then rebuilt to 3+
  - weekend_warrior: "Weekend Warrior" (calendar emoji), completed chores on both Sat+Sun at least 4 weekends
  - early_bird: "Early Bird" (sunrise emoji), 7 morning chores completed
  - night_owl: "Night Owl" (owl emoji), 7 evening chores completed
  - perfect_week: "Perfect Week" (star emoji), all required chores for 7 consecutive days

  CHORE_COUNT (8):
  - chore_1: "Getting Started" (seedling emoji), chore_total >= 1
  - chore_10: "Helping Hand" (hand emoji), chore_total >= 10
  - chore_25: "Hard Worker" (hammer emoji), chore_total >= 25
  - chore_50: "Chore Champion" (trophy emoji), chore_total >= 50
  - chore_100: "Chore Master" (medal emoji), chore_total >= 100
  - chore_250: "Chore Legend" (gem emoji), chore_total >= 250
  - chore_500: "Chore Titan" (mountain emoji), chore_total >= 500
  - chore_1000: "Chore God" (lightning emoji), chore_total >= 1000

  TIME_EARNED (8):
  - time_earn_10: "First Minutes" (hourglass emoji), time_earned_minutes >= 10
  - time_earn_30: "Time Saver" (clock emoji), time_earned_minutes >= 30
  - time_earn_60: "Hour Hero" (superhero emoji), time_earned_minutes >= 60
  - time_earn_120: "Time Rich" (money bag emoji), time_earned_minutes >= 120
  - time_earn_300: "Time Baron" (top hat emoji), time_earned_minutes >= 300
  - time_earn_600: "Time Tycoon" (chart emoji), time_earned_minutes >= 600
  - time_earn_1440: "Time Mogul" (building emoji), time_earned_minutes >= 1440
  - time_earn_6000: "Time Billionaire" (globe emoji), time_earned_minutes >= 6000

  TIME_USED (5):
  - timer_1: "Screen Starter" (TV emoji), timer_sessions >= 1
  - timer_30min: "Movie Time" (popcorn emoji), timer_long_session >= 30 (single session >= 30 min)
  - timer_60min: "Marathon" (runner emoji), timer_long_session >= 60
  - timer_10: "Timer Pro" (game controller emoji), timer_sessions >= 10
  - timer_50: "Timer Veteran" (joystick emoji), timer_sessions >= 50

  BONUS (5):
  - bonus_1: "Extra Mile" (plus emoji), bonus_total >= 1
  - bonus_5: "Overachiever" (muscle emoji), bonus_total >= 5
  - bonus_10: "Bonus Boss" (briefcase emoji), bonus_total >= 10
  - bonus_25: "Bonus Legend" (diamond emoji), bonus_total >= 25
  - bonus_50: "Above and Beyond" (rainbow emoji), bonus_total >= 50

  SPEED (4):
  - speed_1: "Quick Finisher" (running emoji), chore_early >= 1 (completed before deadline_time on due_date)
  - speed_5: "Speed Demon" (dash emoji), chore_early >= 5
  - speed_10: "Lightning" (lightning emoji), chore_early >= 10
  - speed_25: "Flash" (zap emoji), chore_early >= 25

  VARIETY (5):
  - variety_3: "Explorer" (compass emoji), chore_variety >= 3 (distinct chore names completed)
  - variety_5: "Well-Rounded" (target emoji), chore_variety >= 5
  - variety_10: "Jack of All Trades" (wrench emoji), chore_variety >= 10
  - variety_15: "Renaissance Kid" (art palette emoji), chore_variety >= 15
  - variety_20: "Master of All" (infinity emoji), chore_variety >= 20

  UNLOCKABLE (9 -- these unlock patterns/fonts):
  - unlock_stars: "Pattern: Stars" (star emoji), chore_total >= 15
  - unlock_polka: "Pattern: Polka Dots" (circle emoji), streak_current >= 3
  - unlock_stripes: "Pattern: Stripes" (barber pole emoji), time_earned_minutes >= 60
  - unlock_waves: "Pattern: Waves" (wave emoji), bonus_total >= 5
  - unlock_rounded: "Font: Rounded" (speech bubble emoji), streak_current >= 7
  - unlock_handwritten: "Font: Handwritten" (pen emoji), chore_total >= 50
  - unlock_pixel: "Font: Pixel" (game emoji), timer_sessions >= 10
  - unlock_comic: "Font: Comic" (comic speech emoji), time_earned_minutes >= 300

  Total: 54 achievements.

  **seed_achievements() function** that uses Achievement.objects.update_or_create(slug=..., defaults={...}) for each definition. This is idempotent.

  **check_achievements(user) function** that:
  - Gets all achievement slugs user has NOT yet earned
  - For each unearned achievement, computes the relevant stat and checks if criteria_value is met
  - Creates UserAchievement records for any newly earned achievements
  - Returns list of newly earned Achievement objects (for potential toast/notification later)

  Stats to compute (only compute stats needed for unearned achievements):
  - streak_current: ChoreInstance.get_streak(user)
  - chore_total: ChoreInstance.objects.filter(assigned_to=user, completed=True).count()
  - time_earned_minutes: TimeBankTransaction.objects.filter(kid=user, transaction_type="earn").aggregate(Sum("amount"))["amount__sum"] or 0
  - timer_sessions: TimerSession.objects.filter(kid=user, ended_at__isnull=False).count()
  - bonus_total: ChoreInstance.objects.filter(assigned_to=user, completed=True, chore__chore_type="bonus").count()
  - chore_early: count of ChoreInstance where completed=True and completed_at date == due_date and completed_at time < chore.deadline_time
  - chore_variety: ChoreInstance.objects.filter(assigned_to=user, completed=True).values("chore__name").distinct().count()
  - timer_long_session: TimerSession.objects.filter(kid=user, ended_at__isnull=False) then check if any session's actual_minutes >= criteria_value
  - early_bird: ChoreInstance.objects.filter(assigned_to=user, completed=True, chore__time_of_day="morning").count()
  - night_owl: ChoreInstance.objects.filter(assigned_to=user, completed=True, chore__time_of_day="evening").count()
  - perfect_week and weekend_warrior and comeback: These are complex; implement reasonable approximations. For perfect_week, use ChoreInstance._streak_data logic checking 7 consecutive complete days. For weekend_warrior, count weekends where both Sat+Sun had all required chores done. For comeback, check if user's streak was 0 at some point and is now >= 3.

  Group criteria_types so stats are computed lazily (only query DB for stat categories that have unearned achievements).

  3. Create migration 0013_achievement_system.py using `python manage.py makemigrations`. Then add a RunPython operation to call seed_achievements() in the migration (import from core.achievements). Use a pattern like:

  ```python
  def seed(apps, schema_editor):
      from core.achievements import seed_achievements
      seed_achievements()
  ```

  Run `python manage.py migrate` to apply.
  </action>
  <verify>
  - `python manage.py migrate` completes without errors
  - `python manage.py shell -c "from core.models import Achievement; print(Achievement.objects.count())"` prints 54
  - `python manage.py shell -c "from core.achievements import check_achievements; print('OK')"` prints OK
  </verify>
  <done>Achievement and UserAchievement models exist with 54 seeded achievements. check_achievements function exists and is importable. User model has active_badge and active_title FK fields.</done>
</task>

<task type="auto">
  <name>Task 2: Wire achievement checking + badge gallery + active badge/title + lock patterns/fonts</name>
  <files>
    core/views.py
    core/urls.py
    templates/base_kid.html
    templates/core/kid_badges.html
    templates/core/kid_settings.html
  </files>
  <action>
  **1. Wire achievement checking into CompleteChoreView and TimerStopView (core/views.py):**

  In CompleteChoreView.post(), after the TimeBankTransaction.objects.create block (around line 557), add:
  ```python
  from core.achievements import check_achievements
  newly_earned = check_achievements(request.user)
  ```
  (Import at top of file, not inline.)

  In TimerStopView.post(), after the balance calculation (around line 744), add:
  ```python
  newly_earned = check_achievements(request.user)
  ```

  For now, newly_earned is unused -- we just want the side-effect of creating UserAchievement records. A future enhancement could show a toast.

  **2. Create KidBadgesView (core/views.py):**

  Add a new view class KidBadgesView(KidRequiredMixin, View):
  - GET: Query all Achievement objects ordered by category, criteria_value
  - Query user's earned achievement slugs: set(UserAchievement.objects.filter(user=request.user).values_list("achievement__slug", flat=True))
  - Group achievements by category (use OrderedDict or similar)
  - Pass to template: categories (list of (category_label, achievements_with_earned_flag)), user's active_badge, user's active_title, earned_count, total_count
  - POST: Handle setting active_badge and active_title
    - active_badge_slug from POST data -- look up Achievement, verify user has earned it (UserAchievement exists), set user.active_badge
    - active_title_slug from POST data -- same check, set user.active_title
    - Allow clearing (empty string = set to None)
    - Save user, redirect to kid_badges

  **3. Add URL (core/urls.py):**

  Add to imports: KidBadgesView
  Add URL: path("kid/badges/", KidBadgesView.as_view(), name="kid_badges")

  **4. Add nav item (templates/base_kid.html):**

  Add a "Badges" nav item between "History" and "Settings" in the sidebar:
  ```html
  <li class="nav-item">
      <a href="{% url 'kid_badges' %}" class="nav-link {% block nav_badges_active %}{% endblock %}">
          <i class="nav-icon bi bi-award"></i>
          <p>Badges</p>
      </a>
  </li>
  ```

  **5. Create templates/core/kid_badges.html:**

  Extends base_kid.html. Sets nav_badges_active block.

  Layout:
  - Top section: "My Badges" title with earned_count/total_count progress
  - Active badge/title display section showing current selections with change buttons
  - For each category, a section with category name header
  - Grid of badge cards (4 columns on desktop, 2 on mobile)
  - Each badge card shows:
    - Earned: colorful background, emoji large, title bold, description, "Set as Badge" / "Set as Title" buttons (small, only on earned)
    - Unearned: greyed out (opacity 0.4, grayscale filter), emoji, title, description of what's needed
  - Active badge/title selection via form POST (hidden inputs for slug)

  Style: Match the existing kid settings aesthetic (#B19CD9 accent, pref-card style, rounded corners). Use Bootstrap grid. Badge cards should feel like collectible cards.

  Active badge/title selector:
  - Show current active badge emoji + title at top
  - "Set as Badge" button on each earned badge card submits a form to set active_badge
  - "Set as Title" button on each earned badge card submits a form to set active_title
  - "Clear" option for both

  **6. Update KidSettingsView (core/views.py):**

  In GET context, add:
  - unlocked_patterns: set of pattern slugs unlocked by user. Map achievement slugs to pattern values: unlock_stars -> "stars", unlock_polka -> "polka", unlock_stripes -> "stripes", unlock_waves -> "waves". Query UserAchievement for these slugs.
  - unlocked_fonts: same approach. unlock_rounded -> "rounded", unlock_handwritten -> "handwritten", unlock_pixel -> "pixel", unlock_comic -> "comic".
  - Pass unlocked_patterns and unlocked_fonts to template.

  In POST handler, validate pattern/font against unlocked set:
  - If bg_pattern is not "none" and bg_pattern not in unlocked_patterns, force to "none"
  - If font_style is not "default" and font_style not in unlocked_fonts, force to "default"

  **7. Update templates/core/kid_settings.html:**

  Modify Background Pattern section:
  - For each pattern option (except "none"), check if it's in unlocked_patterns
  - If locked: disable the radio input, add a lock icon (bi-lock-fill) and small text showing what's needed (e.g., "Complete 15 chores to unlock"). Grey out the option visually.
  - If unlocked: show as normal with a small unlock/check icon

  Modify Font Style section:
  - Same approach: check unlocked_fonts, disable locked options with lock icon and unlock criteria text
  - The "Default (Nunito)" option is always available

  Add criteria text mapping in the template context or as data attributes. The unlock criteria text should be human-readable:
  - Stars: "Complete 15 chores"
  - Polka Dots: "Get a 3-day streak"
  - Stripes: "Earn 1 hour of time"
  - Waves: "Complete 5 bonus chores"
  - Rounded: "Get a 7-day streak"
  - Handwritten: "Complete 50 chores"
  - Pixel: "Use timer 10 times"
  - Comic: "Earn 5 hours of time"
  </action>
  <verify>
  - `python manage.py runserver` starts without errors
  - Navigate to /kid/badges/ -- page loads showing all 54 achievements
  - Navigate to /kid/settings/ -- patterns and fonts show lock/unlock status
  - Complete a chore and verify achievement checking runs (check UserAchievement table)
  </verify>
  <done>
  - Badge gallery page at /kid/badges/ shows all achievements with earned/unearned visual states
  - Active badge and title can be set from the gallery page
  - Patterns and fonts are locked in settings until corresponding achievements are earned
  - Achievement checking runs automatically on chore completion and timer stop
  - "Badges" nav item appears in kid sidebar
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <what-built>Complete achievement system: 54 badges across 8 categories, badge gallery page, active badge/title selection, locked patterns/fonts in settings, auto-checking on chore completion and timer stop.</what-built>
  <how-to-verify>
    1. Log in as a kid user
    2. Navigate to Badges page via sidebar -- verify all 54 badges display in categorized grid
    3. Verify unearned badges appear greyed out with unlock criteria text
    4. Complete a chore from My Chores page
    5. Return to Badges page -- verify "Getting Started" (1 chore) badge is now earned (colorful)
    6. Click "Set as Badge" on an earned badge -- verify it sets as active badge shown at top
    7. Click "Set as Title" on an earned badge -- verify it sets as active title shown at top
    8. Navigate to Settings page
    9. Verify patterns (Stars, Polka, etc.) show lock icons with unlock criteria for ones not yet earned
    10. Verify fonts show lock icons similarly
    11. If any pattern/font IS unlocked (based on earned achievements), verify it can be selected normally
    12. Check that locked patterns/fonts cannot be selected (radio disabled)
  </how-to-verify>
  <resume-signal>Type "approved" or describe issues to fix</resume-signal>
</task>

</tasks>

<verification>
- All 54 achievements seeded in database
- Achievement checking triggers on chore completion and timer stop
- Badge gallery renders all badges with correct earned/unearned states
- Active badge and title can be set and cleared
- Patterns and fonts are locked until corresponding achievements earned
- Settings page enforces locks server-side (not just UI)
- No regressions to existing chore completion or timer stop flows
</verification>

<success_criteria>
- 54 Achievement records in database across 8 categories
- Kids earn badges automatically when meeting criteria
- Badge gallery page accessible at /kid/badges/ with sidebar nav link
- Active badge + title selectable and displayed
- Patterns locked until: Stars (15 chores), Polka (3-day streak), Stripes (1hr earned), Waves (5 bonus)
- Fonts locked until: Rounded (7-day streak), Handwritten (50 chores), Pixel (10 timer sessions), Comic (5hr earned)
- Settings page shows lock icons with human-readable unlock criteria
- Server-side validation prevents selecting locked patterns/fonts
</success_criteria>

<output>
After completion, create `.planning/quick/014-achievement-badges-titles-unlockables/014-SUMMARY.md`
</output>
