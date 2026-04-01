"""Admin configuration for ChoreBank core models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Chore, ChoreInstance, ChoreTemplate, User


@admin.register(User)
class ChorebankUserAdmin(UserAdmin):
    """Custom admin for ChoreBank User with role and emoji fields."""

    list_display = ("username", "first_name", "role", "emoji_avatar")
    list_filter = ("role",)
    fieldsets = UserAdmin.fieldsets + (
        ("ChoreBank", {"fields": ("role", "emoji_avatar")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("ChoreBank", {"fields": ("role", "emoji_avatar")}),
    )


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    """Admin for Chore definitions."""

    list_display = (
        "name",
        "chore_type",
        "reward_minutes",
        "time_of_day",
        "recurrence_type",
        "is_active",
    )
    list_filter = ("chore_type", "time_of_day", "recurrence_type", "is_active")


@admin.register(ChoreInstance)
class ChoreInstanceAdmin(admin.ModelAdmin):
    """Admin for per-kid chore instances."""

    list_display = (
        "chore",
        "assigned_to",
        "due_date",
        "completed",
        "completed_at",
    )
    list_filter = ("completed", "due_date")


@admin.register(ChoreTemplate)
class ChoreTemplateAdmin(admin.ModelAdmin):
    """Admin for pre-built chore templates."""

    list_display = (
        "name",
        "chore_type",
        "suggested_reward_minutes",
        "suggested_time_of_day",
    )
    list_filter = ("chore_type", "suggested_time_of_day")
