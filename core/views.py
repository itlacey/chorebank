"""Core views for ChoreBank.

LoginView              -- Card-picker login with emoji avatars + 4-digit PIN
LogoutView             -- POST-only logout (CSRF-safe)
PinChangeView          -- Logged-in user changes their own PIN
PinResetView           -- Parent resets a kid's PIN
HomeRouterView         -- Redirect authenticated users to role-appropriate home
KidHomeView            -- Kid landing page with greeting and balance
ParentHomeView         -- Parent landing page with kid overview cards
ParentChoreListView    -- List all active chores for parent management
ParentChoreCreateView  -- Create a new chore
ParentChoreEditView    -- Edit an existing chore (regenerates instances)
ParentChoreDeleteView  -- Soft-delete a chore
ChoreTemplateLoadView  -- JSON endpoint for template picker
"""

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import localdate
from django.views import View
from django.views.generic import TemplateView

from core.forms import ChoreForm
from core.mixins import KidRequiredMixin, ParentRequiredMixin
from core.models import Chore, ChoreTemplate, User
from core.tasks import generate_chore_instances
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
            return redirect("parent_home")
        return redirect("kid_home")


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


# ---------------------------------------------------------------------------
# Home / Landing pages
# ---------------------------------------------------------------------------


class HomeRouterView(LoginRequiredMixin, View):
    """Redirect authenticated users to their role-appropriate home page."""

    def get(self, request):
        if request.user.is_parent:
            return redirect("parent_home")
        return redirect("kid_home")


class KidHomeView(KidRequiredMixin, TemplateView):
    """Kid landing page -- personalized greeting and balance placeholder."""

    template_name = "core/kid_home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["first_name"] = user.first_name
        ctx["emoji_avatar"] = user.emoji_avatar
        ctx["balance"] = 0
        return ctx


class ParentHomeView(ParentRequiredMixin, TemplateView):
    """Parent landing page -- overview of all kids with placeholder balances."""

    template_name = "core/parent_home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        kids = User.objects.filter(role=User.Role.KID).order_by("first_name")
        ctx["kids"] = [
            {
                "first_name": kid.first_name,
                "emoji_avatar": kid.emoji_avatar,
                "balance": 0,
                "user": kid,
            }
            for kid in kids
        ]
        return ctx


# ---------------------------------------------------------------------------
# Parent Chore CRUD
# ---------------------------------------------------------------------------


class ParentChoreListView(ParentRequiredMixin, TemplateView):
    """List all active chores for parent management."""

    template_name = "core/chore_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["chores"] = (
            Chore.objects.filter(is_active=True)
            .prefetch_related("assigned_to")
            .order_by("time_of_day", "name")
        )
        return ctx


class ParentChoreCreateView(ParentRequiredMixin, View):
    """Create a new chore with form validation and instance generation."""

    def get(self, request):
        form = ChoreForm()
        templates_list = ChoreTemplate.objects.all()
        return render(request, "core/chore_form.html", {
            "form": form,
            "templates_list": templates_list,
            "editing": False,
        })

    def post(self, request):
        form = ChoreForm(request.POST)
        if form.is_valid():
            chore = form.save(commit=False)
            chore.created_by = request.user
            chore.save()
            form.save_m2m()
            # Generate instances for today + 7 days so kids see the chore now
            generate_chore_instances(target_date=localdate(), days_ahead=7)
            messages.success(request, f'Chore "{chore.name}" created!')
            return redirect("chore_list")
        templates_list = ChoreTemplate.objects.all()
        return render(request, "core/chore_form.html", {
            "form": form,
            "templates_list": templates_list,
            "editing": False,
        })


class ParentChoreEditView(ParentRequiredMixin, View):
    """Edit an existing chore. Regenerates instances after save."""

    def _get_chore(self, pk):
        chore = get_object_or_404(Chore, pk=pk)
        if not chore.is_active:
            raise Http404
        return chore

    def get(self, request, pk):
        chore = self._get_chore(pk)
        form = ChoreForm(instance=chore)
        templates_list = ChoreTemplate.objects.all()
        return render(request, "core/chore_form.html", {
            "form": form,
            "templates_list": templates_list,
            "editing": True,
            "chore": chore,
        })

    def post(self, request, pk):
        chore = self._get_chore(pk)
        form = ChoreForm(request.POST, instance=chore)
        if form.is_valid():
            chore = form.save(commit=False)
            chore.save()
            form.save_m2m()
            # Regenerate instances so schedule/assignment changes take effect
            generate_chore_instances(target_date=localdate(), days_ahead=7)
            messages.success(request, f'Chore "{chore.name}" updated!')
            return redirect("chore_list")
        templates_list = ChoreTemplate.objects.all()
        return render(request, "core/chore_form.html", {
            "form": form,
            "templates_list": templates_list,
            "editing": True,
            "chore": chore,
        })


class ParentChoreDeleteView(ParentRequiredMixin, View):
    """Soft-delete a chore (set is_active=False)."""

    def get(self, request, pk):
        chore = get_object_or_404(Chore, pk=pk, is_active=True)
        return render(request, "core/chore_confirm_delete.html", {
            "chore": chore,
        })

    def post(self, request, pk):
        chore = get_object_or_404(Chore, pk=pk, is_active=True)
        chore.is_active = False
        chore.save()
        messages.success(request, f'Chore "{chore.name}" deleted.')
        return redirect("chore_list")


class ChoreTemplateLoadView(ParentRequiredMixin, View):
    """Return template fields as JSON for the form template picker."""

    def get(self, request):
        template_id = request.GET.get("template_id")
        if not template_id:
            return JsonResponse({"error": "template_id required"}, status=400)
        template = get_object_or_404(ChoreTemplate, pk=template_id)
        return JsonResponse({
            "name": template.name,
            "chore_type": template.chore_type,
            "reward_minutes": template.suggested_reward_minutes,
            "penalty_minutes": template.suggested_penalty_minutes,
            "time_of_day": template.suggested_time_of_day,
        })
