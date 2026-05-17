from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import TimeBankTransaction, TimerSession, User


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
