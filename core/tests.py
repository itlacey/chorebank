import json
from datetime import date, time, timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import localdate

from core.forms import ChoreForm, KidChoreRequestForm
from core.models import Chore, ChoreInstance, TimeBankTransaction, TimerSession, User
from core.tasks import generate_chore_instances, process_penalties


def _make_kid(balance_minutes=60):
    """Create a kid with a starting bank balance."""
    kid = User.objects.create_user(
        username="zeke", password="x", first_name="Zeke", role=User.Role.KID
    )
    if balance_minutes:
        TimeBankTransaction.objects.create(
            kid=kid,
            transaction_type="earn",
            amount=balance_minutes,
            note="seed",
            created_by=kid,
        )
    return kid


class TimerPauseResumeIdempotencyTests(TestCase):
    def setUp(self):
        self.kid = _make_kid()
        self.client.force_login(self.kid)
        self.session = TimerSession.objects.create(
            kid=self.kid,
            requested_minutes=10,
            started_at=timezone.now() - timedelta(seconds=30),
        )

    def test_pause_while_paused_is_noop_200(self):
        # First pause sets paused_at
        resp = self.client.post(reverse("timer_pause"))
        self.assertEqual(resp.status_code, 200)
        self.session.refresh_from_db()
        first_paused_at = self.session.paused_at
        self.assertIsNotNone(first_paused_at)

        # Second pause is a no-op, must not 400 and must not change paused_at
        resp = self.client.post(reverse("timer_pause"))
        self.assertEqual(resp.status_code, 200)
        self.session.refresh_from_db()
        self.assertEqual(self.session.paused_at, first_paused_at)

    def test_resume_while_running_is_noop_200(self):
        # Session is not paused; resume should no-op, not 400
        resp = self.client.post(reverse("timer_resume"))
        self.assertEqual(resp.status_code, 200)
        self.session.refresh_from_db()
        self.assertIsNone(self.session.paused_at)
        self.assertEqual(self.session.paused_seconds, 0)


class TimerStateViewTests(TestCase):
    def setUp(self):
        self.kid = _make_kid(balance_minutes=30)
        self.client.force_login(self.kid)
        self.url = reverse("timer_state")

    def test_idle_when_no_session(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "idle")
        self.assertEqual(data["balance"], 30)
        self.assertEqual(data["balance_display"], "30m")
        self.assertNotIn("session_id", data)

    def test_running_returns_remaining_seconds(self):
        started = timezone.now() - timedelta(seconds=120)
        session = TimerSession.objects.create(
            kid=self.kid,
            requested_minutes=10,
            started_at=started,
        )

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "running")
        self.assertEqual(data["session_id"], session.pk)
        self.assertEqual(data["requested_minutes"], 10)
        # 600s requested - 120s elapsed = 480s remaining (allow 1s slop for clock)
        self.assertGreaterEqual(data["remaining_seconds"], 479)
        self.assertLessEqual(data["remaining_seconds"], 480)

    def test_paused_freezes_remaining_across_polls(self):
        started = timezone.now() - timedelta(seconds=60)
        paused = timezone.now() - timedelta(seconds=30)
        TimerSession.objects.create(
            kid=self.kid,
            requested_minutes=10,
            started_at=started,
            paused_at=paused,
        )

        resp1 = self.client.get(self.url)
        data1 = resp1.json()
        self.assertEqual(data1["status"], "paused")
        first_remaining = data1["remaining_seconds"]
        # 600 requested - 60s started ago + 30s paused = 570 remaining
        self.assertGreaterEqual(first_remaining, 569)
        self.assertLessEqual(first_remaining, 570)

        # Paused remaining is invariant w.r.t. wall-clock time — the math is:
        #   elapsed = (now - started_at) - (paused_seconds + (now - paused_at))
        #           = paused_at - started_at - paused_seconds   (now cancels)
        # So a second poll computes the same value, no time-mocking required.
        resp2 = self.client.get(self.url)
        data2 = resp2.json()
        self.assertEqual(data2["status"], "paused")
        self.assertEqual(data2["remaining_seconds"], first_remaining)

    def test_expired_session_is_auto_closed_and_returns_ended(self):
        # A 5-min session started 10 minutes ago: expired
        started = timezone.now() - timedelta(minutes=10)
        session = TimerSession.objects.create(
            kid=self.kid,
            requested_minutes=5,
            started_at=started,
        )

        resp = self.client.get(self.url)
        data = resp.json()
        self.assertEqual(data["status"], "ended")

        session.refresh_from_db()
        self.assertIsNotNone(session.ended_at)
        self.assertEqual(session.ended_reason, "timer_expired")


