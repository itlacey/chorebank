"""Core models for ChoreBank.

Custom User model with role (parent/kid) and emoji avatar.
Must be set as AUTH_USER_MODEL before first migration.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with role and avatar for ChoreBank family members."""

    class Role(models.TextChoices):
        PARENT = "parent", "Parent"
        KID = "kid", "Kid"

    role = models.CharField(max_length=10, choices=Role.choices)
    emoji_avatar = models.CharField(max_length=10, default="\U0001f600")

    @property
    def is_parent(self):
        """Return True if user has parent role."""
        return self.role == self.Role.PARENT

    @property
    def is_kid(self):
        """Return True if user has kid role."""
        return self.role == self.Role.KID

    class Meta:
        db_table = "core_user"

    def __str__(self):
        return f"{self.emoji_avatar} {self.first_name}"
