"""PIN validation for ChoreBank.

Enforces exactly 4-digit numeric PINs.
Registered via AUTH_PASSWORD_VALIDATORS in settings.
"""

from django.core.exceptions import ValidationError


class PinValidator:
    """Validate that the password is exactly 4 digits."""

    def validate(self, password, user=None):
        """Raise ValidationError if password is not a 4-digit PIN."""
        if not password.isdigit() or len(password) != 4:
            raise ValidationError(
                "PIN must be exactly 4 digits.",
                code="invalid_pin",
            )

    def get_help_text(self):
        """Return help text describing PIN requirements."""
        return "Your PIN must be exactly 4 digits."
