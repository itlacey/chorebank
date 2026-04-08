"""
ChoreBank middleware.

TimezoneMiddleware: activates the browser's IANA timezone (sent via cookie)
so Django's localdate()/localtime() return values in the user's local time.
"""

import zoneinfo

from django.utils import timezone


class TimezoneMiddleware:
    """Activate Django timezone from the browser_tz cookie set by JS."""

    # Family is in Eastern Time -- sensible default when cookie is missing.
    DEFAULT_TZ = "America/New_York"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz_name = request.COOKIES.get("browser_tz", "").strip()
        try:
            tz = zoneinfo.ZoneInfo(tz_name) if tz_name else zoneinfo.ZoneInfo(self.DEFAULT_TZ)
        except (zoneinfo.ZoneInfoNotFoundError, KeyError, ValueError):
            tz = zoneinfo.ZoneInfo(self.DEFAULT_TZ)

        timezone.activate(tz)
        try:
            response = self.get_response(request)
        finally:
            timezone.deactivate()
        return response
