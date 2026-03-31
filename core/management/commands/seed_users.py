"""Management command to seed the 4 ChoreBank family member accounts.

Idempotent: safe to run on every deploy. Uses get_or_create so existing
accounts are never modified. Only sets the default PIN on newly created users.
"""

from django.core.management.base import BaseCommand

from core.models import User

FAMILY = [
    {"username": "ike", "first_name": "Ike", "role": "parent", "emoji_avatar": "\U0001f468"},
    {"username": "sami", "first_name": "Sami", "role": "parent", "emoji_avatar": "\U0001f469"},
    {"username": "zeke", "first_name": "Zeke", "role": "kid", "emoji_avatar": "\U0001f9b8\u200d\u2642\ufe0f"},
    {"username": "eli", "first_name": "Eli", "role": "kid", "emoji_avatar": "\U0001f9d9\u200d\u2642\ufe0f"},
]

DEFAULT_PIN = "1234"


class Command(BaseCommand):
    """Seed the 4 ChoreBank family member accounts."""

    help = "Create the 4 ChoreBank family members (idempotent)"

    def handle(self, *args, **options):
        for data in FAMILY:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "first_name": data["first_name"],
                    "role": data["role"],
                    "emoji_avatar": data["emoji_avatar"],
                },
            )
            if created:
                user.set_password(DEFAULT_PIN)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Created {data['first_name']} ({data['role']})")
                )
            else:
                self.stdout.write(f"{data['first_name']} already exists")
