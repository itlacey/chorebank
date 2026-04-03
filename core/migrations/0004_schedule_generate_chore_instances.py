"""Register Django Q2 Schedule entry to run generate_chore_instances daily."""

from django.db import migrations


def create_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.get_or_create(
        func="core.tasks.generate_chore_instances",
        defaults={
            "name": "Generate daily chore instances",
            "schedule_type": "D",  # Schedule.DAILY
            "repeats": -1,  # Repeat forever
        },
    )


def remove_schedule(apps, schema_editor):
    Schedule = apps.get_model("django_q", "Schedule")
    Schedule.objects.filter(func="core.tasks.generate_chore_instances").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0003_seed_chore_templates"),
        ("django_q", "0018_task_success_index"),
    ]

    operations = [
        migrations.RunPython(create_schedule, remove_schedule),
    ]
