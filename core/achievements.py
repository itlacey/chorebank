"""Achievement definitions and checking logic for ChoreBank.

Defines ~54 achievements across 8 categories. Provides seed_achievements()
to populate the database and check_achievements(user) to evaluate and award
newly earned achievements.
"""

from django.db.models import Sum

ACHIEVEMENT_DEFINITIONS = [
    # === STREAKS (10) ===
    {"slug": "streak_1", "emoji": "\U0001f9b6", "title": "First Step", "description": "Complete a 1-day streak", "category": "streak", "criteria_type": "streak_current", "criteria_value": 1},
    {"slug": "streak_3", "emoji": "\U0001f4c5", "title": "Consistent", "description": "Complete a 3-day streak", "category": "streak", "criteria_type": "streak_current", "criteria_value": 3},
    {"slug": "streak_7", "emoji": "\U0001f525", "title": "Dedicated", "description": "Complete a 7-day streak", "category": "streak", "criteria_type": "streak_current", "criteria_value": 7},
    {"slug": "streak_14", "emoji": "\U0001f680", "title": "Unstoppable", "description": "Complete a 14-day streak", "category": "streak", "criteria_type": "streak_current", "criteria_value": 14},
    {"slug": "streak_30", "emoji": "\U0001f451", "title": "Legend", "description": "Complete a 30-day streak", "category": "streak", "criteria_type": "streak_current", "criteria_value": 30},
    {"slug": "comeback", "emoji": "\U0001f504", "title": "Comeback Kid", "description": "Rebuild a streak to 3+ after losing it", "category": "streak", "criteria_type": "comeback", "criteria_value": 3},
    {"slug": "weekend_warrior", "emoji": "\U0001f4c6", "title": "Weekend Warrior", "description": "Complete chores on both Sat & Sun for 4 weekends", "category": "streak", "criteria_type": "weekend_warrior", "criteria_value": 4},
    {"slug": "early_bird", "emoji": "\U0001f305", "title": "Early Bird", "description": "Complete 7 morning chores", "category": "streak", "criteria_type": "early_bird", "criteria_value": 7},
    {"slug": "night_owl", "emoji": "\U0001f989", "title": "Night Owl", "description": "Complete 7 evening chores", "category": "streak", "criteria_type": "night_owl", "criteria_value": 7},
    {"slug": "perfect_week", "emoji": "\u2B50", "title": "Perfect Week", "description": "Complete all required chores for 7 consecutive days", "category": "streak", "criteria_type": "perfect_week", "criteria_value": 7},

    # === CHORE_COUNT (8) ===
    {"slug": "chore_1", "emoji": "\U0001f331", "title": "Getting Started", "description": "Complete your first chore", "category": "chore_count", "criteria_type": "chore_total", "criteria_value": 1},
    {"slug": "chore_10", "emoji": "\U0001f91a", "title": "Helping Hand", "description": "Complete 10 chores", "category": "chore_count", "criteria_type": "chore_total", "criteria_value": 10},
    {"slug": "chore_25", "emoji": "\U0001f528", "title": "Hard Worker", "description": "Complete 25 chores", "category": "chore_count", "criteria_type": "chore_total", "criteria_value": 25},
    {"slug": "chore_50", "emoji": "\U0001f3c6", "title": "Chore Champion", "description": "Complete 50 chores", "category": "chore_count", "criteria_type": "chore_total", "criteria_value": 50},
    {"slug": "chore_100", "emoji": "\U0001f3c5", "title": "Chore Master", "description": "Complete 100 chores", "category": "chore_count", "criteria_type": "chore_total", "criteria_value": 100},
    {"slug": "chore_250", "emoji": "\U0001f48E", "title": "Chore Legend", "description": "Complete 250 chores", "category": "chore_count", "criteria_type": "chore_total", "criteria_value": 250},
    {"slug": "chore_500", "emoji": "\U0001f3d4\uFE0F", "title": "Chore Titan", "description": "Complete 500 chores", "category": "chore_count", "criteria_type": "chore_total", "criteria_value": 500},
    {"slug": "chore_1000", "emoji": "\u26A1", "title": "Chore God", "description": "Complete 1000 chores", "category": "chore_count", "criteria_type": "chore_total", "criteria_value": 1000},

    # === TIME_EARNED (8) ===
    {"slug": "time_earn_10", "emoji": "\u231B", "title": "First Minutes", "description": "Earn 10 minutes of screen time", "category": "time_earned", "criteria_type": "time_earned_minutes", "criteria_value": 10},
    {"slug": "time_earn_30", "emoji": "\U0001f570\uFE0F", "title": "Time Saver", "description": "Earn 30 minutes of screen time", "category": "time_earned", "criteria_type": "time_earned_minutes", "criteria_value": 30},
    {"slug": "time_earn_60", "emoji": "\U0001f9b8", "title": "Hour Hero", "description": "Earn 1 hour of screen time", "category": "time_earned", "criteria_type": "time_earned_minutes", "criteria_value": 60},
    {"slug": "time_earn_120", "emoji": "\U0001f4b0", "title": "Time Rich", "description": "Earn 2 hours of screen time", "category": "time_earned", "criteria_type": "time_earned_minutes", "criteria_value": 120},
    {"slug": "time_earn_300", "emoji": "\U0001f3A9", "title": "Time Baron", "description": "Earn 5 hours of screen time", "category": "time_earned", "criteria_type": "time_earned_minutes", "criteria_value": 300},
    {"slug": "time_earn_600", "emoji": "\U0001f4C8", "title": "Time Tycoon", "description": "Earn 10 hours of screen time", "category": "time_earned", "criteria_type": "time_earned_minutes", "criteria_value": 600},
    {"slug": "time_earn_1440", "emoji": "\U0001f3E2", "title": "Time Mogul", "description": "Earn 24 hours of screen time", "category": "time_earned", "criteria_type": "time_earned_minutes", "criteria_value": 1440},
    {"slug": "time_earn_6000", "emoji": "\U0001f30D", "title": "Time Billionaire", "description": "Earn 100 hours of screen time", "category": "time_earned", "criteria_type": "time_earned_minutes", "criteria_value": 6000},

    # === TIME_USED (5) ===
    {"slug": "timer_1", "emoji": "\U0001f4FA", "title": "Screen Starter", "description": "Use the timer for the first time", "category": "time_used", "criteria_type": "timer_sessions", "criteria_value": 1},
    {"slug": "timer_30min", "emoji": "\U0001f37F", "title": "Movie Time", "description": "Use a single 30+ minute timer session", "category": "time_used", "criteria_type": "timer_long_session", "criteria_value": 30},
    {"slug": "timer_60min", "emoji": "\U0001f3C3", "title": "Marathon", "description": "Use a single 60+ minute timer session", "category": "time_used", "criteria_type": "timer_long_session", "criteria_value": 60},
    {"slug": "timer_10", "emoji": "\U0001f3AE", "title": "Timer Pro", "description": "Use the timer 10 times", "category": "time_used", "criteria_type": "timer_sessions", "criteria_value": 10},
    {"slug": "timer_50", "emoji": "\U0001f579\uFE0F", "title": "Timer Veteran", "description": "Use the timer 50 times", "category": "time_used", "criteria_type": "timer_sessions", "criteria_value": 50},

    # === BONUS (5) ===
    {"slug": "bonus_1", "emoji": "\u2795", "title": "Extra Mile", "description": "Complete your first bonus chore", "category": "bonus", "criteria_type": "bonus_total", "criteria_value": 1},
    {"slug": "bonus_5", "emoji": "\U0001f4AA", "title": "Overachiever", "description": "Complete 5 bonus chores", "category": "bonus", "criteria_type": "bonus_total", "criteria_value": 5},
    {"slug": "bonus_10", "emoji": "\U0001f4BC", "title": "Bonus Boss", "description": "Complete 10 bonus chores", "category": "bonus", "criteria_type": "bonus_total", "criteria_value": 10},
    {"slug": "bonus_25", "emoji": "\U0001f4A0", "title": "Bonus Legend", "description": "Complete 25 bonus chores", "category": "bonus", "criteria_type": "bonus_total", "criteria_value": 25},
    {"slug": "bonus_50", "emoji": "\U0001f308", "title": "Above and Beyond", "description": "Complete 50 bonus chores", "category": "bonus", "criteria_type": "bonus_total", "criteria_value": 50},

    # === SPEED (4) ===
    {"slug": "speed_1", "emoji": "\U0001f3C3\u200D\u2642\uFE0F", "title": "Quick Finisher", "description": "Complete a chore before deadline", "category": "speed", "criteria_type": "chore_early", "criteria_value": 1},
    {"slug": "speed_5", "emoji": "\U0001f4A8", "title": "Speed Demon", "description": "Complete 5 chores before deadline", "category": "speed", "criteria_type": "chore_early", "criteria_value": 5},
    {"slug": "speed_10", "emoji": "\u26A1", "title": "Lightning", "description": "Complete 10 chores before deadline", "category": "speed", "criteria_type": "chore_early", "criteria_value": 10},
    {"slug": "speed_25", "emoji": "\u2B50", "title": "Flash", "description": "Complete 25 chores before deadline", "category": "speed", "criteria_type": "chore_early", "criteria_value": 25},

    # === VARIETY (5) ===
    {"slug": "variety_3", "emoji": "\U0001f9ED", "title": "Explorer", "description": "Complete 3 different types of chores", "category": "variety", "criteria_type": "chore_variety", "criteria_value": 3},
    {"slug": "variety_5", "emoji": "\U0001f3AF", "title": "Well-Rounded", "description": "Complete 5 different types of chores", "category": "variety", "criteria_type": "chore_variety", "criteria_value": 5},
    {"slug": "variety_10", "emoji": "\U0001f527", "title": "Jack of All Trades", "description": "Complete 10 different types of chores", "category": "variety", "criteria_type": "chore_variety", "criteria_value": 10},
    {"slug": "variety_15", "emoji": "\U0001f3A8", "title": "Renaissance Kid", "description": "Complete 15 different types of chores", "category": "variety", "criteria_type": "chore_variety", "criteria_value": 15},
    {"slug": "variety_20", "emoji": "\u267E\uFE0F", "title": "Master of All", "description": "Complete 20 different types of chores", "category": "variety", "criteria_type": "chore_variety", "criteria_value": 20},

    # === UNLOCKABLE (8) - unlock patterns/fonts ===
    {"slug": "unlock_stars", "emoji": "\u2B50", "title": "Pattern: Stars", "description": "Complete 15 chores to unlock Stars pattern", "category": "unlockable", "criteria_type": "chore_total", "criteria_value": 15},
    {"slug": "unlock_polka", "emoji": "\u26AA", "title": "Pattern: Polka Dots", "description": "Get a 3-day streak to unlock Polka Dots pattern", "category": "unlockable", "criteria_type": "streak_current", "criteria_value": 3},
    {"slug": "unlock_stripes", "emoji": "\U0001f4B2", "title": "Pattern: Stripes", "description": "Earn 1 hour of time to unlock Stripes pattern", "category": "unlockable", "criteria_type": "time_earned_minutes", "criteria_value": 60},
    {"slug": "unlock_waves", "emoji": "\U0001f30A", "title": "Pattern: Waves", "description": "Complete 5 bonus chores to unlock Waves pattern", "category": "unlockable", "criteria_type": "bonus_total", "criteria_value": 5},
    {"slug": "unlock_rounded", "emoji": "\U0001f4AC", "title": "Font: Rounded", "description": "Get a 7-day streak to unlock Rounded font", "category": "unlockable", "criteria_type": "streak_current", "criteria_value": 7},
    {"slug": "unlock_handwritten", "emoji": "\U0001f58A\uFE0F", "title": "Font: Handwritten", "description": "Complete 50 chores to unlock Handwritten font", "category": "unlockable", "criteria_type": "chore_total", "criteria_value": 50},
    {"slug": "unlock_pixel", "emoji": "\U0001f3AE", "title": "Font: Pixel", "description": "Use timer 10 times to unlock Pixel font", "category": "unlockable", "criteria_type": "timer_sessions", "criteria_value": 10},
    {"slug": "unlock_comic", "emoji": "\U0001f4AC", "title": "Font: Comic", "description": "Earn 5 hours of time to unlock Comic font", "category": "unlockable", "criteria_type": "time_earned_minutes", "criteria_value": 300},
]


