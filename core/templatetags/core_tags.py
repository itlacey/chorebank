"""Custom template tags for ChoreBank.

bank_balance  -- Render a user's time-bank balance (placeholder: 0 min)
user_avatar   -- Render a user's emoji avatar at a given size
"""

from django import template

register = template.Library()


@register.simple_tag
def bank_balance(user):
    """Return the user's time-bank balance as a formatted string.

    Placeholder implementation -- always returns '0 min'.
    Will be replaced with real balance lookup in Phase 3.
    """
    return "0 min"


@register.inclusion_tag("core/_user_avatar.html")
def user_avatar(user, size="3rem"):
    """Render a user's emoji avatar at the given CSS size."""
    return {
        "emoji": user.emoji_avatar,
        "name": user.first_name,
        "size": size,
    }
