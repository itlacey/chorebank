"""Custom template tags for ChoreBank.

bank_balance  -- Render a user's time-bank balance as a colored badge
user_avatar   -- Render a user's emoji avatar at a given size
"""

from django import template

from core.models import TimeBankTransaction, format_balance

register = template.Library()


@register.inclusion_tag("core/_balance_badge.html")
def bank_balance(user):
    """Render the user's time-bank balance as a colored badge."""
    balance = TimeBankTransaction.get_balance(user)
    display = format_balance(balance)

    # Color coding: green healthy, orange <15min, red zero/negative
    if balance <= 0:
        color_class = "bg-danger-subtle text-danger-emphasis"
    elif balance < 15:
        color_class = "bg-warning-subtle text-warning-emphasis"
    else:
        color_class = "bg-success-subtle text-success-emphasis"

    return {"display": display, "color_class": color_class, "balance": balance}


@register.inclusion_tag("core/_user_avatar.html")
def user_avatar(user, size="3rem"):
    """Render a user's emoji avatar at the given CSS size."""
    return {
        "emoji": user.emoji_avatar,
        "name": user.first_name,
        "size": size,
    }


@register.simple_tag
def streak_display(streak):
    """Return the streak number as a string for template display."""
    return str(streak)
