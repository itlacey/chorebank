"""Background tasks for ChoreBank chore system.

generate_chore_instances is scheduled daily via Django Q2 to create
ChoreInstance records for each active chore and its assigned kids.
process_penalties runs every 5 minutes to penalize missed required chores.
"""

import calendar
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone
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
    elif chore.recurrence_type == Chore.RecurrenceType.MONTHLY:
        # Fire on same day-of-month as creation date.
        # End-of-month guard: if created on the 31st but target month
        # only has 28-30 days, fire on the last day of that month.
        created_day = chore.created_at.day
        last_day_of_month = calendar.monthrange(target_date.year, target_date.month)[1]
        target_day = min(created_day, last_day_of_month)
        return target_date.day == target_day
    elif chore.recurrence_type == Chore.RecurrenceType.CUSTOM:
        # Calculate based on interval from chore creation
        if not chore.recurrence_interval:
            return False
        delta = (target_date - chore.created_at.date()).days
        return delta % chore.recurrence_interval == 0
    elif chore.recurrence_type == Chore.RecurrenceType.ONCE:
        return target_date == chore.one_off_date
    return False


def process_penalties(target_date=None):
    """Apply penalty transactions for overdue, incomplete required chores.

    Finds all ChoreInstance records that are:
    - For required chores (only required chores have penalties)
    - Not completed
    - Not yet penalized (penalty_applied=False)
    - Past their deadline (due_date + deadline_time < now)
    - On active chores

    Uses select_for_update inside transaction.atomic to prevent races.
    No date filtering on due_date -- processes ALL overdue instances for
    catch-up after downtime. penalty_applied=False prevents double-processing.

    Returns count of penalties applied.
    """
    from core.models import ChoreInstance, TimeBankTransaction

    now = timezone.now()

    instances = (
        ChoreInstance.objects.filter(
            chore__chore_type="required",
            chore__is_active=True,
            completed=False,
            penalty_applied=False,
        )
        .select_related("chore")
    )

    penalty_count = 0
    for instance in instances:
        # Combine due_date + deadline_time into a timezone-aware datetime
        deadline_naive = datetime.combine(
            instance.due_date, instance.chore.deadline_time
        )
        deadline_aware = timezone.make_aware(deadline_naive)

        if now <= deadline_aware:
            continue  # Not yet overdue

        with transaction.atomic():
            # Re-fetch with lock to prevent double-processing
            locked = (
                ChoreInstance.objects.select_for_update()
                .filter(pk=instance.pk, penalty_applied=False)
                .first()
            )
            if not locked:
                continue  # Already processed by another worker

            TimeBankTransaction.objects.create(
                kid=locked.assigned_to,
                transaction_type=TimeBankTransaction.TransactionType.PENALTY,
                amount=-instance.chore.penalty_minutes,
                note=f"Missed: {instance.chore.name}",
                created_by=None,
                chore_instance=locked,
            )
            locked.penalty_applied = True
            locked.save(update_fields=["penalty_applied"])
            penalty_count += 1

    return penalty_count
