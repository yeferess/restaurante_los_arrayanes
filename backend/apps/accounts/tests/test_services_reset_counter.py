from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.services import attempt_login

User = get_user_model()


class ResetCounterOnSuccessTests(TestCase):
    """T13 — a successful login resets failed_login_attempts to 0 (RF-7)."""

    def setUp(self):
        self.mesero = User.objects.create_user(
            username="mesero_reset", password="1234", role=User.Role.MESERO
        )

    def test_three_failures_then_success_resets_counter_to_zero(self):
        for _ in range(3):
            attempt_login(
                username="mesero_reset",
                credential="wrong",
                expected_role=User.Role.MESERO,
            )
        self.mesero.refresh_from_db()
        self.assertEqual(self.mesero.failed_login_attempts, 3)

        result = attempt_login(
            username="mesero_reset", credential="1234", expected_role=User.Role.MESERO
        )
        self.assertTrue(result.success)
        self.mesero.refresh_from_db()
        self.assertEqual(self.mesero.failed_login_attempts, 0)
