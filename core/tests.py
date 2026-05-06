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
