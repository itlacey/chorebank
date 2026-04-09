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


@register.filter
def contrast_text_color(hex_color, mode="text"):
    """Return a contrasting text color based on background luminance (WCAG 2.0).

    Usage: {{ bg_color|contrast_text_color:"sidebar-link" }}

    Modes:
      text (default)     - general text (#1a1a1a / #f0f0f0)
      sidebar-link       - sidebar nav links
      sidebar-link-hover - sidebar nav hover/active
      sidebar-hover-bg   - sidebar hover background
      sidebar-brand      - sidebar brand text
      sidebar-btn        - sidebar button text
      sidebar-btn-border - sidebar button border
    """
    if not hex_color or not isinstance(hex_color, str):
        return ""

    color = hex_color.strip().lstrip("#")
    if len(color) not in (3, 6):
        return ""

    try:
        if len(color) == 3:
            color = "".join(c * 2 for c in color)
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    except (ValueError, IndexError):
        return ""

    # sRGB to linear
    def linearize(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    luminance = 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
    is_light = luminance > 0.179

    # Light background -> dark text variants; dark background -> light text variants
    modes = {
        "text":              ("#1a1a1a",          "#f0f0f0"),
        "sidebar-link":      ("rgba(0,0,0,0.7)",  "rgba(255,255,255,0.85)"),
        "sidebar-link-hover":("rgba(0,0,0,0.9)",  "#fff"),
        "sidebar-hover-bg":  ("rgba(0,0,0,0.1)",  "rgba(255,255,255,0.15)"),
        "sidebar-brand":     ("#222",              "#fff"),
        "sidebar-btn":       ("rgba(0,0,0,0.6)",  "rgba(255,255,255,0.8)"),
        "sidebar-btn-border":("rgba(0,0,0,0.2)",  "rgba(255,255,255,0.3)"),
    }

    light_val, dark_val = modes.get(mode, modes["text"])
    return light_val if is_light else dark_val
