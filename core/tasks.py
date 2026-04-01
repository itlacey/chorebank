"""Background tasks for ChoreBank chore system.

generate_chore_instances is scheduled daily via Django Q2 to create
ChoreInstance records for each active chore and its assigned kids.
"""

from datetime import timedelta

from django.utils.timezone import localdate


def generate_chore_instances(target_date=None, days_ahead=7):
    """Generate ChoreInstance records for target_date through target_date + days_ahead.

    Called by Django Q2 nightly schedule. Uses get_or_create for idempotency.
    Generates 7 days ahead to support the kid "upcoming" section and
    resilience to missed runs.
    """
    from core.models import Chore, ChoreInstance

    if target_date is None:
        target_date = localdate()

    created_count = 0
    for day_offset in range(days_ahead):
        check_date = target_date + timedelta(days=day_offset)
        chores = Chore.objects.filter(is_active=True).prefetch_related(
            "assigned_to"
        )
        for chore in chores:
            if not _is_due_on(chore, check_date):
                continue
            for kid in chore.assigned_to.all():
                _, created = ChoreInstance.objects.get_or_create(
                    chore=chore,
                    assigned_to=kid,
                    due_date=check_date,
                )
                if created:
                    created_count += 1
    return created_count


def _is_due_on(chore, target_date):
    """Check if a chore is due on the given date based on its recurrence."""
    from core.models import Chore

    if chore.recurrence_type == Chore.RecurrenceType.DAILY:
        return True
    elif chore.recurrence_type == Chore.RecurrenceType.WEEKLY:
        # recurrence_days stores "0,2,4" for Mon/Wed/Fri
        due_days = [int(d) for d in chore.recurrence_days.split(",") if d]
        return target_date.weekday() in due_days
    elif chore.recurrence_type == Chore.RecurrenceType.CUSTOM:
        # Calculate based on interval from chore creation
        if not chore.recurrence_interval:
            return False
        delta = (target_date - chore.created_at.date()).days
        return delta % chore.recurrence_interval == 0
    elif chore.recurrence_type == Chore.RecurrenceType.ONCE:
        return target_date == chore.one_off_date
    return False
