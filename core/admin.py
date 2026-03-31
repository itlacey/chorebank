"""Admin configuration for ChoreBank core models."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


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
