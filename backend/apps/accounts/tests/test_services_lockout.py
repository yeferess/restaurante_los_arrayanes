from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import FailedLoginAttempt
from apps.accounts.services import attempt_login

User = get_user_model()


class LockoutAfterFiveFailedAttemptsTests(TestCase):
    """T12 — 5 consecutive failed attempts lock the account (RF-7)."""

    def setUp(self):
        self.mesero = User.objects.create_user(
            username="mesero_bloqueo", password="1234", role=User.Role.MESERO
        )

    def _fail_login(self, times):
        for _ in range(times):
            attempt_login(
                username="mesero_bloqueo",
                credential="wrong",
                expected_role=User.Role.MESERO,
            )

    def test_five_failed_attempts_lock_the_account(self):
        self._fail_login(5)
        self.mesero.refresh_from_db()
        self.assertTrue(self.mesero.is_locked)
        self.assertIsNotNone(self.mesero.locked_at)

    def test_fewer_than_five_failed_attempts_do_not_lock(self):
        self._fail_login(4)
        self.mesero.refresh_from_db()
        self.assertFalse(self.mesero.is_locked)

    def test_locked_account_rejects_even_correct_credentials(self):
        self._fail_login(5)
        result = attempt_login(
            username="mesero_bloqueo",
            credential="1234",
            expected_role=User.Role.MESERO,
        )
        self.assertFalse(result.success)
        self.assertEqual(result.status, "locked")

    def test_each_failed_attempt_is_logged(self):
        self._fail_login(3)
        self.assertEqual(
            FailedLoginAttempt.objects.filter(account=self.mesero).count(), 3
        )
