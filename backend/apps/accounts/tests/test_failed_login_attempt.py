from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import FailedLoginAttempt

User = get_user_model()


class FailedLoginAttemptModelTests(TestCase):
    """T07 — FailedLoginAttempt log, support for RF-7 lockout."""

    def setUp(self):
        self.mesero = User.objects.create_user(
            username="mesero_intentos", password="1234", role=User.Role.MESERO
        )

    def test_create_failed_login_attempt(self):
        attempt = FailedLoginAttempt.objects.create(account=self.mesero)
        self.assertEqual(attempt.account, self.mesero)

    def test_timestamp_is_set_automatically(self):
        attempt = FailedLoginAttempt.objects.create(account=self.mesero)
        self.assertIsNotNone(attempt.timestamp)

    def test_multiple_attempts_are_kept_independently(self):
        FailedLoginAttempt.objects.create(account=self.mesero)
        FailedLoginAttempt.objects.create(account=self.mesero)
        FailedLoginAttempt.objects.create(account=self.mesero)
        self.assertEqual(
            FailedLoginAttempt.objects.filter(account=self.mesero).count(), 3
        )

    def test_deleting_account_cascades_its_attempts(self):
        FailedLoginAttempt.objects.create(account=self.mesero)
        self.mesero.delete()
        self.assertEqual(FailedLoginAttempt.objects.count(), 0)