def seed_achievements():
    """Populate Achievement table from definitions. Idempotent via update_or_create."""
    from core.models import Achievement

    for defn in ACHIEVEMENT_DEFINITIONS:
        Achievement.objects.update_or_create(
            slug=defn["slug"],
            defaults={
                "emoji": defn["emoji"],
                "title": defn["title"],
                "description": defn["description"],
                "category": defn["category"],
                "criteria_type": defn["criteria_type"],
                "criteria_value": defn["criteria_value"],
            },
        )


def check_achievements(user):
    """Check and award any newly earned achievements for a user.

    Computes stats lazily -- only queries DB for categories with unearned achievements.
    Returns list of newly earned Achievement objects.
    """
    from collections import defaultdict
    from datetime import timedelta

    from django.utils.timezone import localdate

    from core.models import (
        Achievement,
        ChoreInstance,
        TimeBankTransaction,
        TimerSession,
        UserAchievement,
    )

    # Get all achievement slugs user has already earned
    earned_slugs = set(
        UserAchievement.objects.filter(user=user).values_list(
            "achievement__slug", flat=True
        )
    )

    # Get unearned achievements grouped by criteria_type
    unearned = Achievement.objects.exclude(slug__in=earned_slugs)
    if not unearned.exists():
        return []

    # Group by criteria_type
    by_criteria = defaultdict(list)
    for ach in unearned:
        by_criteria[ach.criteria_type].append(ach)

    # Compute stats lazily
    stats_cache = {}

    def get_stat(criteria_type):
        if criteria_type in stats_cache:
            return stats_cache[criteria_type]

        val = 0
        if criteria_type == "streak_current":
            val = ChoreInstance.get_streak(user)
        elif criteria_type == "chore_total":
            val = ChoreInstance.objects.filter(
                assigned_to=user, completed=True
            ).count()
        elif criteria_type == "time_earned_minutes":
            val = (
                TimeBankTransaction.objects.filter(
                    kid=user, transaction_type="earn"
                ).aggregate(total=Sum("amount"))["total"]
                or 0
            )
        elif criteria_type == "timer_sessions":
            val = TimerSession.objects.filter(
                kid=user, ended_at__isnull=False
            ).count()
        elif criteria_type == "bonus_total":
            val = ChoreInstance.objects.filter(
                assigned_to=user, completed=True, chore__chore_type="bonus"
            ).count()
        elif criteria_type == "chore_early":
            # Completed before deadline_time on due_date
            early_count = 0
            early_instances = ChoreInstance.objects.filter(
                assigned_to=user, completed=True, completed_at__isnull=False
            ).select_related("chore")
            for inst in early_instances:
                if (
                    inst.completed_at
                    and inst.completed_at.date() == inst.due_date
                    and inst.chore.deadline_time
                    and inst.completed_at.time() < inst.chore.deadline_time
                ):
                    early_count += 1
            val = early_count
        elif criteria_type == "chore_variety":
            val = (
                ChoreInstance.objects.filter(assigned_to=user, completed=True)
                .values("chore__name")
                .distinct()
                .count()
            )
        elif criteria_type == "early_bird":
            val = ChoreInstance.objects.filter(
                assigned_to=user, completed=True, chore__time_of_day="morning"
            ).count()
        elif criteria_type == "night_owl":
            val = ChoreInstance.objects.filter(
                assigned_to=user, completed=True, chore__time_of_day="evening"
            ).count()
        elif criteria_type == "timer_long_session":
            # Check longest single session in minutes
            sessions = TimerSession.objects.filter(
                kid=user, ended_at__isnull=False
            )
            max_mins = 0
            for s in sessions:
                mins = s.actual_minutes
                if mins > max_mins:
                    max_mins = mins
            val = max_mins
        elif criteria_type == "perfect_week":
            # Check if user has 7 consecutive days with all required chores done
            today = localdate()
            val = 0
            consecutive = 0
            for i in range(30, -1, -1):
                d = today - timedelta(days=i)
                instances = ChoreInstance.objects.filter(
                    assigned_to=user,
                    due_date=d,
                    chore__chore_type="required",
                )
                total = instances.count()
                if total == 0:
                    continue  # no required chores, skip
                done = instances.filter(completed=True).count()
                if done >= total:
                    consecutive += 1
                    if consecutive >= 7:
                        val = 7
                        break
                else:
                    consecutive = 0
        elif criteria_type == "weekend_warrior":
            # Count weekends where both Sat+Sun had all required chores done
            today = localdate()
            weekend_count = 0
            for w in range(12):  # check last 12 weeks
                sat = today - timedelta(days=today.weekday() + 2 + w * 7)
                sun = sat + timedelta(days=1)
                sat_ok = _all_required_done(user, sat)
                sun_ok = _all_required_done(user, sun)
                if sat_ok and sun_ok:
                    weekend_count += 1
            val = weekend_count
        elif criteria_type == "comeback":
            # Check if user had streak of 0 at some point and now has 3+
            current_streak = ChoreInstance.get_streak(user)
            if current_streak >= 3:
                # Check if there's a gap (missed day) in history
                today = localdate()
                had_miss = False
                for i in range(1, 31):
                    d = today - timedelta(days=i)
                    instances = ChoreInstance.objects.filter(
                        assigned_to=user,
                        due_date=d,
                        chore__chore_type="required",
                    )
                    total = instances.count()
                    if total == 0:
                        continue
                    done = instances.filter(completed=True).count()
                    if done < total:
                        had_miss = True
                        break
                val = current_streak if had_miss else 0
            else:
                val = 0

        stats_cache[criteria_type] = val
        return val

    # Check each unearned achievement
    newly_earned = []
    for criteria_type, achievements in by_criteria.items():
        # timer_long_session needs special handling per-achievement
        if criteria_type == "timer_long_session":
            sessions = TimerSession.objects.filter(
                kid=user, ended_at__isnull=False
            )
            session_minutes = [s.actual_minutes for s in sessions]
            for ach in achievements:
                if any(m >= ach.criteria_value for m in session_minutes):
                    newly_earned.append(ach)
        else:
            stat_val = get_stat(criteria_type)
            for ach in achievements:
                if stat_val >= ach.criteria_value:
                    newly_earned.append(ach)

    # Create UserAchievement records
    created = []
    for ach in newly_earned:
        obj, was_created = UserAchievement.objects.get_or_create(
            user=user, achievement=ach
        )
        if was_created:
            created.append(ach)

    return created


def _all_required_done(user, date):
    """Check if all required chores for a date are completed."""
    from core.models import ChoreInstance

    instances = ChoreInstance.objects.filter(
        assigned_to=user,
        due_date=date,
        chore__chore_type="required",
    )
    total = instances.count()
    if total == 0:
        return False  # no chores = not a valid weekend day
    done = instances.filter(completed=True).count()
    return done >= total
