"""Seed pre-built ChoreTemplate records for parent quick-create."""

from django.db import migrations

TEMPLATES = [
    # Morning
    ("Make Bed", "required", 5, 5, "morning"),
    ("Brush Teeth (Morning)", "required", 5, 5, "morning"),
    ("Get Dressed", "required", 5, 5, "morning"),
    ("Eat Breakfast", "required", 5, 5, "morning"),
    ("Feed Pet", "required", 10, 5, "morning"),
    # Afternoon
    ("Do Homework", "required", 15, 10, "afternoon"),
    ("Practice Instrument", "bonus", 15, 0, "afternoon"),
    ("Read for 20 Minutes", "bonus", 15, 0, "afternoon"),
    ("Clean Room", "required", 10, 10, "afternoon"),
    ("Put Away Laundry", "required", 10, 5, "afternoon"),
    # Evening
    ("Set Table", "required", 5, 5, "evening"),
    ("Clear Table", "required", 5, 5, "evening"),
    ("Brush Teeth (Evening)", "required", 5, 5, "evening"),
    ("Take Out Trash", "required", 10, 5, "evening"),
    ("Pack Backpack", "required", 5, 5, "evening"),
    ("Shower/Bath", "required", 10, 5, "evening"),
    # Bonus (any time)
    ("Help with Cooking", "bonus", 15, 0, "afternoon"),
    ("Extra Cleaning", "bonus", 20, 0, "afternoon"),
]


def seed_templates(apps, schema_editor):
    ChoreTemplate = apps.get_model("core", "ChoreTemplate")
    for name, chore_type, reward, penalty, time_of_day in TEMPLATES:
        ChoreTemplate.objects.get_or_create(
            name=name,
            defaults={
                "chore_type": chore_type,
                "suggested_reward_minutes": reward,
                "suggested_penalty_minutes": penalty,
                "suggested_time_of_day": time_of_day,
            },
        )


def remove_templates(apps, schema_editor):
    ChoreTemplate = apps.get_model("core", "ChoreTemplate")
    names = [t[0] for t in TEMPLATES]
    ChoreTemplate.objects.filter(name__in=names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_choretemplate_chore_choreinstance"),
    ]

    operations = [
        migrations.RunPython(seed_templates, remove_templates),
    ]
