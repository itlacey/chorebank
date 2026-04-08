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
KidChoreListView       -- Kid chore list grouped by time of day
CompleteChoreView      -- HTMX one-tap chore completion
TimerPageView          -- Timer page with setup/resume state
TimerStartView         -- Start timer session with optimistic SPEND
TimerStopView          -- Stop timer session with ADJUST refund
TimeAdjustView         -- Parent manual time bank adjustment
TransactionHistoryView -- Transaction history with kid filter and HTMX pagination
ChoreLogView           -- Chore completion log with kid filter and HTMX pagination
BalanceBadgeView       -- HTMX partial returning updated balance badge
"""

from collections import OrderedDict
from datetime import timedelta

import json
import math

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import localdate
from django.views import View
from django.views.generic import TemplateView

from core.forms import ChoreForm, TimeAdjustForm
from core.mixins import KidRequiredMixin, ParentRequiredMixin
from core.models import (
    Chore,
    ChoreInstance,
    ChoreTemplate,
    TimeBankTransaction,
    TimeRequest,
    TimerSession,
    User,
    format_balance,
)
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
        ctx["balance"] = TimeBankTransaction.get_balance(user)
        ctx["balance_display"] = format_balance(ctx["balance"])
        ctx["streak"] = ChoreInstance.get_streak(user)
        ctx["longest_streak"] = ChoreInstance.get_longest_streak(user)
        return ctx


class ParentHomeView(ParentRequiredMixin, TemplateView):
    """Parent dashboard -- kid overview cards with balance, transactions, chore progress."""

    template_name = "core/parent_home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = localdate()
        kids = list(User.objects.filter(role=User.Role.KID).order_by("first_name"))
        kid_pks = [k.pk for k in kids]

        # Bulk-fetch last 3 transactions per kid
        # We fetch all recent transactions and slice per kid in Python
        all_txns = list(
            TimeBankTransaction.objects.filter(kid__in=kid_pks)
            .select_related("chore_instance__chore")
            .order_by("kid_id", "-created_at")
        )
        txns_by_kid = {}
        for txn in all_txns:
            txns_by_kid.setdefault(txn.kid_id, [])
            if len(txns_by_kid[txn.kid_id]) < 3:
                txns_by_kid[txn.kid_id].append(txn)

        # Bulk-fetch chore counts for today
        today_instances = list(
            ChoreInstance.objects.filter(
                assigned_to__in=kid_pks, due_date=today
            ).values_list("assigned_to_id", "completed")
        )
        chores_total_by_kid = {}
        chores_done_by_kid = {}
        for kid_id, completed in today_instances:
            chores_total_by_kid[kid_id] = chores_total_by_kid.get(kid_id, 0) + 1
            if completed:
                chores_done_by_kid[kid_id] = chores_done_by_kid.get(kid_id, 0) + 1

        # Bulk-fetch weekly chore counts (Monday through today)
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_instances = list(
            ChoreInstance.objects.filter(
                assigned_to__in=kid_pks, due_date__gte=week_start, due_date__lte=today
            ).values_list("assigned_to_id", "completed")
        )
        weekly_total_by_kid = {}
        weekly_done_by_kid = {}
        for kid_id, completed in week_instances:
            weekly_total_by_kid[kid_id] = weekly_total_by_kid.get(kid_id, 0) + 1
            if completed:
                weekly_done_by_kid[kid_id] = weekly_done_by_kid.get(kid_id, 0) + 1

        kid_cards = []
        for kid in kids:
            balance = TimeBankTransaction.get_balance(kid)
            if balance >= 15:
                balance_color = "text-success"
            elif balance > 0:
                balance_color = "text-warning"
            else:
                balance_color = "text-danger"
            kid_cards.append({
                "first_name": kid.first_name,
                "emoji_avatar": kid.emoji_avatar,
                "balance": balance,
                "balance_display": format_balance(balance),
                "balance_color": balance_color,
                "recent_transactions": txns_by_kid.get(kid.pk, []),
                "chores_today_total": chores_total_by_kid.get(kid.pk, 0),
                "chores_today_done": chores_done_by_kid.get(kid.pk, 0),
                "weekly_total": weekly_total_by_kid.get(kid.pk, 0),
                "weekly_done": weekly_done_by_kid.get(kid.pk, 0),
                "streak": ChoreInstance.get_streak(kid),
                "longest_streak": ChoreInstance.get_longest_streak(kid),
                "user": kid,
            })
        ctx["kids"] = kid_cards
        ctx["time_requests"] = TimeRequest.objects.filter(
            dismissed=False
        ).select_related("kid")[:10]
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
        ctx["templates_list"] = ChoreTemplate.objects.all()
        ctx["kids"] = User.objects.filter(role=User.Role.KID).order_by("first_name")
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


class QuickAddChoreView(ParentRequiredMixin, View):
    """Create a chore from a template with minimal input."""

    DEADLINE_DEFAULTS = {
        "morning": "09:00",
        "afternoon": "14:00",
        "evening": "19:00",
    }

    def post(self, request):
        from datetime import time as dt_time

        template_id = request.POST.get("template_id")
        kid_ids = request.POST.getlist("assigned_to")
        recurrence_type = request.POST.get("recurrence_type", "daily")

        if not template_id or not kid_ids:
            messages.error(request, "Please select a template and at least one kid.")
            return redirect("chore_list")

        tmpl = get_object_or_404(ChoreTemplate, pk=template_id)

        # Derive deadline from time_of_day
        deadline_str = self.DEADLINE_DEFAULTS.get(tmpl.suggested_time_of_day, "12:00")
        h, m = deadline_str.split(":")
        deadline = dt_time(int(h), int(m))

        chore = Chore.objects.create(
            name=tmpl.name,
            chore_type=tmpl.chore_type,
            reward_minutes=tmpl.suggested_reward_minutes,
            penalty_minutes=tmpl.suggested_penalty_minutes,
            time_of_day=tmpl.suggested_time_of_day,
            deadline_time=deadline,
            recurrence_type=recurrence_type,
            created_by=request.user,
        )

        kids = User.objects.filter(pk__in=kid_ids, role=User.Role.KID)
        chore.assigned_to.set(kids)

        # Generate instances for the next 7 days
        generate_chore_instances(target_date=localdate(), days_ahead=7)

        messages.success(request, f'Chore "{chore.name}" created from template!')
        return redirect("chore_list")


# ---------------------------------------------------------------------------
# Kid Chore Views
# ---------------------------------------------------------------------------


class KidChoreListView(KidRequiredMixin, TemplateView):
    """Kid chore list grouped by Morning / Afternoon / Evening with upcoming."""

    template_name = "core/kid_chore_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = localdate()
        user = self.request.user

        # Today's chores grouped by time of day
        todays = (
            ChoreInstance.objects.filter(
                assigned_to=user,
                due_date=today,
            )
            .select_related("chore")
            .order_by("chore__time_of_day", "chore__deadline_time")
        )

        morning_chores = []
        afternoon_chores = []
        evening_chores = []
        for inst in todays:
            tod = inst.chore.time_of_day
            if tod == Chore.TimeOfDay.MORNING:
                morning_chores.append(inst)
            elif tod == Chore.TimeOfDay.AFTERNOON:
                afternoon_chores.append(inst)
            else:
                evening_chores.append(inst)

        # Upcoming chores: next 7 days (excluding today)
        upcoming_qs = (
            ChoreInstance.objects.filter(
                assigned_to=user,
                due_date__gt=today,
                due_date__lte=today + timedelta(days=7),
            )
            .select_related("chore")
            .order_by("due_date", "chore__time_of_day", "chore__deadline_time")
        )

        # Group upcoming by date (OrderedDict preserves insertion order)
        upcoming_by_date = OrderedDict()
        for inst in upcoming_qs:
            upcoming_by_date.setdefault(inst.due_date, []).append(inst)

        ctx.update({
            "today": today,
            "tomorrow": today + timedelta(days=1),
            "morning_chores": morning_chores,
            "afternoon_chores": afternoon_chores,
            "evening_chores": evening_chores,
            "upcoming_by_date": upcoming_by_date,
            "streak": ChoreInstance.get_streak(user),
        })
        return ctx


class CompleteChoreView(KidRequiredMixin, View):
    """One-tap HTMX chore completion. Returns partial for swap."""

    def post(self, request, instance_id):
        instance = get_object_or_404(
            ChoreInstance,
            pk=instance_id,
            assigned_to=request.user,
            completed=False,
        )
        instance.completed = True
        instance.completed_at = timezone.now()
        instance.save()

        # Create EARN transaction for chore completion
        if instance.chore.reward_minutes > 0:
            TimeBankTransaction.objects.create(
                kid=request.user,
                transaction_type=TimeBankTransaction.TransactionType.EARN,
                amount=instance.chore.reward_minutes,
                note=f"Completed: {instance.chore.name}",
                created_by=request.user,
                chore_instance=instance,
            )

        response = render(
            request, "core/_chore_item.html", {"instance": instance}
        )
        response["HX-Trigger"] = "chore-completed"
        return response


class BalanceBadgeView(KidRequiredMixin, View):
    """HTMX partial returning the current balance badge for the navbar."""

    def get(self, request):
        balance = TimeBankTransaction.get_balance(request.user)
        display = format_balance(balance)

        if balance <= 0:
            color_class = "bg-danger-subtle text-danger-emphasis"
        elif balance < 15:
            color_class = "bg-warning-subtle text-warning-emphasis"
        else:
            color_class = "bg-success-subtle text-success-emphasis"

        return render(
            request,
            "core/_balance_badge.html",
            {"display": display, "color_class": color_class, "balance": balance},
        )


# ---------------------------------------------------------------------------
# Timer Views
# ---------------------------------------------------------------------------


class TimerPageView(KidRequiredMixin, TemplateView):
    """Timer page with setup state and active-session resume."""

    template_name = "core/timer.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        now = timezone.now()

        # Auto-close stale sessions (past expected end, still open)
        stale_sessions = TimerSession.objects.filter(
            kid=user, ended_at__isnull=True
        )
        for session in stale_sessions:
            expected_end = session.started_at + timedelta(
                minutes=session.requested_minutes,
                seconds=session.paused_seconds,
            )
            # If currently paused, add ongoing pause time
            if session.paused_at:
                expected_end += now - session.paused_at
            if expected_end < now:
                session.ended_at = expected_end
                session.ended_reason = "timer_expired"
                session.save()

        # Check for an active session (still running)
        active_session = (
            TimerSession.objects.filter(kid=user, ended_at__isnull=True)
            .first()
        )
        if active_session:
            expected_end = active_session.started_at + timedelta(
                minutes=active_session.requested_minutes,
                seconds=active_session.paused_seconds,
            )
            if active_session.paused_at:
                # Currently paused -- add ongoing pause duration to expected end
                expected_end += now - active_session.paused_at
                ctx["is_paused"] = True
                ctx["paused_seconds"] = active_session.paused_seconds + int(
                    (now - active_session.paused_at).total_seconds()
                )
            if expected_end > now:
                ctx["active_session"] = active_session
                ctx["active_session_end_time_ms"] = int(
                    expected_end.timestamp() * 1000
                )

        balance = TimeBankTransaction.get_balance(user)
        ctx["balance"] = balance
        ctx["balance_display"] = format_balance(balance)
        return ctx


class TimerStartView(KidRequiredMixin, View):
    """Start a timer session with optimistic SPEND transaction."""

    def post(self, request):
        try:
            data = json.loads(request.body)
            minutes = int(data.get("minutes", 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            return JsonResponse({"error": "Invalid request"}, status=400)

        if minutes < 1 or minutes > 480:
            return JsonResponse(
                {"error": "Minutes must be between 1 and 480"}, status=400
            )

        with transaction.atomic():
            balance = TimeBankTransaction.get_balance(request.user)
            if balance <= 0 or balance < minutes:
                return JsonResponse(
                    {"error": "Not enough balance"}, status=400
                )

            # Prevent double-start
            if TimerSession.objects.filter(
                kid=request.user, ended_at__isnull=True
            ).exists():
                return JsonResponse(
                    {"error": "Timer already running"}, status=400
                )

            # Optimistic SPEND deduction
            spend_txn = TimeBankTransaction.objects.create(
                kid=request.user,
                transaction_type="spend",
                amount=-minutes,
                note=f"Timer: {minutes}m session",
                created_by=request.user,
            )

            now = timezone.now()
            session = TimerSession.objects.create(
                kid=request.user,
                requested_minutes=minutes,
                started_at=now,
                spend_transaction=spend_txn,
            )

            end_time_ms = int(
                (now + timedelta(minutes=minutes)).timestamp() * 1000
            )
            new_balance = TimeBankTransaction.get_balance(request.user)

        return JsonResponse({
            "ok": True,
            "session_id": session.pk,
            "end_time_ms": end_time_ms,
            "balance": new_balance,
            "balance_display": format_balance(new_balance),
        })


class TimerStopView(KidRequiredMixin, View):
    """Stop an active timer session and refund unused time."""

    def post(self, request):
        session = get_object_or_404(
            TimerSession, kid=request.user, ended_at__isnull=True
        )

        now = timezone.now()

        # If currently paused, finalize the pause duration
        if session.paused_at:
            session.paused_seconds += int(
                (now - session.paused_at).total_seconds()
            )
            session.paused_at = None

        session.ended_at = now
        session.ended_reason = "manual"
        session.save()

        total_elapsed = (session.ended_at - session.started_at).total_seconds()
        used_seconds = total_elapsed - session.paused_seconds
        used_minutes = math.ceil(used_seconds / 60)
        unused = session.requested_minutes - used_minutes

        if unused > 0:
            TimeBankTransaction.objects.create(
                kid=request.user,
                transaction_type="adjust",
                amount=unused,
                note=f"Refund: {unused}m unused from {session.requested_minutes}m session",
                created_by=request.user,
            )

        new_balance = TimeBankTransaction.get_balance(request.user)
        return JsonResponse({
            "ok": True,
            "used_minutes": used_minutes,
            "refunded_minutes": max(0, unused),
            "balance": new_balance,
            "balance_display": format_balance(new_balance),
        })


class TimerPauseView(KidRequiredMixin, View):
    """Pause an active timer session."""

    def post(self, request):
        session = TimerSession.objects.filter(
            kid=request.user, ended_at__isnull=True, paused_at__isnull=True
        ).first()
        if not session:
            return JsonResponse({"error": "No active running session"}, status=400)

        session.paused_at = timezone.now()
        session.save()
        return JsonResponse({"ok": True, "paused": True})


class TimerResumeView(KidRequiredMixin, View):
    """Resume a paused timer session."""

    def post(self, request):
        session = TimerSession.objects.filter(
            kid=request.user, ended_at__isnull=True, paused_at__isnull=False
        ).first()
        if not session:
            return JsonResponse({"error": "No paused session"}, status=400)

        now = timezone.now()
        pause_duration = int((now - session.paused_at).total_seconds())
        session.paused_seconds += pause_duration
        session.paused_at = None
        session.save()

        # Recalculate end time: original end + total paused seconds
        expected_end = session.started_at + timedelta(
            minutes=session.requested_minutes,
            seconds=session.paused_seconds,
        )

        return JsonResponse({
            "ok": True,
            "resumed": True,
            "paused_seconds": session.paused_seconds,
            "end_time_ms": int(expected_end.timestamp() * 1000),
        })


# ---------------------------------------------------------------------------
# Parent Bank Management
# ---------------------------------------------------------------------------


class TimeAdjustView(ParentRequiredMixin, View):
    """Parent manual time bank adjustment: add or subtract minutes per kid."""

    def get(self, request):
        form = TimeAdjustForm()
        kids = self._get_kids_with_balances()
        return render(request, "core/time_adjust.html", {
            "form": form,
            "kids": kids,
        })

    def post(self, request):
        form = TimeAdjustForm(request.POST)
        if form.is_valid():
            kid = form.cleaned_data["kid"]
            amount = form.cleaned_data["amount"]
            note = form.cleaned_data["note"] or f"Manual adjustment by {request.user.first_name}"
            TimeBankTransaction.objects.create(
                kid=kid,
                transaction_type=TimeBankTransaction.TransactionType.ADJUST,
                amount=amount,
                note=note,
                created_by=request.user,
            )
            sign = "+" if amount >= 0 else ""
            messages.success(
                request,
                f"Adjusted {kid.first_name}'s balance by {sign}{amount} minutes.",
            )
            return redirect("bank_adjust")
        kids = self._get_kids_with_balances()
        return render(request, "core/time_adjust.html", {
            "form": form,
            "kids": kids,
        })

    @staticmethod
    def _get_kids_with_balances():
        kids = User.objects.filter(role=User.Role.KID).order_by("first_name")
        return [
            {
                "user": kid,
                "balance": TimeBankTransaction.get_balance(kid),
                "balance_display": format_balance(TimeBankTransaction.get_balance(kid)),
            }
            for kid in kids
        ]


class TransactionHistoryView(ParentRequiredMixin, View):
    """Transaction history with kid filter and HTMX load-more pagination."""

    PAGE_SIZE = 25

    def get(self, request):
        kid_id = request.GET.get("kid")
        offset = int(request.GET.get("offset", 0))

        qs = TimeBankTransaction.objects.select_related(
            "kid", "created_by", "chore_instance__chore"
        )
        if kid_id:
            qs = qs.filter(kid_id=kid_id)

        transactions = list(qs[offset:offset + self.PAGE_SIZE + 1])
        has_more = len(transactions) > self.PAGE_SIZE
        transactions = transactions[:self.PAGE_SIZE]

        context = {
            "transactions": transactions,
            "has_more": has_more,
            "next_offset": offset + self.PAGE_SIZE,
            "kid_id": kid_id,
        }

        if request.headers.get("HX-Request"):
            return render(request, "core/_transaction_rows.html", context)

        kids = User.objects.filter(role=User.Role.KID).order_by("first_name")
        context["kids"] = kids
        return render(request, "core/transaction_history.html", context)


class TimerHistoryView(KidRequiredMixin, View):
    """Timer session history with HTMX load-more pagination for kids."""

    PAGE_SIZE = 20

    def get(self, request):
        offset = int(request.GET.get("offset", 0))

        qs = TimerSession.objects.filter(
            kid=request.user, ended_at__isnull=False
        ).order_by("-started_at")

        sessions = list(qs[offset:offset + self.PAGE_SIZE + 1])
        has_more = len(sessions) > self.PAGE_SIZE
        sessions = sessions[:self.PAGE_SIZE]

        context = {
            "sessions": sessions,
            "has_more": has_more,
            "next_offset": offset + self.PAGE_SIZE,
        }

        if request.headers.get("HX-Request"):
            return render(request, "core/_timer_history_rows.html", context)

        return render(request, "core/timer_history.html", context)


class TimeRequestCreateView(KidRequiredMixin, View):
    """Kid requests more screen time. Rate-limited to one per 30 minutes."""

    def post(self, request):
        from django.utils import timezone as tz

        cutoff = tz.now() - timedelta(minutes=30)
        recent = TimeRequest.objects.filter(
            kid=request.user, dismissed=False, created_at__gte=cutoff
        ).exists()

        if recent:
            return render(request, "core/_ask_time_result.html", {
                "message": "Already asked! Give them a minute.",
                "alert_class": "alert-warning",
            })

        TimeRequest.objects.create(kid=request.user)
        return render(request, "core/_ask_time_result.html", {
            "message": "Request sent!",
            "alert_class": "alert-success",
        })


class TimeRequestDismissView(ParentRequiredMixin, View):
    """Parent dismisses a time request."""

    def post(self, request, pk):
        req = get_object_or_404(TimeRequest, pk=pk, dismissed=False)
        req.dismissed = True
        req.save()
        return render(request, "core/_empty.html")


EMOJI_CHOICES = [
    # Animals
    "\U0001F436", "\U0001F431", "\U0001F430", "\U0001F98A", "\U0001F43B",
    "\U0001F984", "\U0001F98B", "\U0001F42C", "\U0001F989", "\U0001F427",
    # Faces
    "\U0001F600", "\U0001F929", "\U0001F60E", "\U0001F913", "\U0001F609",
    # Space/nature
    "\U0001F680", "\U00002B50", "\U0001F308", "\U00002600\U0000FE0F", "\U0001F319",
    # Sports/fun
    "\U000026BD", "\U0001F3C0", "\U0001F3B8", "\U0001F3A8", "\U0001F451",
    # Fantasy
    "\U0001F9D9", "\U0001F9DA", "\U0001F9DD", "\U0001F9DB", "\U0001F9DE",
    "\U0001F409", "\U0001FA84", "\U0001F52E", "\U00002694\U0000FE0F", "\U0001F3F0",
    # Ninja
    "\U0001F977",
]


class KidSettingsView(KidRequiredMixin, View):
    """Kid settings page for sound, animation, and emoji avatar preferences."""

    def get(self, request):
        return render(request, "core/kid_settings.html", {
            "sound_choices": User.SoundPreference.choices,
            "animation_choices": User.AnimationPreference.choices,
            "current_sound": request.user.sound_preference,
            "current_animation": request.user.animation_preference,
            "emoji_choices": EMOJI_CHOICES,
            "current_emoji": request.user.emoji_avatar,
            "bg_color_1": request.user.bg_color_1,
            "bg_color_2": request.user.bg_color_2,
            "bg_use_gradient": request.user.bg_use_gradient,
        })

    def post(self, request):
        import re
        sound = request.POST.get("sound_preference", "chime")
        animation = request.POST.get("animation_preference", "confetti")
        emoji_avatar = request.POST.get("emoji_avatar", "")

        valid_sounds = [c[0] for c in User.SoundPreference.choices]
        valid_animations = [c[0] for c in User.AnimationPreference.choices]

        if sound not in valid_sounds:
            sound = "chime"
        if animation not in valid_animations:
            animation = "confetti"

        request.user.sound_preference = sound
        request.user.animation_preference = animation
        if emoji_avatar in EMOJI_CHOICES:
            request.user.emoji_avatar = emoji_avatar

        # Background color preferences
        hex_re = re.compile(r'^#[0-9A-Fa-f]{6}$')
        bg_color_1 = request.POST.get("bg_color_1", "")
        bg_color_2 = request.POST.get("bg_color_2", "")
        bg_use_gradient = request.POST.get("bg_use_gradient") == "on"

        if bg_color_1 and not hex_re.match(bg_color_1):
            bg_color_1 = ""
        if bg_color_2 and not hex_re.match(bg_color_2):
            bg_color_2 = ""
        if bg_use_gradient and not bg_color_2:
            bg_use_gradient = False

        request.user.bg_color_1 = bg_color_1
        request.user.bg_color_2 = bg_color_2
        request.user.bg_use_gradient = bg_use_gradient
        request.user.save()

        messages.success(request, "Settings saved!")
        return redirect("kid_settings")


class ChoreLogView(ParentRequiredMixin, View):
    """Chore completion log with kid filter and HTMX load-more pagination."""

    PAGE_SIZE = 25

    def get(self, request):
        kid_id = request.GET.get("kid")
        offset = int(request.GET.get("offset", 0))
        today = localdate()

        # Completed chores OR missed required/one-off chores (past deadline)
        from django.db.models import Q

        qs = ChoreInstance.objects.filter(
            Q(completed=True)
            | Q(completed=False, due_date__lt=today, chore__chore_type="required")
            | Q(completed=False, due_date__lt=today, chore__recurrence_type="once")
        ).select_related("chore", "assigned_to").order_by("-due_date", "-completed_at")

        if kid_id:
            qs = qs.filter(assigned_to_id=kid_id)

        instances = list(qs[offset:offset + self.PAGE_SIZE + 1])
        has_more = len(instances) > self.PAGE_SIZE
        instances = instances[:self.PAGE_SIZE]

        # Annotate status and penalty amount
        for inst in instances:
            if inst.completed:
                inst.status = "Completed"
                inst.penalty_amount = None
            else:
                inst.status = "Missed"
                inst.penalty_amount = (
                    inst.chore.penalty_minutes
                    if inst.chore.chore_type == "required" and inst.chore.penalty_minutes
                    else None
                )

        context = {
            "instances": instances,
            "has_more": has_more,
            "next_offset": offset + self.PAGE_SIZE,
            "kid_id": kid_id,
        }

        if request.headers.get("HX-Request"):
            return render(request, "core/_chore_log_rows.html", context)

        kids = User.objects.filter(role=User.Role.KID).order_by("first_name")
        context["kids"] = kids
        return render(request, "core/chore_log.html", context)