def _make_parent():
    return User.objects.create_user(
        username="mom", password="x", first_name="Mom", role=User.Role.PARENT
    )


def _make_chore(parent, **overrides):
    defaults = dict(
        name="Test Chore",
        chore_type=Chore.ChoreType.REQUIRED,
        reward_minutes=5,
        penalty_minutes=10,
        time_of_day=Chore.TimeOfDay.MORNING,
        deadline_time=time(9, 0),
        recurrence_type=Chore.RecurrenceType.DAILY,
        created_by=parent,
    )
    defaults.update(overrides)
    return Chore.objects.create(**defaults)


class MultiCompletionSchemaTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid(balance_minutes=0)

    def test_chore_max_per_day_defaults_to_1(self):
        chore = _make_chore(self.parent)
        self.assertEqual(chore.max_per_day, 1)

    def test_chore_max_per_day_can_be_null(self):
        chore = _make_chore(self.parent, max_per_day=None)
        self.assertIsNone(chore.max_per_day)

    def test_chore_deadline_time_can_be_null(self):
        chore = _make_chore(self.parent, deadline_time=None)
        self.assertIsNone(chore.deadline_time)

    def test_chore_instance_completion_count_defaults_to_0(self):
        chore = _make_chore(self.parent)
        chore.assigned_to.add(self.kid)
        inst = ChoreInstance.objects.create(
            chore=chore, assigned_to=self.kid, due_date=date(2026, 1, 1)
        )
        self.assertEqual(inst.completion_count, 0)


class TimerPrerequisiteSchemaTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid(balance_minutes=0)

    def test_chore_timer_prerequisite_defaults_to_false(self):
        chore = _make_chore(self.parent)
        self.assertFalse(chore.timer_prerequisite)

    def test_chore_timer_prerequisite_can_be_true(self):
        chore = _make_chore(self.parent, timer_prerequisite=True)
        self.assertTrue(chore.timer_prerequisite)

    def test_chore_form_includes_timer_prerequisite_field(self):
        form = ChoreForm()
        self.assertIn("timer_prerequisite", form.fields)

    def test_chore_form_saves_timer_prerequisite(self):
        form_data = {
            "name": "Brush Teeth",
            "chore_type": "required",
            "reward_minutes": 5,
            "penalty_minutes": 5,
            "time_of_day": "morning",
            "assigned_to": [self.kid.pk],
            "recurrence_type": "daily",
            "completion_limit": "once",
            "timer_prerequisite": True,
        }
        form = ChoreForm(data=form_data)
        form.fields["assigned_to"].queryset = User.objects.filter(role=User.Role.KID)
        self.assertTrue(form.is_valid(), form.errors)
        chore = form.save(commit=False)
        chore.created_by = self.parent
        chore.save()
        self.assertTrue(chore.timer_prerequisite)


class PenaltyJobNullDeadlineTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid(balance_minutes=0)

    def test_required_chore_with_no_deadline_penalized_after_midnight(self):
        chore = _make_chore(
            self.parent,
            chore_type=Chore.ChoreType.REQUIRED,
            penalty_minutes=10,
            deadline_time=None,
        )
        chore.assigned_to.add(self.kid)
        yesterday = timezone.localdate() - timedelta(days=1)
        ChoreInstance.objects.create(
            chore=chore, assigned_to=self.kid, due_date=yesterday
        )

        applied = process_penalties()

        self.assertEqual(applied, 1)
        balance = TimeBankTransaction.get_balance(self.kid)
        self.assertEqual(balance, -10)

    def test_partial_multi_completion_not_penalized(self):
        chore = _make_chore(
            self.parent,
            chore_type=Chore.ChoreType.REQUIRED,
            penalty_minutes=10,
            max_per_day=3,
            deadline_time=None,
        )
        chore.assigned_to.add(self.kid)
        yesterday = timezone.localdate() - timedelta(days=1)
        # 1/3 done — completed is True, so penalty job's completed=False filter excludes it
        ChoreInstance.objects.create(
            chore=chore,
            assigned_to=self.kid,
            due_date=yesterday,
            completion_count=1,
            completed=True,
            completed_at=timezone.now() - timedelta(days=1),
        )

        applied = process_penalties()

        self.assertEqual(applied, 0)


class CompleteChoreCounterTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid(balance_minutes=0)
        self.client.force_login(self.kid)

    def _make_instance(self, **chore_overrides):
        chore = _make_chore(self.parent, **chore_overrides)
        chore.assigned_to.add(self.kid)
        return ChoreInstance.objects.create(
            chore=chore,
            assigned_to=self.kid,
            due_date=timezone.localdate(),
        )

    def test_once_a_day_first_tap_completes(self):
        inst = self._make_instance(max_per_day=1, reward_minutes=5)
        resp = self.client.post(reverse("complete_chore", args=[inst.pk]))
        self.assertEqual(resp.status_code, 200)
        inst.refresh_from_db()
        self.assertEqual(inst.completion_count, 1)
        self.assertTrue(inst.completed)
        self.assertIsNotNone(inst.completed_at)
        self.assertEqual(TimeBankTransaction.get_balance(self.kid), 5)

    def test_once_a_day_second_tap_rejected(self):
        inst = self._make_instance(max_per_day=1, reward_minutes=5)
        self.client.post(reverse("complete_chore", args=[inst.pk]))
        resp = self.client.post(reverse("complete_chore", args=[inst.pk]))
        self.assertEqual(resp.status_code, 400)
        inst.refresh_from_db()
        self.assertEqual(inst.completion_count, 1)
        self.assertEqual(TimeBankTransaction.get_balance(self.kid), 5)

    def test_capped_chore_three_taps_then_rejected(self):
        inst = self._make_instance(max_per_day=3, reward_minutes=2)
        for _ in range(3):
            resp = self.client.post(reverse("complete_chore", args=[inst.pk]))
            self.assertEqual(resp.status_code, 200)
        resp = self.client.post(reverse("complete_chore", args=[inst.pk]))
        self.assertEqual(resp.status_code, 400)
        inst.refresh_from_db()
        self.assertEqual(inst.completion_count, 3)
        self.assertEqual(TimeBankTransaction.get_balance(self.kid), 6)
        # 3 EARN transactions
        earns = TimeBankTransaction.objects.filter(
            kid=self.kid, transaction_type="earn"
        )
        self.assertEqual(earns.count(), 3)

    def test_unlimited_chore_five_taps_all_accepted(self):
        inst = self._make_instance(max_per_day=None, reward_minutes=1)
        for _ in range(5):
            resp = self.client.post(reverse("complete_chore", args=[inst.pk]))
            self.assertEqual(resp.status_code, 200)
        inst.refresh_from_db()
        self.assertEqual(inst.completion_count, 5)
        self.assertEqual(TimeBankTransaction.get_balance(self.kid), 5)

    def test_completed_at_set_on_first_tap_only(self):
        inst = self._make_instance(max_per_day=3, reward_minutes=2)
        self.client.post(reverse("complete_chore", args=[inst.pk]))
        inst.refresh_from_db()
        first_completed_at = inst.completed_at
        self.client.post(reverse("complete_chore", args=[inst.pk]))
        inst.refresh_from_db()
        self.assertEqual(inst.completed_at, first_completed_at)

    def test_zero_reward_chore_increments_count_no_transaction(self):
        inst = self._make_instance(
            max_per_day=2,
            reward_minutes=0,
            chore_type=Chore.ChoreType.BONUS,
            penalty_minutes=0,
        )
        self.client.post(reverse("complete_chore", args=[inst.pk]))
        inst.refresh_from_db()
        self.assertEqual(inst.completion_count, 1)
        self.assertEqual(TimeBankTransaction.objects.filter(kid=self.kid).count(), 0)


class ChoreFormCompletionLimitTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid(balance_minutes=0)

    def _base_data(self, **overrides):
        data = dict(
            name="Test",
            chore_type="required",
            reward_minutes="5",
            penalty_minutes="10",
            time_of_day="morning",
            deadline_time="09:00",
            assigned_to=[str(self.kid.pk)],
            recurrence_type="daily",
            completion_limit="once",
            max_per_day_value="",
        )
        data.update(overrides)
        return data

    def test_once_saves_max_per_day_1(self):
        form = ChoreForm(data=self._base_data(completion_limit="once"))
        self.assertTrue(form.is_valid(), form.errors)
        chore = form.save(commit=False)
        chore.created_by = self.parent
        chore.save()
        form.save_m2m()
        self.assertEqual(chore.max_per_day, 1)

    def test_multiple_with_3_saves_max_per_day_3(self):
        form = ChoreForm(
            data=self._base_data(completion_limit="multiple", max_per_day_value="3")
        )
        self.assertTrue(form.is_valid(), form.errors)
        chore = form.save(commit=False)
        chore.created_by = self.parent
        chore.save()
        form.save_m2m()
        self.assertEqual(chore.max_per_day, 3)

    def test_unlimited_saves_max_per_day_null(self):
        form = ChoreForm(data=self._base_data(completion_limit="unlimited"))
        self.assertTrue(form.is_valid(), form.errors)
        chore = form.save(commit=False)
        chore.created_by = self.parent
        chore.save()
        form.save_m2m()
        self.assertIsNone(chore.max_per_day)

    def test_multiple_with_no_value_is_invalid(self):
        form = ChoreForm(
            data=self._base_data(completion_limit="multiple", max_per_day_value="")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("max_per_day_value", form.errors)

    def test_multiple_with_1_is_invalid(self):
        form = ChoreForm(
            data=self._base_data(completion_limit="multiple", max_per_day_value="1")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("max_per_day_value", form.errors)

    def test_deadline_time_optional(self):
        form = ChoreForm(data=self._base_data(deadline_time=""))
        self.assertTrue(form.is_valid(), form.errors)
        chore = form.save(commit=False)
        chore.created_by = self.parent
        chore.save()
        form.save_m2m()
        self.assertIsNone(chore.deadline_time)

    def test_editing_unlimited_chore_initializes_radio(self):
        chore = _make_chore(self.parent, max_per_day=None)
        form = ChoreForm(instance=chore)
        self.assertEqual(form.fields["completion_limit"].initial, "unlimited")

    def test_editing_multiple_chore_initializes_radio_and_value(self):
        chore = _make_chore(self.parent, max_per_day=5)
        form = ChoreForm(instance=chore)
        self.assertEqual(form.fields["completion_limit"].initial, "multiple")
        self.assertEqual(form.fields["max_per_day_value"].initial, 5)

    def test_editing_once_chore_initializes_radio(self):
        chore = _make_chore(self.parent, max_per_day=1)
        form = ChoreForm(instance=chore)
        self.assertEqual(form.fields["completion_limit"].initial, "once")

    def test_multiple_with_1_emits_single_error(self):
        form = ChoreForm(
            data=self._base_data(completion_limit="multiple", max_per_day_value="1")
        )
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors["max_per_day_value"]), 1)


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)
class TimerPrerequisiteGateTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid(balance_minutes=60)
        self.client.force_login(self.kid)
        self.client.cookies["browser_tz"] = "UTC"

        self.prereq_chore = _make_chore(
            self.parent, name="Make Bed", timer_prerequisite=True
        )
        self.prereq_chore.assigned_to.add(self.kid)

        self.normal_chore = _make_chore(
            self.parent, name="Read Book", timer_prerequisite=False
        )
        self.normal_chore.assigned_to.add(self.kid)

    def _create_instances(self, today=None):
        today = today or localdate()
        ChoreInstance.objects.create(
            chore=self.prereq_chore, assigned_to=self.kid, due_date=today
        )
        ChoreInstance.objects.create(
            chore=self.normal_chore, assigned_to=self.kid, due_date=today
        )

    def test_timer_page_blocked_when_prereq_incomplete(self):
        self._create_instances()
        resp = self.client.get(reverse("kid_timer"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["timer_blocked"])
        self.assertContains(resp, "Finish your chores first")
        self.assertContains(resp, "Make Bed")

    def test_timer_page_unblocked_when_prereq_complete(self):
        self._create_instances()
        inst = ChoreInstance.objects.get(
            chore=self.prereq_chore, assigned_to=self.kid
        )
        inst.completed = True
        inst.completed_at = timezone.now()
        inst.save()

        resp = self.client.get(reverse("kid_timer"))
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context["timer_blocked"])
        self.assertNotContains(resp, "Finish your chores first")

    def test_timer_page_unblocked_when_no_prereq_chores(self):
        self.prereq_chore.timer_prerequisite = False
        self.prereq_chore.save()
        self._create_instances()

        resp = self.client.get(reverse("kid_timer"))
        self.assertFalse(resp.context["timer_blocked"])

    def test_timer_page_unblocked_when_no_instances_today(self):
        resp = self.client.get(reverse("kid_timer"))
        self.assertFalse(resp.context["timer_blocked"])

    def test_timer_page_shows_completed_prereqs_crossed_out(self):
        self._create_instances()
        second_prereq = _make_chore(
            self.parent, name="Brush Teeth", timer_prerequisite=True
        )
        second_prereq.assigned_to.add(self.kid)
        ChoreInstance.objects.create(
            chore=second_prereq, assigned_to=self.kid, due_date=localdate()
        )
        # Complete one of the two prerequisites
        inst = ChoreInstance.objects.get(
            chore=second_prereq, assigned_to=self.kid
        )
        inst.completed = True
        inst.completed_at = timezone.now()
        inst.save()

        resp = self.client.get(reverse("kid_timer"))
        self.assertTrue(resp.context["timer_blocked"])
        self.assertContains(resp, "Brush Teeth")
        self.assertContains(resp, "Make Bed")

    def test_timer_start_rejected_when_prereq_incomplete(self):
        self._create_instances()
        resp = self.client.post(
            reverse("timer_start"),
            data=json.dumps({"minutes": 10}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        data = resp.json()
        self.assertIn("chores", data["error"].lower())
        self.assertFalse(
            TimerSession.objects.filter(kid=self.kid).exists()
        )

    def test_timer_start_allowed_when_prereq_complete(self):
        self._create_instances()
        inst = ChoreInstance.objects.get(
            chore=self.prereq_chore, assigned_to=self.kid
        )
        inst.completed = True
        inst.completed_at = timezone.now()
        inst.save()

        resp = self.client.post(
            reverse("timer_start"),
            data=json.dumps({"minutes": 10}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(
            TimerSession.objects.filter(kid=self.kid).exists()
        )


# ---------------------------------------------------------------------------
# Kid chore requests
# ---------------------------------------------------------------------------

_STORAGE_OVERRIDE = dict(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
)


def _make_kid2():
    return User.objects.create_user(
        username="ava", password="x", first_name="Ava", role=User.Role.KID
    )


def _make_pending(kid, name="Feed the fish", **overrides):
    defaults = dict(
        name=name,
        chore_type=Chore.ChoreType.BONUS,
        reward_minutes=15,
        penalty_minutes=0,
        time_of_day=Chore.TimeOfDay.AFTERNOON,
        deadline_time=None,
        recurrence_type=Chore.RecurrenceType.DAILY,
        created_by=kid,
        is_active=False,
        pending_approval=True,
    )
    defaults.update(overrides)
    chore = Chore.objects.create(**defaults)
    chore.assigned_to.set([kid])
    return chore


def _request_post(**overrides):
    data = {
        "name": "Feed the fish",
        "chore_type": "bonus",
        "reward_minutes": 15,
        "time_of_day": "afternoon",
        "recurrence_type": "daily",
        "completion_limit": "once",
    }
    data.update(overrides)
    return data


class ChorePendingApprovalSchemaTests(TestCase):
    def test_default_false(self):
        chore = _make_chore(_make_parent())
        self.assertFalse(chore.pending_approval)

    def test_kid_request_form_has_no_assigned_to(self):
        self.assertNotIn("assigned_to", KidChoreRequestForm().fields)
        self.assertIn("assigned_to", ChoreForm().fields)


@override_settings(**_STORAGE_OVERRIDE)
class KidChoreRequestTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid()
        self.kid2 = _make_kid2()
        self.client.force_login(self.kid)
        self.client.cookies["browser_tz"] = "UTC"
        self.url = reverse("kid_chore_request")

    def test_get_renders_suggest_form(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Suggest a chore")
        self.assertContains(resp, "Send to a parent")
        self.assertNotContains(resp, 'name="assigned_to"')

    def test_post_creates_pending_chore(self):
        self.client.post(self.url, _request_post())
        chore = Chore.objects.get()
        self.assertFalse(chore.is_active)
        self.assertTrue(chore.pending_approval)
        self.assertEqual(chore.created_by, self.kid)
        self.assertEqual(list(chore.assigned_to.all()), [self.kid])
        self.assertEqual(chore.max_per_day, 1)

    def test_post_ignores_posted_assigned_to(self):
        self.client.post(self.url, _request_post(assigned_to=[self.kid2.pk]))
        chore = Chore.objects.get()
        self.assertEqual(list(chore.assigned_to.all()), [self.kid])

    def test_post_ignores_posted_approval_flags(self):
        self.client.post(self.url, _request_post(is_active="on", pending_approval=""))
        chore = Chore.objects.get()
        self.assertFalse(chore.is_active)
        self.assertTrue(chore.pending_approval)

    def test_post_redirects_with_message(self):
        resp = self.client.post(self.url, _request_post(), follow=True)
        self.assertRedirects(resp, reverse("kid_chore_list"))
        self.assertContains(resp, 'Sent! A parent will look at')

    def test_invalid_post_rerenders_and_saves_nothing(self):
        resp = self.client.post(self.url, _request_post(chore_type="required"))
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["form"].errors)
        self.assertEqual(Chore.objects.count(), 0)

    def test_post_creates_no_instances(self):
        self.client.post(self.url, _request_post())
        self.assertEqual(ChoreInstance.objects.count(), 0)

    def test_parent_cannot_use_kid_form(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_anonymous_redirected_to_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)


@override_settings(**_STORAGE_OVERRIDE)
class PendingChoreLeakTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid()
        self.kid2 = _make_kid2()
        self.client.cookies["browser_tz"] = "UTC"

    def test_generate_chore_instances_skips_pending(self):
        chore = _make_pending(self.kid)
        generate_chore_instances(target_date=localdate(), days_ahead=7)
        self.assertEqual(ChoreInstance.objects.filter(chore=chore).count(), 0)

    def test_kid_list_shows_own_pending_only(self):
        _make_pending(self.kid, name="Mine Pending")
        _make_pending(self.kid2, name="Theirs Pending")
        self.client.force_login(self.kid)
        resp = self.client.get(reverse("kid_chore_list"))
        self.assertContains(resp, "Waiting for a parent")
        self.assertContains(resp, "Mine Pending")
        self.assertNotContains(resp, "Theirs Pending")
        self.assertContains(resp, "Sent today")
        self.assertEqual(resp.context["afternoon_chores"], [])

    def test_parent_chore_list_excludes_pending(self):
        _make_pending(self.kid, name="Mine Pending")
        self.client.force_login(self.parent)
        resp = self.client.get(reverse("chore_list"))
        self.assertNotContains(resp, "Mine Pending")

    def test_kid_list_has_suggest_button(self):
        self.client.force_login(self.kid)
        resp = self.client.get(reverse("kid_chore_list"))
        self.assertContains(resp, reverse("kid_chore_request"))

    def test_suggest_button_is_above_todays_chores(self):
        self.client.force_login(self.kid)
        html = self.client.get(reverse("kid_chore_list")).content.decode()
        self.assertLess(html.index(reverse("kid_chore_request")), html.index("Today's Chores"))


@override_settings(**_STORAGE_OVERRIDE)
class ParentChoreRequestBoxTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid()
        self.kid2 = _make_kid2()
        self.client.force_login(self.parent)
        self.client.cookies["browser_tz"] = "UTC"

    def test_box_shows_count_and_details(self):
        _make_pending(self.kid, name="Feed the fish")
        _make_pending(self.kid2, name="Walk dog")
        resp = self.client.get(reverse("parent_home"))
        self.assertContains(resp, "Chore requests (2)")
        self.assertContains(resp, "Zeke")
        self.assertContains(resp, "Ava")
        self.assertContains(resp, "+15 min")
        self.assertContains(resp, "every day")
        self.assertContains(resp, "afternoon")

    def test_box_hidden_when_none(self):
        resp = self.client.get(reverse("parent_home"))
        self.assertNotContains(resp, "Chore requests")

    def test_soft_deleted_chore_not_listed(self):
        _make_pending(self.kid, name="Gone", pending_approval=False)
        resp = self.client.get(reverse("parent_home"))
        self.assertNotContains(resp, "Chore requests")


@override_settings(**_STORAGE_OVERRIDE)
class ChoreRequestApproveTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid()
        self.chore = _make_pending(self.kid)
        self.client.cookies["browser_tz"] = "UTC"
        self.url = reverse("chore_request_approve", args=[self.chore.pk])

    def test_approve_activates_and_creates_today_instance(self):
        self.client.force_login(self.parent)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.chore.refresh_from_db()
        self.assertFalse(self.chore.pending_approval)
        self.assertTrue(self.chore.is_active)
        self.assertTrue(
            ChoreInstance.objects.filter(
                chore=self.chore, assigned_to=self.kid, due_date=localdate()
            ).exists()
        )
        self.client.force_login(self.kid)
        resp = self.client.get(reverse("kid_chore_list"))
        self.assertEqual(len(resp.context["afternoon_chores"]), 1)

    def test_approve_returns_remaining_box_with_count(self):
        other = _make_pending(self.kid, name="Second")
        self.client.force_login(self.parent)
        resp = self.client.post(self.url)
        self.assertContains(resp, "Chore requests (1)")
        self.assertContains(resp, 'id="chore-requests"')
        self.assertContains(resp, f"chore-req-{other.pk}")

    def test_approve_last_returns_empty(self):
        self.client.force_login(self.parent)
        resp = self.client.post(self.url)
        self.assertNotContains(resp, "Chore requests")

    def test_approve_get_not_allowed(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.chore.refresh_from_db()
        self.assertTrue(self.chore.pending_approval)

    def test_kid_cannot_approve(self):
        self.client.force_login(self.kid)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.chore.refresh_from_db()
        self.assertTrue(self.chore.pending_approval)
        self.assertEqual(ChoreInstance.objects.count(), 0)

    def test_approve_non_pending_404(self):
        active = _make_chore(self.parent)
        self.client.force_login(self.parent)
        resp = self.client.post(reverse("chore_request_approve", args=[active.pk]))
        self.assertEqual(resp.status_code, 404)


@override_settings(**_STORAGE_OVERRIDE)
class ChoreRequestRejectTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid()
        self.chore = _make_pending(self.kid)
        self.url = reverse("chore_request_reject", args=[self.chore.pk])

    def test_reject_deletes(self):
        self.client.force_login(self.parent)
        self.assertEqual(self.client.post(self.url).status_code, 200)
        self.assertFalse(Chore.objects.filter(pk=self.chore.pk).exists())

    def test_reject_keeps_box_count_correct(self):
        _make_pending(self.kid, name="Second")
        self.client.force_login(self.parent)
        resp = self.client.post(self.url)
        self.assertContains(resp, "Chore requests (1)")

    def test_reject_last_returns_empty(self):
        self.client.force_login(self.parent)
        resp = self.client.post(self.url)
        self.assertNotContains(resp, "Chore requests")

    def test_kid_cannot_reject(self):
        self.client.force_login(self.kid)
        self.assertEqual(self.client.post(self.url).status_code, 403)
        self.assertTrue(Chore.objects.filter(pk=self.chore.pk).exists())

    def test_reject_non_pending_404(self):
        active = _make_chore(self.parent)
        self.client.force_login(self.parent)
        resp = self.client.post(reverse("chore_request_reject", args=[active.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Chore.objects.filter(pk=active.pk).exists())


@override_settings(**_STORAGE_OVERRIDE)
class ChoreRequestEditTests(TestCase):
    def setUp(self):
        self.parent = _make_parent()
        self.kid = _make_kid()
        self.chore = _make_pending(self.kid)
        self.url = reverse("chore_edit", args=[self.chore.pk])
        self.client.cookies["browser_tz"] = "UTC"

    def _post_data(self, **kw):
        return _request_post(assigned_to=[self.kid.pk], **kw)

    def test_edit_get_pending_200(self):
        self.client.force_login(self.parent)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "chore request from Zeke")

    def test_edit_post_keeps_pending(self):
        self.client.force_login(self.parent)
        resp = self.client.post(self.url, self._post_data(name="Renamed"))
        self.assertRedirects(resp, reverse("parent_home"))
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.name, "Renamed")
        self.assertTrue(self.chore.pending_approval)
        self.assertFalse(self.chore.is_active)
        self.assertEqual(ChoreInstance.objects.count(), 0)

    def test_edit_message_shown_on_parent_home(self):
        self.client.force_login(self.parent)
        resp = self.client.post(
            self.url, self._post_data(name="Renamed"), follow=True
        )
        self.assertContains(resp, "updated!")
        resp = self.client.get(reverse("parent_home"))
        self.assertNotContains(resp, "updated!")

    def test_edit_soft_deleted_still_404(self):
        self.chore.pending_approval = False
        self.chore.save()
        self.client.force_login(self.parent)
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_kid_cannot_open_edit(self):
        self.client.force_login(self.kid)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        resp = self.client.post(self.url, self._post_data(name="Hacked"))
        self.assertEqual(resp.status_code, 403)
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.name, "Feed the fish")

    def test_edit_active_chore_still_redirects_to_chore_list(self):
        active = _make_chore(self.parent, chore_type=Chore.ChoreType.BONUS, penalty_minutes=0)
        active.assigned_to.set([self.kid])
        self.client.force_login(self.parent)
        resp = self.client.post(
            reverse("chore_edit", args=[active.pk]), self._post_data(name="Edited")
        )
        self.assertRedirects(resp, reverse("chore_list"))
