"""Core views for ChoreBank authentication.

LoginView       -- Card-picker login with emoji avatars + 4-digit PIN
LogoutView      -- POST-only logout (CSRF-safe)
PinChangeView   -- Logged-in user changes their own PIN
PinResetView    -- Parent resets a kid's PIN
"""

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from core.mixins import ParentRequiredMixin
from core.models import User
from core.validators import PinValidator


class LoginView(View):
    """Card-picker login: tap your card, enter 4-digit PIN."""

    def get(self, request):
        if request.user.is_authenticated:
            return self._redirect_home(request.user)
        users = User.objects.order_by("first_name")
        return render(request, "core/login.html", {"users": users})

    def post(self, request):
        username = request.POST.get("username", "").strip()
        pin = request.POST.get("pin", "").strip()
        user = authenticate(request, username=username, password=pin)
        if user is not None:
            login(request, user)
            return self._redirect_home(user)
        # Failed: re-render with error
        users = User.objects.order_by("first_name")
        return render(request, "core/login.html", {
            "users": users,
            "error": "Wrong PIN! Try again.",
            "selected_username": username,
        })

    @staticmethod
    def _redirect_home(user):
        """Redirect to role-appropriate home page."""
        if user.is_parent:
            return redirect("/parent/")
        return redirect("/kid/")


class LogoutView(View):
    """POST-only logout for CSRF safety."""

    def post(self, request):
        logout(request)
        return redirect("login")


class PinChangeView(View):
    """Let any logged-in user change their own PIN."""

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("login")
        return render(request, "core/pin_change.html")

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("login")

        current_pin = request.POST.get("current_pin", "").strip()
        new_pin = request.POST.get("new_pin", "").strip()
        confirm_pin = request.POST.get("confirm_pin", "").strip()

        # Validate current PIN
        if not request.user.check_password(current_pin):
            return render(request, "core/pin_change.html", {
                "error": "Current PIN is incorrect.",
            })

        # Validate new PINs match
        if new_pin != confirm_pin:
            return render(request, "core/pin_change.html", {
                "error": "New PINs don't match.",
            })

        # Must be different
        if new_pin == current_pin:
            return render(request, "core/pin_change.html", {
                "error": "New PIN must be different from your current PIN.",
            })

        # Validate PIN format
        validator = PinValidator()
        try:
            validator.validate(new_pin)
        except Exception as e:
            return render(request, "core/pin_change.html", {
                "error": e.messages[0] if hasattr(e, "messages") else str(e),
            })

        # All good -- change the PIN
        request.user.set_password(new_pin)
        request.user.save()
        update_session_auth_hash(request, request.user)
        messages.success(request, "PIN updated successfully!")
        return redirect("pin_change")


class PinResetView(ParentRequiredMixin, View):
    """Let a parent reset any kid's PIN."""

    def get(self, request):
        kids = User.objects.filter(role=User.Role.KID).order_by("first_name")
        return render(request, "core/pin_reset.html", {"kids": kids})

    def post(self, request):
        kid_id = request.POST.get("kid_id", "").strip()
        new_pin = request.POST.get("new_pin", "").strip()

        kid = get_object_or_404(User, pk=kid_id, role=User.Role.KID)

        # Validate PIN format
        validator = PinValidator()
        try:
            validator.validate(new_pin)
        except Exception as e:
            kids = User.objects.filter(role=User.Role.KID).order_by("first_name")
            return render(request, "core/pin_reset.html", {
                "kids": kids,
                "error": e.messages[0] if hasattr(e, "messages") else str(e),
                "selected_kid_id": kid.pk,
            })

        kid.set_password(new_pin)
        kid.save()
        messages.success(request, f"{kid.first_name}'s PIN has been reset!")
        return redirect("pin_reset")
