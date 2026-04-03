"""Management command to bootstrap Django Q2 Schedule objects.

Creates (or updates) two schedules:
- process_penalties: every 5 minutes
- generate_chore_instances: daily at midnight
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule


class Command(BaseCommand):
    help = "Create or update Django Q2 scheduled tasks for ChoreBank"

    def handle(self, *args, **options):
        # Schedule 1: Penalty processing every 5 minutes
        _, created = Schedule.objects.update_or_create(
            name="process_penalties",
            defaults={
                "func": "core.tasks.process_penalties",
                "schedule_type": Schedule.MINUTES,
                "minutes": 5,
            },
        )
        status = "Created" if created else "Updated"
        self.stdout.write(f"{status} schedule: process_penalties (every 5 min)")

        # Schedule 2: Chore instance generation daily at midnight
        tomorrow_midnight = (
            timezone.localtime() + timedelta(days=1)
        ).replace(hour=0, minute=0, second=0, microsecond=0)

        _, created = Schedule.objects.update_or_create(
            name="generate_chore_instances",
            defaults={
                "func": "core.tasks.generate_chore_instances",
                "schedule_type": Schedule.DAILY,
                "next_run": tomorrow_midnight,
            },
        )
        status = "Created" if created else "Updated"
        self.stdout.write(
            f"{status} schedule: generate_chore_instances (daily at midnight)"
        )

        self.stdout.write(self.style.SUCCESS("Schedules configured successfully"))
