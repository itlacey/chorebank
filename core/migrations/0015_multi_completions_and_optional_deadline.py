from django.db import migrations, models


def backfill_completion_count(apps, schema_editor):
    """Existing ChoreInstance rows with completed=True get completion_count=1."""
    ChoreInstance = apps.get_model("core", "ChoreInstance")
    ChoreInstance.objects.filter(completed=True).update(completion_count=1)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_expand_unlockables"),
    ]

    operations = [
        migrations.AddField(
            model_name="chore",
            name="max_per_day",
            field=models.PositiveIntegerField(
                blank=True,
                default=1,
                null=True,
                help_text="1 = once a day, N = capped at N, NULL = unlimited.",
            ),
        ),
        migrations.AlterField(
            model_name="chore",
            name="deadline_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="choreinstance",
            name="completion_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(
            backfill_completion_count, migrations.RunPython.noop
        ),
    ]
