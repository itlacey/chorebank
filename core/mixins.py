"""Role-based access control mixins for ChoreBank views.

ParentRequiredMixin -- restricts to parent role
KidRequiredMixin    -- restricts to kid role

Both redirect unauthenticated users to the login page and return 403
for authenticated users who fail the role test (raise_exception=False
causes redirect-to-login for anonymous, 403 for wrong role).
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class ParentRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only allow authenticated users with the parent role."""

    raise_exception = False

    def test_func(self):
        return self.request.user.is_parent


class KidRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Only allow authenticated users with the kid role."""

    raise_exception = False

    def test_func(self):
        return self.request.user.is_kid
