"""Custom authentication backend for ChoreBank.

PINs are stored using Django's standard password hashing (via set_password).
This backend delegates to ModelBackend, which checks the hashed password.
The PIN is passed as the ``password`` argument to authenticate().
"""

from django.contrib.auth.backends import ModelBackend


class PinAuthBackend(ModelBackend):
    """Authenticate users by username + 4-digit PIN.

    PINs are hashed and stored in the standard ``password`` field.
    This backend simply inherits ModelBackend behaviour -- the only
    purpose of the subclass is to make intent explicit and to allow
    future PIN-specific logic (lockout, rate limiting, etc.).
    """

    pass
