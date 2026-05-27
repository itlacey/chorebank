from datetime import date, time, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.forms import ChoreForm
from core.models import Chore, ChoreInstance, TimeBankTransaction, TimerSession, User
from core.tasks import process_penalties


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

    def test_chore_timer_prerequisite_defaults_to_false(self):
        chore = _make_chore(self.parent)
        self.assertFalse(chore.timer_prerequisite)

    def test_chore_timer_prerequisite_can_be_true(self):
        chore = _make_chore(self.parent, timer_prerequisite=True)
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
